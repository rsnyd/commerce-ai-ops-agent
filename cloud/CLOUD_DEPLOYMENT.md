# Deploying the Commerce AI Ops Agent on AWS Bedrock

The Commerce AI Ops Agent produces merchandising recommendations for a SKU: it pulls internal metrics, competitor prices and review sentiment through tools, writes a recommendation, and runs it through a brand-voice guardrail. This document covers moving it from the direct Anthropic API to AWS Bedrock: why, how, what it costs, and what to watch for.

## Why Bedrock (vs direct Anthropic API)

Same model, same output quality. What changes is who you buy from and whose controls apply.

- **Procurement:** AI spend lands on the existing AWS bill and draws down existing commitments. No new vendor to onboard.
- **Data residency:** geographic inference profiles (`us.`) keep requests inside US regions, within the AWS security boundary.
- **Identity:** access is controlled by existing IAM users and roles, not long-lived API keys that live in `.env` files.
- **Audit:** Bedrock API calls are recorded in CloudTrail (who, which model, when). Model invocation logging can also capture prompts and responses to S3 or CloudWatch.
- **Cost allocation:** application inference profiles can be tagged per project or team, so spend shows up in Cost Explorer by owner.

## Migration approach

I used the `AnthropicBedrock` client from the Anthropic SDK, which keeps the native Messages API. The orchestration loop didn't change. The diff to `agent.py` is the client constructor and the model ID:

```python
client = AnthropicBedrock(aws_region="us-east-1")
MODEL = "us.anthropic.claude-sonnet-4-6"
```

Tool schemas, the system prompt and the tool dispatcher are imported from `agent.py` unchanged. Well-structured application code ports cleanly: only auth, region and billing differ.

The alternative is boto3's Converse API, which is model-agnostic (the same script ran Amazon Nova and Claude by changing only the model ID) but means rewriting the message and tool-use handling. For a Claude-only agent, `AnthropicBedrock` is the smaller change. The two clients report the same failure differently (boto3 `AccessDeniedException` vs the SDK's `PermissionDeniedError`), so error handling doesn't carry over between them.

**Not fully ported yet.** The guardrail and the review-sentiment tool create their own `Anthropic()` client, so 2 of the 5 model calls per run still go to the direct API. For a customer that requires all model traffic inside AWS, those clients must be switched too before go-live.

## Authentication

An IAM user with a least-privilege policy (`iam-policy.json`) replaces `AmazonBedrockFullAccess`. It allows only `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` (which also cover Converse) on:

- the `us.anthropic.claude-sonnet-4-6` inference profile, and
- the Sonnet 4.6 foundation model in **every region the profile routes to** (us-east-1, us-east-2, us-west-2).

The second part is the catch. A `us.` profile sends each request to one of several regions, so a policy that allows only the us-east-1 model ARN fails intermittently on requests routed elsewhere. The region list comes from `aws bedrock get-inference-profile`.

For production, swap the IAM user for a role assumed by the workload (ECS task role, Lambda execution role), so there are no access keys at all. Moving the guardrail and sentiment calls onto Bedrock also means adding Haiku 4.5 to the policy.

## Regional considerations

- **Inference profile IDs are required** for current Claude models. The bare model ID fails with "on-demand throughput isn't supported".
- **`us.` vs `global.` is a residency and price tradeoff.** `us.` keeps traffic in US regions. `global.` can route anywhere for more capacity and costs about 10% less (from Sonnet 4.5 / Haiku 4.5 on, geographic and in-region endpoints carry a 10% premium). This deployment uses `us.`.
- **Model access is approved per account, per model.** Sonnet 4.6 and Haiku 4.5 worked immediately. Sonnet 5 and Opus 5 are denied on this account, and AWS Support couldn't approve them: access depends on account history and goes through an AWS account team. The availability API shows the same status for working and denied models, so the only reliable check is a real invoke. **If a launch depends on the newest model, confirm access before committing to a date.**
- **Legacy models are closed to new accounts.** A model the account hasn't used in 30 days (e.g. Sonnet 4) is blocked.
- **On-demand vs provisioned throughput.** On-demand bills per token with no commitment. Provisioned throughput reserves capacity for a term and fits steady, high-volume traffic or workloads that need a throughput guarantee. At the volume projected below, on-demand is the right choice.

## Cost and latency (measured)

10 runs on SKU GM-001, 2026-09-29, measured from Langfuse traces. Full method and per-call breakdown in `cost_analysis.md`.

| Metric (per agent run) | Value |
|---|---|
| Avg tokens | 6,138 (5,326 input / 812 output) |
| Avg cost | $0.029 as routed today ($0.030 all on Bedrock `us.`) |
| Avg latency | 17.0s end to end (p50 16.6s, p95 25.1s) |
| Model calls | 5: 3 orchestrator turns + 1 sentiment (Haiku, inside a tool) + 1 guardrail |

**Projected: 1,000 runs/day = ~$900/month on Bedrock `us.`** ($822 on `global.`), p50 latency ~17s.

Where the money goes:

- The guardrail check is the most expensive single call: about a third of the cost and a quarter of the latency.
- Input is 87% of tokens, because each orchestrator turn re-sends the system prompt, tool schemas and history. Prompt caching is the obvious first optimization.

Latency caveat: these numbers are client-side span timings from a WSL2 dev machine, whose clock skews individual runs by up to about 2s. The average holds; re-measure from EC2 before quoting a latency SLA.

## Guardrail layering

Two layers, doing different jobs. *Design only: the application layer exists, the platform layer isn't implemented yet.*

- **Platform layer: Bedrock Guardrails.** Configured once in AWS and attached to model calls by guardrail ID and version, independent of application code. It handles what every workload needs: content filters (hate, violence, prompt attacks), denied topics, and PII detection and redaction. It can also run standalone through the `ApplyGuardrail` API. It's owned by the platform or security team and applies whether or not the app code is correct.
- **Application layer: brand-voice evaluator (`guardrail.py`).** Enforces Spices Inc's voice: a regex scan for forbidden words and em dashes, then a model call for the judgment calls (tone, vague sensory language), which returns revised text. This is business logic no platform guardrail knows about.

The platform layer is the safety net: it catches unsafe or PII-bearing content even if the application's own checks are wrong or bypassed. The application layer makes the output on-brand. Neither replaces the other.

## What I'd add for production

- **Finish the port:** move the guardrail and sentiment clients onto Bedrock so all model traffic stays inside AWS, and extend the IAM policy to Haiku 4.5.
- **IAM role, not user:** workload identity with no long-lived keys.
- **Bedrock Guardrails** attached to the orchestrator calls (PII, content safety).
- **Cost controls:** prompt caching on the system prompt and tools; evaluate Haiku for the guardrail check, gated on the existing eval suite.
- **CloudWatch alarms** on cost, error rate and throttling.
- **A VPC endpoint (PrivateLink) for Bedrock** to keep traffic off the public internet.
- **Retry with exponential backoff and jitter** on throttling errors.
- **Provisioned throughput** only if traffic becomes steady and latency-sensitive well beyond 1,000 runs/day.
