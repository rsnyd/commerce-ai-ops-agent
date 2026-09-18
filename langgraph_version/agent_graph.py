"""Week 8 Day 10: Custom LangGraph graph - agent node + guardrail node."""
from typing import TypedDict
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END

import sys
sys.path.insert(0, "..")
from agent_prebuilt import get_internal_metrics, get_competitor_prices, get_review_sentiment, SYSTEM
sys.path.insert(0, "../..")
from guardrail import apply_brand_guardrail

model = init_chat_model("claude-sonnet-4-6", temperature=0)
inner_agent = create_agent(
    model,
    tools=[get_internal_metrics, get_competitor_prices, get_review_sentiment],
    system_prompt=SYSTEM,
)


class AgentState(TypedDict):
    sku: str
    draft: str
    final: str
    guardrail_violations: list


def agent_node(state: AgentState) -> AgentState:
    result = inner_agent.invoke({"messages": [("user", f"Recommendation for SKU {state['sku']}.")]})
    state["draft"] = result["messages"][-1].content
    return state


def guardrail_node(state: AgentState) -> AgentState:
    check = apply_brand_guardrail(state["draft"])
    state["final"] = check["revised_text"]
    state["guardrail_violations"] = check["violations"]
    return state


graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("guardrail", guardrail_node)
graph.add_edge(START, "agent")
graph.add_edge("agent", "guardrail")
graph.add_edge("guardrail", END)
app = graph.compile()


def run(sku: str) -> str:
    result = app.invoke({"sku": sku})
    if result["guardrail_violations"]:
        print(f"[guardrail] {result['guardrail_violations']}")
    return result["final"]


if __name__ == "__main__":
    sku = sys.argv[1] if len(sys.argv) > 1 else "GM-001"
    print(run(sku))
