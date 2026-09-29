"""Week 10 Day 5: cost/latency per Bedrock agent run, measured from Langfuse traces.

    uv run python cloud/measure_runs.py [runs] [sku]         # run the agent, then report
    uv run python cloud/measure_runs.py --report <session>   # re-report an earlier batch

Every run in a batch shares one Langfuse session id, so the report reads back
exactly those traces rather than whatever else landed in the project today.

Latency comes from span timings, not Bedrock's `metrics.latencyMs`: that field is
only on Converse responses, and the agent uses the AnthropicBedrock (Messages) client.
Under WSL2 the VM clock runs ~6% slow and is stepped forward ~2s every ~30s, so a
single run's span latency is off by up to ~2s either way; averages over a batch hold.
"""
import statistics
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langfuse import propagate_attributes

from observability import langfuse

# USD per million tokens. Bedrock prices Sonnet 4.5+ / Haiku 4.5 at a 10% premium on
# geographic (`us.`) profiles vs `global.` - the agent uses `us.`, so that's the rate.
# The guardrail and sentiment calls still hit the direct Anthropic API (own client in
# guardrail.py / tools.py), so they're priced at direct-API rates.
BEDROCK_US_PRICES = {
    "claude-sonnet-4-6": {"input": 3.30, "output": 16.50},
    "claude-haiku-4-5": {"input": 1.10, "output": 5.50},
}
DIRECT_PRICES = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}
RUNS_PER_DAY = 1_000
DAYS_PER_MONTH = 30


def run_batch(runs: int, sku: str) -> str:
    from cloud.agent_bedrock import run_agent_bedrock

    session_id = f"bedrock-measure-{uuid.uuid4().hex[:8]}"
    for i in range(runs):
        with propagate_attributes(session_id=session_id, tags=["bedrock-measure"]):
            t0 = time.perf_counter()
            run_agent_bedrock(sku)
            print(f"  run {i + 1}/{runs} done in {time.perf_counter() - t0:.1f}s")
    langfuse.flush()
    print(f"  session: {session_id}")
    return session_id


def price(model: str, prices: dict) -> dict:
    # Langfuse stores the resolved model id; match on prefix like observability.py does
    for alias, p in prices.items():
        if alias in model:
            return p
    raise KeyError(f"no price for {model}")


def fetch_session_observations(session_id: str) -> list:
    # The v1 /traces endpoint 404s on Langfuse v4 (events_only mode) - v2
    # /observations is the only read path, and it omits usage/model unless asked.
    observations, cursor = [], None
    while True:
        page = langfuse.api.observations.get_many(
            session_id=session_id, limit=100, cursor=cursor,
            fields="core,basic,time,model,usage",
        )
        observations += page.data
        cursor = page.meta.cursor
        if not cursor or not page.data:
            return observations


def fetch_traces(session_id: str, expected: int | None) -> list:
    """Poll until ingestion has caught up - traces appear before all their spans do."""
    for _ in range(20):
        by_trace = {}
        for o in fetch_session_observations(session_id):
            by_trace.setdefault(o.trace_id, []).append(o)
        complete = [os for os in by_trace.values()
                    if any(o.name == "guardrail-check" for o in os)
                    and any(o.parent_observation_id is None for o in os)]
        if complete and (expected is None or len(complete) >= expected):
            return complete
        time.sleep(3)
    raise RuntimeError(f"Langfuse never showed {expected} complete traces for {session_id}")


def summarize(session_id: str, expected: int | None = None) -> None:
    rows = []
    for observations in fetch_traces(session_id, expected):
        gens = [o for o in observations if o.type == "GENERATION"]
        root = next(o for o in observations if o.parent_observation_id is None)
        run = {"tokens": 0, "cost": 0.0, "cost_all_bedrock": 0.0, "orch": 0, "other": 0,
               "latency": (root.end_time - root.start_time).total_seconds(),
               "model_latency": sum((g.end_time - g.start_time).total_seconds() for g in gens)}
        for g in gens:
            usage = g.usage_details or {}
            tin, tout = usage.get("input", 0), usage.get("output", 0)
            on_bedrock = g.name.startswith("orchestrator-turn")
            p = price(g.model, BEDROCK_US_PRICES if on_bedrock else DIRECT_PRICES)
            pb = price(g.model, BEDROCK_US_PRICES)
            run["tokens"] += tin + tout
            run["cost"] += (tin * p["input"] + tout * p["output"]) / 1e6
            run["cost_all_bedrock"] += (tin * pb["input"] + tout * pb["output"]) / 1e6
            run["orch" if on_bedrock else "other"] += 1
        rows.append(run)

    def avg(key):
        return statistics.mean(r[key] for r in rows)

    latencies = sorted(r["latency"] for r in rows)
    p50 = statistics.median(latencies)
    p95 = latencies[min(len(latencies) - 1, round(0.95 * (len(latencies) - 1)))]
    monthly = avg("cost") * RUNS_PER_DAY * DAYS_PER_MONTH
    monthly_bedrock = avg("cost_all_bedrock") * RUNS_PER_DAY * DAYS_PER_MONTH
    calls = sorted({(r["orch"], r["other"]) for r in rows})

    print(f"\nSession {session_id}: {len(rows)} runs\n")
    print("| Metric | Per run (avg) |")
    print("|---|---|")
    print(f"| Tokens (input + output, all calls) | {avg('tokens'):,.0f} |")
    print(f"| Cost (as routed today) | ${avg('cost'):.4f} |")
    print(f"| Cost (if every call were on Bedrock `us.`) | ${avg('cost_all_bedrock'):.4f} |")
    print(f"| Latency, end to end | {avg('latency'):.1f}s (p50 {p50:.1f}s, p95 {p95:.1f}s) |")
    print(f"| Of which model calls | {avg('model_latency'):.1f}s |")
    print(f"| Model calls | {avg('orch') + avg('other'):.1f} "
          f"({avg('orch'):.1f} orchestrator on Bedrock + {avg('other'):.1f} sentiment/guardrail on direct API) |")
    print(f"| Call-count mix seen (orch, other) | {', '.join(map(str, calls))} |")
    print(f"\nAt {RUNS_PER_DAY:,} runs/day: monthly cost = ${monthly:,.0f} as routed "
          f"(${monthly_bedrock:,.0f} all-Bedrock), p50 latency = {p50:.1f}s")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--report"]:
        summarize(sys.argv[2])
    else:
        runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        sku = sys.argv[2] if len(sys.argv) > 2 else "GM-001"
        summarize(run_batch(runs, sku), expected=runs)
