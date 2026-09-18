"""Week 8 Day 9: Commerce agent using LangGraph's prebuilt ReAct agent."""
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

import sys
sys.path.insert(0, "..")
import tools as t


# Wrap your existing functions as LangChain tools with the @tool decorator
@tool
def get_internal_metrics(sku: str) -> dict:
    """Get inventory, sales velocity, price, and reorder point for a product SKU."""
    return t.get_internal_metrics(sku)


@tool
def get_competitor_prices(product_name: str) -> dict:
    """Search competitor prices for a product by name. Returns avg/min/max."""
    return t.get_competitor_prices(product_name)


@tool
def get_review_sentiment(sku: str) -> dict:
    """Get average rating and sentiment summary for a product SKU."""
    return t.get_review_sentiment(sku)


SYSTEM = """You are a merchandising analyst for Spices Inc. Given a SKU, gather
data with the tools (call get_internal_metrics first), then recommend pricing,
inventory, and a promotional angle in under 150 words. Ground every claim in tool
data. Use plain hyphens, never em dashes."""

model = init_chat_model("claude-sonnet-4-6", temperature=0)
agent = create_agent(
    model,
    tools=[get_internal_metrics, get_competitor_prices, get_review_sentiment],
    system_prompt=SYSTEM,
)


def run(sku: str) -> str:
    result = agent.invoke({"messages": [("user", f"Produce a merchandising recommendation for SKU {sku}.")]})
    return result["messages"][-1].content


if __name__ == "__main__":
    sku = sys.argv[1] if len(sys.argv) > 1 else "GM-001"
    print(run(sku))