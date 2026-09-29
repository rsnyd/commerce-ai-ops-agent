# Cost, Latency and Regional Considerations (Week 10 Day 5)

What one run of the Commerce AI Ops Agent costs on AWS Bedrock, how long it takes, and the operational gotchas I hit getting there. Feeds the Day 6 `CLOUD_DEPLOYMENT.md`.

## Method

- 10 runs of `cloud/agent_bedrock.py` on SKU GM-001, 2026-09-29, us-east-1.
- Orchestrator: Claude Sonnet 4.6 via the `us.anthropic.claude-sonnet-4-6` inference profile, `AnthropicBedrock` client.
- Numbers come from Langfuse traces. Every run in the batch shares one session id (`bedrock-measure-e47d8d21`), so the report reads back exactly those 10 traces.
- Reproduce with `uv run python cloud/measure_runs.py 10 GM-001`, or re-report a past batch with `--report <session>`.

## Results

| Metric (per agent run) | Value |
|---|---|
| Tokens (input + output, all model calls) | 6,138 (5,326 in / 812 out) |
| Cost per run | $0.029 as routed today ($0.030 if every call ran on Bedrock `us.`) |
| Latency, end to end | 17.0s average, p50 16.6s, p95 25.1s |
| Model calls per run | 5 (3 orchestrator turns + 1 sentiment + 1 guardrail) |

Every run took the same path: 3 orchestrator turns, 5 model calls. Tool execution is ~1ms, so latency is effectively all model time.

### Per-call breakdown (averages, priced at Bedrock `us.` rates)

| Call | Model | Input | Output | Latency | Cost |
|---|---|---|---|---|---|
| orchestrator-turn-1 | Sonnet 4.6 | 1,014 | 80 | 2.9s | $0.0047 |
| orchestrator-turn-2 | Sonnet 4.6 | 1,225 | 123 | 2.2s | $0.0061 |
| orchestrator-turn-3 | Sonnet 4.6 | 1,641 | 238 | 5.4s | $0.0093 |
| sentiment-summary (inside a tool) | Haiku 4.5 | 78 | 60 | 1.8s | $0.0004 |
| guardrail-check | Sonnet 4.6 | 1,368 | 311 | 4.7s | $0.0097 |

Two things stand out:

- **The guardrail is the most expensive single call** - a third of the cost and over a quarter of the latency. It's the obvious first target for optimization.
- **Input dominates tokens (87%) and cost (~57%).** Each orchestrator turn re-sends the system prompt, tool schemas and growing history. That's what prompt caching is for.

## Projection: 1,000 agent runs per day

| Routing | Cost/run | Monthly (30 days) |
|---|---|---|
| As measured (orchestrator on Bedrock `us.`, sentiment + guardrail on direct API) | $0.029 | **$877** |
| Everything on Bedrock `us.` (geographic) | $0.030 | $904 |
| Everything on Bedrock `global.` | $0.027 | $822 |

**At 1,000 runs/day: ~$880-900/month, p50 latency ~17s.**

Levers, not yet measured:

- Prompt caching on the system prompt + tool schemas across orchestrator turns (cached reads bill at 0.1x input).
- Haiku 4.5 for the guardrail check if its judgment holds up in the eval suite - it's the largest single cost line.
- `global.` instead of `us.` saves ~9%, if data residency allows it (see below).

1,000 runs/day is under one run per minute - far below where provisioned throughput pays off. On-demand is the right choice at this volume.

## Measurement gotchas

- **`latencyMs` isn't available with this client.** Bedrock only reports `metrics.latencyMs` on Converse API responses. The `AnthropicBedrock` client uses InvokeModel with the Messages shape and returns no latency metric, so latency here is from Langfuse span timings (client-side, includes network).
- **The Bedrock port wasn't traced.** Day 3's `agent_bedrock.py` called `client.messages.create` directly, so its orchestrator turns never reached Langfuse - only the guardrail and sentiment calls showed up, as orphan traces. Fixed by wrapping it the same way as `agent.py` (`@observe` + `traced_messages_create`).
- **2 of the 5 model calls still bypass Bedrock.** `guardrail.py` and `tools.get_review_sentiment` each build their own `Anthropic()` client, so they hit the direct API regardless of which agent calls them. A customer who needs all traffic inside AWS would need those clients injected or switched too. The cost difference is small (the 10% `us.` premium); the compliance difference is not.
- **Langfuse v4 removed the v1 trace endpoint.** `langfuse.api.trace.list` returns 404 on an events-only v4 deployment. Read data via `api.observations.get_many` (v2), and pass `fields="core,basic,time,model,usage"` - the default response omits usage and model.
- **WSL2's clock skews per-run latency.** The VM's clock runs ~6% slow and gets stepped forward ~2s every ~30s to resync with the Windows host. Span timestamps are wall-clock, so any single run can be off by up to ~2s depending on whether a step landed inside it. Batch averages are sound; treat p50 as +/-1s. Measure from a real Linux host (or an EC2 instance) before quoting latency to a customer.

## Regional and model-availability gotchas

- **Current Claude models need an inference profile ID.** The bare model ID (`anthropic.claude-sonnet-4-6`) fails with "on-demand throughput isn't supported". Use a `us.` or `global.` profile.
- **`us.` vs `global.` is a data-residency and price choice.** `us.` keeps requests in US regions (us-east-1, us-east-2, us-west-2 for this profile). `global.` can route anywhere for more capacity. From Sonnet 4.5 / Haiku 4.5 on, geographic and in-region endpoints cost 10% more than global. A compliance-sensitive customer wants the geographic profile and should budget for the premium.
- **Cross-region profiles complicate IAM.** A least-privilege policy has to allow the inference-profile ARN and the foundation model in every region the profile routes to (see `iam-policy.json`).
- **Model access is per account, per model.** Sonnet 4.6 and Haiku 4.5 worked immediately; Sonnet 5 and Opus 5 are denied on this account, and AWS Support couldn't approve them - access depends on account history and goes through an AWS account team. The availability API reports the same status for working and denied models, so the only reliable check is a real invoke. A customer planning to launch on the newest model should confirm access before committing to a date.
- **Legacy models are closed to new accounts.** A model the account hasn't used in 30 days (e.g. Sonnet 4) is blocked, so a new account can't start on an old model.
- **On-demand vs provisioned throughput.** On-demand bills per token with no commitment. Provisioned throughput reserves model capacity for a term - worth it for steady, high-volume traffic or when a latency/throughput guarantee matters, not for spiky or low-volume workloads like this one.

## Still open

- Same-prompt latency comparison, direct API vs Bedrock (planned in `NOTES.md`, not yet run).
- Re-measure with the guardrail and sentiment calls moved onto Bedrock.
