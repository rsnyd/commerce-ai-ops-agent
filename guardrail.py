"""Week 7 Day 4: Brand-voice guardrail as an evaluator-optimizer gate."""
from anthropic import Anthropic

BRAND_RULES = """Spices Inc brand voice:
- Warm, expert, never patronizing. Concrete before evocative.
- Forbidden words: elevate, premium, artisanal, gourmet, curated, luxurious, decadent.
- Preferred: well-made, carefully sourced, small batch, honest, fresh-ground.
- Plain hyphens, never em dashes. Specific about heat (mild, building, sharp), not vague."""

CHECK_TOOL = {
    "name": "report_check",
    "description": "Report whether the text passes brand-voice rules and provide a fix if not.",
    "input_schema": {
        "type": "object",
        "properties": {
            "passes": {"type": "boolean"},
            "violations": {"type": "array", "items": {"type": "string"}},
            "revised_text": {"type": "string", "description": "If it fails, the corrected text. If it passes, echo the original."},
        },
        "required": ["passes", "violations", "revised_text"],
    },
}


def apply_brand_guardrail(text: str) -> dict:
    client = Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=f"You check text against brand-voice rules and fix violations.\n\n{BRAND_RULES}",
        tools=[CHECK_TOOL],
        tool_choice={"type": "tool", "name": "report_check"},
        messages=[{"role": "user", "content": f"Check this recommendation:\n\n{text}"}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input