
# Commerce AI Ops Agent

A multi-tool agent that produces merchandising recommendations for an
e-commerce catalog. Given a product SKU, it gathers internal metrics,
competitor prices, and review sentiment, then recommends pricing, inventory,
and promotional actions - with a brand-voice guardrail and full observability.

Built from scratch on the raw Anthropic SDK (orchestrator-workers pattern),
then reimplemented in LangGraph for comparison (see `langgraph_version/`).

## Architecture

\`\`\`mermaid
graph TD
    SKU[Product SKU] --> O[Orchestrator LLM]
    O -->|tool| M[get_internal_metrics]
    O -->|tool| C[get_competitor_prices]
    O -->|tool| R[get_review_sentiment]
    M --> O
    C --> O
    R --> O
    O --> REC[Draft recommendation]
    REC --> G[Brand-voice guardrail]
    G --> OUT[Final recommendation]
\`\`\`

## Run

\`\`\`bash
uv sync
export ANTHROPIC_API_KEY=...
uv run python agent.py GM-001
\`\`\`

## Evaluation

Outcome evaluation against per-SKU reference expectations. See `evals/`.

## What this demonstrates

- Orchestrator-workers agent pattern (raw SDK, no framework)
- Multi-tool use where tool outputs feed subsequent tool inputs
- Evaluator-optimizer guardrail for output quality
- Full Langfuse observability (cost and latency per run)
- Outcome + light trajectory evaluation
