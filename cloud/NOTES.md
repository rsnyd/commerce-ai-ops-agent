# Bedrock Working Notes (Week 10)

Raw notes for the Day 6 `CLOUD_DEPLOYMENT.md` write-up. Account: us-east-1, IAM user `ai_user`.

## Status

Tested 2026-09-28 with real Converse calls (alias in `cloud/bedrock_hello.py` in parentheses):

| Model | ID | Status |
|---|---|---|
| Amazon Nova Lite | `us.amazon.nova-lite-v1:0` | Works (`nova-lite`) |
| Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` | Works (`claude`), **used for Week 10** |
| Claude Sonnet 4.5 | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Works |
| Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Works (both clients) |
| Claude Sonnet 5 | `us.anthropic.claude-sonnet-5` | **Denied** (`sonnet-5`): `AccessDeniedException ... is not available for this account` |
| Claude Opus 5 | `us.anthropic.claude-opus-5` | **Denied**, same error |

## Model access: what it actually takes

Bedrock "model access" is more than one switch. For a third-party (Marketplace) model like Claude:

1. **Anthropic use-case form** submitted once per account.
   Check with `aws bedrock get-use-case-for-model-access`.
2. **Per-account, per-model approval by AWS.** The newest models have higher eligibility requirements. AWS Support's answer on Sonnet 5 (paraphrased):
   - it "requires separate internal approval evaluated on a per-account basis"
   - access "might depend on regional factors, payment history, and account usage"
   - they "can't approve your request"
   - "accessibility is subject to change automatically as time passes"
   - the only other route is an AWS Account Manager or AWS Sales

   So a new or low-usage account can get older Claude models right away but be denied the newest ones.
3. IAM permissions for `bedrock:InvokeModel` (which also covers Converse).

First-party Amazon models (Nova) skip steps 1-2.

**The availability API doesn't show step 2.** `aws bedrock get-foundation-model-availability` returns the same result for *every* Claude model, working or denied:
- `agreementAvailability: NOT_AVAILABLE`
- `authorizationStatus: AUTHORIZED`
- `entitlementAvailability: AVAILABLE`
- `regionAvailability: AVAILABLE`

I initially read `agreementAvailability` as the blocker, but it's a red herring: Sonnet 4.6 and Haiku 4.5 work despite it. The only reliable check is a real invoke, one cheap Converse call per model.

Ruled out while debugging Sonnet 5:
- Free plan: the account is paid, with billing history.
- Payment method: updated, and it made no difference.
- IAM: fails as root too, so it isn't a policy problem.
- Console vs API: the console playground fails the same way.

## Model IDs and inference profiles

- Current Claude models need an **inference profile ID** (`us.` or `global.` prefix). The bare model ID (`anthropic.claude-sonnet-5`) fails with "on-demand throughput isn't supported".
- `us.` keeps requests inside US regions. `global.` can route them to any region. That's a **data-residency tradeoff**: `global.` gives more capacity, and `us.` is the one to tell a compliance-sensitive customer about.
- Legacy models (e.g. Sonnet 4) are blocked for accounts that haven't used them in the last 30 days. A new account can't start on an old model.
- The denial error names the *base* model (`anthropic.claude-sonnet-5`), not the profile ID that was requested.
- IAM for inference profiles (Day 4): a `us.` profile routes across several US regions, so a least-privilege policy has to allow the inference-profile ARN *and* the foundation model in every region it routes to. A `foundation-model/...` ARN in us-east-1 alone isn't enough.

## API differences seen so far

- **Converse (boto3)** is model-agnostic. The same script ran Nova and (attempted) Claude by changing only the model ID. `cloud/bedrock_hello.py` switches with a CLI arg / `BEDROCK_MODEL_ID`.
- **AnthropicBedrock** (`anthropic[bedrock]`) keeps the native Messages API shape but only works with Claude.
- The same access failure surfaces differently in each client:
  - boto3: `botocore ClientError` / `AccessDeniedException`
  - Anthropic SDK: HTTP 403, `anthropic.PermissionDeniedError`

  Error handling isn't portable between the two clients.
- Sonnet 5 and newer reject sampling params (`temperature`/`top_p`), so the Converse script only sends `temperature=0` to non-Anthropic models. Carrying `temperature=0` over from Nova would 400 on those models. Sonnet 4.6 still accepts it. *(The Sonnet 5 behavior comes from the docs; I can't test it on this account.)*
- The Anthropic SDK also ships `AnthropicBedrockMantle`, a newer client that calls Bedrock's Messages-API endpoint instead of `bedrock-runtime` InvokeModel. It's worth trying now that Claude access works. Note that it uses `anthropic.`-prefixed IDs rather than `us.` profiles.

## Still to measure (Day 5)

- Latency: direct API vs Bedrock, same prompt.
- Cost per agent run on Bedrock pricing vs direct.
