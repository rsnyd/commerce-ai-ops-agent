"""Week 7 Day 3: The Commerce AI Ops Agent - raw Anthropic SDK orchestration."""
import json

from anthropic import Anthropic

import tools
# At the top of agent.py
from guardrail import apply_brand_guardrail

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

def run_agent(sku: str, max_turns: int = 8) -> str:
    client = Anthropic()
    messages = [{"role": "user", "content": f"Produce a merchandising recommendation for SKU {sku}."}]

    for turn in range(max_turns):
        response = client.messages.create(
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
            return check["revised_text"]  # always return the (possibly revised) text

        if response.stop_reason == "end_turn":
            # Final answer
            return response.content[0].text

        if response.stop_reason == "tool_use":
            # Append the assistant's turn (with tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute every tool the model requested this turn
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    fn = TOOL_FUNCTIONS[block.name]
                    print(f"  -> {block.name}({block.input})")
                    result = fn(**block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            messages.append({"role": "user", "content": tool_results})

    return "Agent stopped: max turns reached without a final recommendation."


if __name__ == "__main__":
    import sys
    sku = sys.argv[1] if len(sys.argv) > 1 else "GM-001"
    print(f"Running agent for {sku}...\n")
    recommendation = run_agent(sku)
    print(f"\n=== Recommendation ===\n{recommendation}")