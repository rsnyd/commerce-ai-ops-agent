# Bedrock Working Notes (Week 10)

Raw notes for the Day 6 `CLOUD_DEPLOYMENT.md` write-up. Account: us-east-1, IAM user `ai_user`.

## Status

| Model | ID | Status |
|---|---|---|
| Amazon Nova Lite | `us.amazon.nova-lite-v1:0` | Works (Converse API) |
| Claude Sonnet 5 | `us.anthropic.claude-sonnet-5` | Blocked: `AccessDeniedException ... is not available for this account` |

AWS Support case opened (Account and billing) to get Anthropic Marketplace access enabled.

## Model access: what it actually takes

Bedrock "model access" is more than one switch. For a third-party (Marketplace) model like Claude:

1. **Anthropic use-case form** submitted once per account.
   Check with `aws bedrock get-use-case-for-model-access`.
2. **Marketplace agreement accepted for each model.**
   `aws bedrock get-foundation-model-availability --model-id anthropic.claude-sonnet-5` showed:
   - `authorizationStatus: AUTHORIZED`
   - `regionAvailability: AVAILABLE`
   - `agreementAvailability: NOT_AVAILABLE`, which is the blocker

   An offer exists (`aws bedrock list-foundation-model-agreement-offers`) but hasn't been accepted.
3. IAM permissions for `bedrock:InvokeModel` / `bedrock:Converse` (plus Marketplace permissions for accepting the agreement).

First-party Amazon models (Nova) skip steps 1-2, which is why Nova worked from the same credentials while every Claude model failed.

Ruled out while debugging:
- Free plan: the account is paid, with billing history.
- Payment method: updated, and it made no difference.
- IAM: fails as root too, so it isn't a policy problem.
- Console vs API: the console playground fails the same way.

## Model IDs and inference profiles

- Current Claude models need an **inference profile ID** (`us.` or `global.` prefix). The bare model ID (`anthropic.claude-sonnet-5`) fails with "on-demand throughput isn't supported".
- `us.` keeps requests inside US regions. `global.` can route them to any region. That's a **data-residency tradeoff**: `global.` gives more capacity, and `us.` is the one to tell a compliance-sensitive customer about.
- Legacy models (e.g. Sonnet 4) are blocked for accounts that haven't used them in the last 30 days. A new account can't start on an old model.
- Even while blocked, the error message names the *base* model (`anthropic.claude-sonnet-5`), not the profile ID that was requested.

## API differences seen so far

- **Converse (boto3)** is model-agnostic. The same script ran Nova and (attempted) Claude by changing only the model ID. `cloud/bedrock_hello.py` switches with a CLI arg / `BEDROCK_MODEL_ID`.
- **AnthropicBedrock** (`anthropic[bedrock]`) keeps the native Messages API shape but only works with Claude.
- The same access failure surfaces differently in each client:
  - boto3: `botocore ClientError` / `AccessDeniedException`
  - Anthropic SDK: HTTP 403, `anthropic.PermissionDeniedError`

  Error handling isn't portable between the two clients.
- Sonnet 5 rejects sampling params (`temperature`/`top_p`), so the Converse script only sends `temperature=0` to non-Anthropic models. Carrying over `temperature=0` from Nova would 400 on Claude. *(From docs, not yet verified on Bedrock because access is blocked.)*
- The Anthropic SDK also ships `AnthropicBedrockMantle`, a newer client that calls Bedrock's Messages-API endpoint instead of `bedrock-runtime` InvokeModel. It's worth trying once access works. Note that it uses `anthropic.`-prefixed IDs rather than `us.` profiles.

## Still to measure (Day 5)

- Latency: direct API vs Bedrock, same prompt.
- Cost per agent run on Bedrock pricing vs direct.
