"""Week 10 Day 3: Commerce agent running on Bedrock (AnthropicBedrock client)."""
import json
import sys
from pathlib import Path

from anthropic import AnthropicBedrock
from langfuse import observe

# Running `python cloud/agent_bedrock.py` puts cloud/ on sys.path, not the repo
# root - add it so the shared modules (agent, guardrail, tools) resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from guardrail import apply_brand_guardrail
from observability import langfuse, traced_messages_create

# The only real changes from agent.py: the client and the model ID
client = AnthropicBedrock(aws_region="us-east-1")
MODEL = "us.anthropic.claude-sonnet-4-6"

# TOOL_SCHEMAS, TOOL_FUNCTIONS, SYSTEM_PROMPT: identical to agent.py
# ... (import them from agent.py to avoid duplication) ...
from agent import TOOL_SCHEMAS, SYSTEM_PROMPT, run_requested_tool


# Day 5: traced the same way as agent.py, so a Bedrock run is one Langfuse trace
# with a generation span per model call. Without this the orchestrator turns were
# invisible and only the guardrail/sentiment calls showed up, as orphan traces.
# Note those two still go to the direct Anthropic API - guardrail.py and tools.py
# build their own Anthropic() client.
@observe(name="merchandising-agent-bedrock", as_type="agent")
def run_agent_bedrock(sku: str, max_turns: int = 8) -> str:
    langfuse.update_current_span(metadata={"sku": sku, "orchestrator_model": MODEL})
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
            langfuse.update_current_span(metadata={"turns_used": turn + 1})
            return apply_brand_guardrail(response.content[0].text)["revised_text"]
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_requested_tool(block)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
            messages.append({"role": "user", "content": results})
    langfuse.update_current_span(level="WARNING", status_message="max turns reached")
    return "Max turns reached."


if __name__ == "__main__":
    sku = sys.argv[1] if len(sys.argv) > 1 else "GM-001"
    print(run_agent_bedrock(sku))
    langfuse.flush()