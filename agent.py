"""Week 7 Day 3: The Commerce AI Ops Agent - raw Anthropic SDK orchestration.

Week 7 Day 5: instrumented with Langfuse. One run of run_agent() is one trace:

    merchandising-agent                     (agent span, the whole run)
      orchestrator-turn-1                   (generation - Sonnet decides what to call)
      get_internal_metrics                  (tool span)
      orchestrator-turn-2                   (generation)
      get_competitor_prices                 (tool span)
      get_review_sentiment                  (tool span)
        sentiment-summary                   (generation - Haiku, inside the tool)
      orchestrator-turn-3                   (generation - writes the recommendation)
      brand-guardrail                       (guardrail span)
        guardrail-check                     (generation - Sonnet checks brand voice)
"""
import json

from anthropic import Anthropic
from langfuse import observe

import tools
from guardrail import apply_brand_guardrail
from observability import langfuse, traced_messages_create

MODEL = "claude-sonnet-4-6"

# Tool schemas the model sees
TOOL_SCHEMAS = [
    {
        "name": "get_internal_metrics",
        "description": "Get current inventory, 30-day sales velocity, current price, reorder point, and days of stock remaining for a product SKU. Call this first to understand the product's current state.",
        "input_schema": {
            "type": "object",
            "properties": {"sku": {"type": "string", "description": "Product SKU, e.g. 'GM-001'"}},
            "required": ["sku"],
        },
    },
    {
        "name": "get_competitor_prices",
        "description": "Search for competitor prices for a product by its name (not SKU). Returns competitor list with prices and the average/min/max. Use the product name from get_internal_metrics.",
        "input_schema": {
            "type": "object",
            "properties": {"product_name": {"type": "string", "description": "Product name, e.g. 'Garam Masala'"}},
            "required": ["product_name"],
        },
    },
    {
        "name": "get_review_sentiment",
        "description": "Get average rating, review count, and a sentiment summary for a product SKU. Use to factor customer perception into the recommendation.",
        "input_schema": {
            "type": "object",
            "properties": {"sku": {"type": "string", "description": "Product SKU, e.g. 'GM-001'"}},
            "required": ["sku"],
        },
    },
]

# Map tool names to the actual functions
TOOL_FUNCTIONS = {
    "get_internal_metrics": tools.get_internal_metrics,
    "get_competitor_prices": tools.get_competitor_prices,
    "get_review_sentiment": tools.get_review_sentiment,
}

SYSTEM_PROMPT = """You are a merchandising analyst for Spices Inc, a small-batch spice company.

Given a product SKU, produce a concise merchandising recommendation covering:
1. Pricing: is the current price competitive? Should it change?
2. Inventory: is a reorder needed soon?
3. Promotional angle: a one-line suggestion grounded in reviews and positioning.

Use the available tools to gather data before recommending. Call get_internal_metrics
first to learn the product name and state, then gather competitor and review data as needed.

Base every claim on tool data. Do not invent numbers. Keep the final recommendation under
150 words. Use plain hyphens, never em dashes."""


def run_requested_tool(block) -> dict:
    """Execute one tool_use block the model emitted, as its own Langfuse span.

    This is the dispatcher the Langfuse tutorial calls `call_tool`. It does not
    exist until you write it - the point is that there is exactly one place where
    a tool gets executed, so one wrapper covers all three tools. The alternative,
    decorating get_internal_metrics / get_competitor_prices / get_review_sentiment
    individually in tools.py, means three decorators to keep in sync and leaves
    tools.py importing an observability stack it otherwise has no use for.

    A context manager rather than a decorator, because the span has to be named
    after the tool the model actually asked for. A decorator on this function would
    name every span "run_requested_tool" and the trace tree would be unreadable.
    """
    fn = TOOL_FUNCTIONS[block.name]
    with langfuse.start_as_current_observation(
        name=block.name, as_type="tool", input=block.input
    ) as span:
        result = fn(**block.input)
        span.update(output=result)
        return result


@observe(name="merchandising-agent", as_type="agent")
def run_agent(sku: str, max_turns: int = 8) -> str:
    # @observe already captures sku/max_turns as the span input. The metadata is
    # what makes a run findable later - Langfuse filters traces on metadata, not
    # on the input blob.
    langfuse.update_current_span(metadata={"sku": sku, "orchestrator_model": MODEL})
    # get_trace_url() reads the *currently active* span, so it only works in here -
    # called from __main__ after the agent span has closed it returns None.
    print(f"  [langfuse] {langfuse.get_trace_url()}")

    client = Anthropic()
    messages = [{"role": "user", "content": f"Produce a merchandising recommendation for SKU {sku}."}]

    for turn in range(max_turns):
        response = traced_messages_create(
            client,
            span_name=f"orchestrator-turn-{turn + 1}",
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            raw = response.content[0].text
            check = apply_brand_guardrail(raw)
            if not check["passes"]:
                print(f"  [guardrail] violations: {check['violations']}")
            # Turn count is on the agent span rather than a generation span because
            # it describes the run, not any one model call.
            langfuse.update_current_span(
                metadata={"turns_used": turn + 1, "guardrail_passed": check["passes"]}
            )
            return check["revised_text"]  # always return the (possibly revised) text

        if response.stop_reason == "tool_use":
            # Append the assistant's turn (with tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute every tool the model requested this turn
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  -> {block.name}({block.input})")
                    result = run_requested_tool(block)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            messages.append({"role": "user", "content": tool_results})

    langfuse.update_current_span(level="WARNING", status_message="max turns reached")
    return "Agent stopped: max turns reached without a final recommendation."


if __name__ == "__main__":
    import sys
    sku = sys.argv[1] if len(sys.argv) > 1 else "GM-001"
    print(f"Running agent for {sku}...\n")
    recommendation = run_agent(sku)
    print(f"\n=== Recommendation ===\n{recommendation}")

    # Langfuse batches spans on a background thread. A short script can exit before
    # the batch is sent, which looks exactly like "the instrumentation didn't work".
    langfuse.flush()
