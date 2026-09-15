"""Week 7 Day 6: Agent outcome evaluation."""
import json
import sys
from pathlib import Path

from anthropic import Anthropic

# Running `python evals/agent_eval.py` puts evals/ on sys.path, not the project
# root, so `import agent` fails. This project has no [build-system], so uv never
# installs it into the venv and there is nothing else putting the root on the
# path. Same bootstrap as the Week 4 evals/ modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent import run_agent  # noqa: E402

client = Anthropic()

# Reference expectations per SKU (what a good recommendation must address)
REFERENCE = {
    "GM-001": {
        "must_address": ["price vs competitors", "inventory is healthy", "a promo angle grounded in positive reviews"],
        "should_not": ["recommend an urgent reorder (stock is fine)"],
    },
    "BB-002": {
        "must_address": ["flag low inventory / reorder needed", "price positioning", "a promo angle"],
        "should_not": ["claim stock is plentiful"],
    },
}

JUDGE_TOOL = {
    "name": "score",
    "description": "Score the recommendation against expectations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string"},
            "addresses_required": {"type": "integer", "minimum": 0, "maximum": 5,
                                   "description": "How well it covered the must_address points, 0-5"},
            "grounded_in_data": {"type": "integer", "minimum": 1, "maximum": 5},
            "avoided_errors": {"type": "boolean"},
        },
        "required": ["reasoning", "addresses_required", "grounded_in_data", "avoided_errors"],
    },
}


def judge(sku: str, recommendation: str, ref: dict) -> dict:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="You evaluate merchandising recommendations against expectations.",
        tools=[JUDGE_TOOL],
        tool_choice={"type": "tool", "name": "score"},
        messages=[{"role": "user", "content":
            f"SKU: {sku}\nMust address: {ref['must_address']}\nShould not: {ref['should_not']}\n\nRecommendation:\n{recommendation}"}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input


if __name__ == "__main__":
    for sku, ref in REFERENCE.items():
        rec = run_agent(sku)
        scores = judge(sku, rec, ref)
        print(f"\n=== {sku} ===")
        print(f"  addresses_required: {scores['addresses_required']}/5")
        print(f"  grounded_in_data:   {scores['grounded_in_data']}/5")
        print(f"  avoided_errors:     {scores['avoided_errors']}")
        print(f"  reasoning: {scores['reasoning']}")