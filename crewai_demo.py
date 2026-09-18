"""Week 8 Day 11: The merchandising agent as a CrewAI crew. Two roles, two tasks."""
import sys
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from crewai.tasks.task_output import TaskOutput
from crewai.tools import tool

import tools as t
from guardrail import BRAND_RULES, apply_brand_guardrail

# Without an explicit llm, CrewAI falls back to OpenAI (gpt-4.1-mini) and silently uses
# whatever OPENAI_API_KEY is in the shell. The "anthropic/" prefix routes to CrewAI's
# native Anthropic provider, so this runs on the same model as the raw SDK and LangGraph
# versions. No temperature: anthropic SDK 1.x removed the sampling params from
# messages.create, and CrewAI forwards temperature verbatim if you set it.
llm = LLM(model="anthropic/claude-sonnet-4-6")


# Same three functions the other versions use, wrapped as CrewAI tools. The docstring is
# the tool description the agent sees.
@tool("get_internal_metrics")
def get_internal_metrics(sku: str) -> dict:
    """Get inventory, sales velocity, price, reorder point, and days of stock left for a product SKU."""
    return t.get_internal_metrics(sku)


@tool("get_competitor_prices")
def get_competitor_prices(product_name: str) -> dict:
    """Search competitor prices for a product by name (e.g. "Garam Masala"). Returns avg/min/max."""
    return t.get_competitor_prices(product_name)


@tool("get_review_sentiment")
def get_review_sentiment(sku: str) -> dict:
    """Get average rating and a sentiment summary of customer reviews for a product SKU."""
    return t.get_review_sentiment(sku)


# CrewAI's unit of design is the role: who the agent is and what it cares about. Only the
# analyst holds tools - the copywriter works purely from the analyst's output.
analyst = Agent(
    role="Merchandising Analyst",
    goal="Gather the facts on a product's pricing, inventory, and customer sentiment",
    backstory="A data-driven analyst at Spices Inc, a small spice company. Reports only what the data shows.",
    tools=[get_internal_metrics, get_competitor_prices, get_review_sentiment],
    llm=llm,
    verbose=True,
)

copywriter = Agent(
    role="Brand Copywriter",
    goal="Turn the analysis into a clear, on-brand merchandising recommendation",
    backstory=f"Writes for Spices Inc and knows the brand voice cold.\n\n{BRAND_RULES}",
    llm=llm,
    verbose=True,
)


# CrewAI task guardrails take the TaskOutput and return (passed, result). Returning
# (True, revised_text) replaces the task's output with the fixed text - the same
# evaluator-optimizer gate as the LangGraph guardrail node. Returning (False, feedback)
# would instead send the copywriter back to retry with that feedback.
def brand_voice_guardrail(output: TaskOutput) -> tuple[bool, Any]:
    check = apply_brand_guardrail(output.raw)
    if check["violations"]:
        print(f"[guardrail] {check['violations']}")
    return True, check["revised_text"]


# {sku} is filled in from kickoff(inputs=...).
analyze_task = Task(
    description=(
        "Analyze product SKU {sku}. Call get_internal_metrics first to get the product name, "
        "then use that name for get_competitor_prices, and call get_review_sentiment."
    ),
    expected_output=(
        "A factual brief with the numbers: current price vs competitor avg/min/max, "
        "inventory, days of stock left vs reorder point, and review themes with the average rating."
    ),
    agent=analyst,
)

write_task = Task(
    description=(
        "Using the analyst's brief, write a merchandising recommendation for SKU {sku} covering "
        "pricing, inventory, and a promotional angle. Under 150 words. Ground every claim in "
        "the brief's data."
    ),
    expected_output="A recommendation with Pricing, Inventory, and Promotional angle sections.",
    agent=copywriter,
    context=[analyze_task],
    guardrail=brand_voice_guardrail,
)

crew = Crew(
    agents=[analyst, copywriter],
    tasks=[analyze_task, write_task],
    process=Process.sequential,
    verbose=True,
)


def run(sku: str) -> str:
    return crew.kickoff(inputs={"sku": sku}).raw


if __name__ == "__main__":
    sku = sys.argv[1] if len(sys.argv) > 1 else "GM-001"
    print(f"\n=== Recommendation ===\n{run(sku)}")
