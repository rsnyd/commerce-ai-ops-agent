"""Week 7 Day 4: Brand-voice guardrail as an evaluator-optimizer gate."""
import re

from anthropic import Anthropic
from langfuse import observe

from observability import traced_messages_create

BRAND_RULES = """Spices Inc brand voice:
- Warm, expert, never patronizing. Concrete before evocative.
- Forbidden words: elevate, premium, artisanal, gourmet, curated, luxurious, decadent.
- Preferred: well-made, carefully sourced, small batch, honest, fresh-ground.
- Plain hyphens, never em dashes. Specific about heat (mild, building, sharp), not vague."""

# Two of the brand rules are exact string matches, and a string scan settles them better
# than a model does: asked to check dashes, Sonnet flagged plain hyphens as em dashes and
# narrated its own second-guessing into the violations list. So the scan owns the
# mechanical rules and the model only gets the judgment calls (tone, concrete-before-
# evocative, vague sensory language) - the part a regex genuinely cannot do.
FORBIDDEN_STEMS = ["elevat", "premium", "artisanal", "gourmet", "curat", "luxurious", "decadent"]
DASHES = {"—": "em dash", "–": "en dash"}


def scan_exact_rules(text: str) -> list[str]:
    """Check the rules that are pure string matching. One entry per distinct violation."""
    violations = []
    for stem in FORBIDDEN_STEMS:
        match = re.search(rf"\b{stem}\w*", text, re.IGNORECASE)
        if match:
            violations.append(f'forbidden word: "{match.group()}"')
    for char, name in DASHES.items():
        if char in text:
            violations.append(f'{name} instead of plain hyphen: "{char}"')
    return violations


# The violations list is printed to the console and read in Langfuse, so it has to stay
# scannable: one line per issue, no reasoning, no duplicates.
REPORTING_RULES = """How to report:
- Dashes and forbidden words are already checked in code. Never report those - just fix
  every occurrence of the ones listed below in your revised text.
- Report only judgment calls: patronizing or hype tone, evocative language that arrives
  before anything concrete, vague sensory description where a specific one belongs.
- One entry per distinct phrase. If two rules describe the same phrase, report it once
  under the rule that fits best.
- Format each entry as `rule broken: "exact quote"`, 15 words max. The entry ends at the
  closing quote - never append an explanation of why it is wrong.
- Only report what you can quote verbatim. If you cannot quote it, it is not a violation.
- No reasoning, hedging, or self-correction in an entry. Decide first, then report.
- Judge the text only against the rules above, as they apply to what the text actually
  says. Do not require content the text was never meant to include.
- If nothing breaks a rule, return an empty list."""

CHECK_TOOL = {
    "name": "report_check",
    "description": "Report brand-voice judgment violations and return the corrected text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "violations": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "string",
                    "description": 'One distinct judgment violation as `rule broken: "exact quote"`, 15 words max. No reasoning.',
                },
            },
            "revised_text": {"type": "string", "description": "The full text with every violation fixed, keeping the original sections and structure. If nothing needs fixing, echo the original exactly."},
        },
        "required": ["violations", "revised_text"],
    },
}


# as_type="guardrail" gives this its own observation type in Langfuse rather than a
# generic span, so the brand-voice gate is filterable separately from the tool calls.
@observe(name="brand-guardrail", as_type="guardrail")
def apply_brand_guardrail(text: str) -> dict:
    exact_violations = scan_exact_rules(text)
    found = "\n".join(f"- {v}" for v in exact_violations) or "- none"

    client = Anthropic()
    resp = traced_messages_create(
        client,
        span_name="guardrail-check",
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=f"You check text against brand-voice rules and fix violations.\n\n{BRAND_RULES}\n\n{REPORTING_RULES}",
        tools=[CHECK_TOOL],
        tool_choice={"type": "tool", "name": "report_check"},
        messages=[{"role": "user", "content": f"A code scan already found these violations to fix:\n{found}\n\nCheck this recommendation:\n\n{text}"}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            result = block.input
            violations = exact_violations + result["violations"]
            return {
                "passes": not violations,
                "violations": violations,
                "revised_text": result["revised_text"],
            }
    # tool_choice forces the tool, so this is unreachable in practice - but callers index
    # into the result, so fail open with the original text rather than returning None.
    return {"passes": not exact_violations, "violations": exact_violations, "revised_text": text}
