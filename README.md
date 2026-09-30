
# Commerce AI Ops Agent

A multi-tool agent that produces merchandising recommendations for an
e-commerce catalog. Given a product SKU, it gathers internal metrics,
competitor prices, and review sentiment, then recommends pricing, inventory,
and promotional actions - with a brand-voice guardrail and full observability.

The same agent is implemented three ways - raw Anthropic SDK, LangGraph and
CrewAI - over the same tools, model and guardrail, and scored by one outcome
eval, so the framework question gets answered with measurements rather than
taste. [`IMPLEMENTATIONS.md`](IMPLEMENTATIONS.md) is the comparison and when to
reach for which.

| Implementation | File | Shape |
| --- | --- | --- |
| Raw SDK | `agent.py` | hand-written orchestrator-workers loop, full Langfuse tracing |
| LangGraph prebuilt | `langgraph_version/agent_prebuilt.py` | `create_agent` ReAct loop, no guardrail |
| LangGraph custom | `langgraph_version/agent_graph.py` | `StateGraph` with agent and guardrail nodes |
| CrewAI | `crewai_demo.py` | analyst + brand copywriter crew, task guardrail |

The short version: across 24 eval runs the four are indistinguishable on outcome
scores. They differ in lines of code, latency, how visible the flow is, and how
much of it Langfuse can see.

## Architecture

```mermaid
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
```

## LangGraph version

`langgraph_version/` reimplements the same agent twice:

- `agent_prebuilt.py` - the prebuilt ReAct agent (`create_agent`), tools only,
  no guardrail.
- `agent_graph.py` - a custom `StateGraph` that makes the guardrail an explicit
  node, so the agent -> guardrail handoff is part of the graph rather than glue
  code around it.

The graph below is generated from the compiled app itself
(`app.get_graph().draw_mermaid()`), not drawn by hand:

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
        __start__([<p>__start__</p>]):::first
        agent(agent)
        guardrail(guardrail)
        __end__([<p>__end__</p>]):::last
        __start__ --> agent;
        agent --> guardrail;
        guardrail --> __end__;
        classDef default fill:#f2f0ff,line-height:1.2
        classDef first fill-opacity:0
        classDef last fill:#bfb6fc
```

The `agent` node runs the inner ReAct loop over the three tools and writes a
draft into state; the `guardrail` node rewrites that draft for brand voice and
records any violations it found.

## Run

```bash
uv sync
export ANTHROPIC_API_KEY=...
uv run python agent.py GM-001
```

LangGraph versions:

```bash
cd langgraph_version
uv run python agent_prebuilt.py GM-001    # prebuilt ReAct agent
uv run python agent_graph.py GM-001       # custom graph with guardrail node

# regenerate the Mermaid diagram above
uv run python -c "from agent_graph import app; print(app.get_graph().draw_mermaid())"
```

CrewAI version:

```bash
uv run python crewai_demo.py GM-001
```

## Evaluation

Outcome evaluation against per-SKU reference expectations, scored by an LLM
judge, run across every implementation with measured lines of code and latency
alongside the scores:

```bash
uv run python evals/agent_eval.py                                   # all four
uv run python evals/agent_eval.py --impl raw-sdk langgraph-custom --trials 3
```

Results and caveats are in [`IMPLEMENTATIONS.md`](IMPLEMENTATIONS.md).

## Cloud Deployment

The agent runs against two targets: the direct Anthropic API (`agent.py`) and
AWS Bedrock (`cloud/agent_bedrock.py`). The Bedrock port changes only the client
constructor and the model ID - the orchestration loop, tools, prompt and
guardrail are shared - and is traced in Langfuse the same way.

Bedrock is what an enterprise customer usually asks for: spend on the existing
AWS bill, IAM instead of API keys, CloudTrail audit, and `us.` inference
profiles to keep requests inside US regions.
[`cloud/CLOUD_DEPLOYMENT.md`](cloud/CLOUD_DEPLOYMENT.md) covers the migration,
the least-privilege IAM policy, regional and model-access gotchas, guardrail
layering, and measured cost and latency: 5 model calls and ~$0.03 per run,
~$900/month at 1,000 runs/day ([`cloud/cost_analysis.md`](cloud/cost_analysis.md)).

One caveat, documented there: the orchestrator runs on Bedrock, but the
guardrail and sentiment calls still use the direct API client.

```bash
# needs AWS credentials with the policy in cloud/iam-policy.json
uv run python cloud/agent_bedrock.py GM-001
uv run python cloud/measure_runs.py 10 GM-001   # cost/latency table from Langfuse
```

## What this demonstrates

- Orchestrator-workers agent pattern (raw SDK, no framework)
- Multi-tool use where tool outputs feed subsequent tool inputs
- Evaluator-optimizer guardrail for output quality
- The same agent across raw SDK, LangGraph and CrewAI, compared on one eval
- The guardrail as a loop call, a graph node, and a CrewAI task guardrail
- Full Langfuse observability on the raw SDK path (cost and latency per run)
- Outcome evaluation with an LLM judge against per-SKU reference expectations
- The same agent running on the direct Anthropic API and on AWS Bedrock, with
  least-privilege IAM and measured per-run cost and latency
