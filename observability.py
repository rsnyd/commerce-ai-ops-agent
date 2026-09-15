"""Week 7 Day 5: Langfuse instrumentation shared by the agent, the tools and the guardrail.

Langfuse 4.x is the OpenTelemetry-based SDK. The v2 API that most tutorials still
show - `from langfuse.decorators import observe, langfuse_context` - does not exist
here; `langfuse.decorators` is gone and `langfuse_context.update_current_observation`
is now `langfuse.update_current_span` / `.update_current_generation` on the client
returned by `get_client()`.

Everything in this module exists for one reason: cost. Langfuse computes the dollar
figure for a run from `model` + `usage_details` on generation spans. A span that
records only latency shows $0.00, so every Anthropic call in this project - the
orchestrator, the sentiment tool, the guardrail - goes through
`traced_messages_create` rather than calling `client.messages.create` directly.
"""
import env  # noqa: F401  - import-time load of LANGFUSE_* and ANTHROPIC_API_KEY

from langfuse import get_client

# The v4 client is a process-wide singleton configured from LANGFUSE_PUBLIC_KEY /
# LANGFUSE_SECRET_KEY / LANGFUSE_HOST. Calling get_client() again returns the same
# object, so importing this module from several places is free.
langfuse = get_client()

# USD per million tokens, from the Anthropic pricing table. Langfuse can map cost
# from the model name against its own price list, but that list lags new model IDs
# and silently yields a blank cost when it misses. Pricing the spans here means the
# number in the UI is right on day one and does not depend on Langfuse's catalog.
PRICES_PER_MTOK = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


def _usage_details(usage) -> dict:
    """Anthropic usage -> Langfuse usage_details.

    `input_tokens` from Anthropic already excludes anything served from or written
    to the prompt cache, so the cache counts are additional keys rather than a
    subset - Langfuse sums the values for the displayed total and that stays correct.
    """
    details = {"input": usage.input_tokens, "output": usage.output_tokens}
    cache_read = getattr(usage, "cache_read_input_tokens", None)
    cache_write = getattr(usage, "cache_creation_input_tokens", None)
    if cache_read:
        details["cache_read_input_tokens"] = cache_read
    if cache_write:
        details["cache_creation_input_tokens"] = cache_write
    return details


def _cost_details(model: str, usage_details: dict) -> dict | None:
    """Price one call, or None if the model is not in PRICES_PER_MTOK.

    Returning None lets Langfuse fall back to its own price list rather than
    reporting a confidently wrong $0.00 for a model added here later.
    """
    # response.model is the resolved snapshot ("claude-sonnet-4-6-20250929"), so
    # match on prefix rather than requiring an exact key.
    price = next(
        (p for alias, p in PRICES_PER_MTOK.items() if model.startswith(alias)), None
    )
    if price is None:
        return None
    cached_read = usage_details.get("cache_read_input_tokens", 0)
    cached_write = usage_details.get("cache_creation_input_tokens", 0)
    input_cost = (
        usage_details["input"] * price["input"]
        + cached_read * price["input"] * 0.10  # cache reads bill at 0.1x
        + cached_write * price["input"] * 1.25  # cache writes bill at 1.25x
    ) / 1_000_000
    output_cost = usage_details["output"] * price["output"] / 1_000_000
    return {"input": input_cost, "output": output_cost}


def traced_messages_create(client, *, span_name: str, **kwargs):
    """Call client.messages.create(**kwargs) inside a Langfuse generation span.

    `span_name` is what labels the row in the trace tree - pass something that says
    which call this is ("orchestrator-turn-3", "sentiment-summary"), not the model
    name, which Langfuse shows in its own column.
    """
    with langfuse.start_as_current_observation(
        name=span_name,
        as_type="generation",
        model=kwargs["model"],
        model_parameters={"max_tokens": kwargs.get("max_tokens")},
        input={"system": kwargs.get("system"), "messages": kwargs["messages"]},
    ) as generation:
        response = client.messages.create(**kwargs)
        usage_details = _usage_details(response.usage)
        generation.update(
            # The resolved snapshot id, not the alias we sent - that is what the
            # Langfuse model-matching and our own price lookup should both see.
            model=response.model,
            output=[block.model_dump() for block in response.content],
            usage_details=usage_details,
            cost_details=_cost_details(response.model, usage_details),
            metadata={"stop_reason": response.stop_reason},
        )
        return response
