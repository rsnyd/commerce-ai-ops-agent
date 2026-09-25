"""Week 10 Day 2: Same call via the AnthropicBedrock client - native Messages API shape.

Claude-only: AnthropicBedrock speaks the Anthropic Messages format, so Nova and
other non-Anthropic models won't work here. Defaults to the "claude" alias;
override with a CLI arg or BEDROCK_MODEL_ID, same as bedrock_hello.py:

    uv run python cloud/bedrock_hello_anthropic.py
    uv run python cloud/bedrock_hello_anthropic.py global.anthropic.claude-sonnet-5
"""
import sys

import anthropic
from anthropic import AnthropicBedrock

from bedrock_hello import REGION, resolve_model_id


def main() -> None:
    model_id = resolve_model_id(sys.argv, default="claude")

    # Reads AWS credentials from your environment / ~/.aws/credentials
    client = AnthropicBedrock(aws_region=REGION)

    print(f"Model: {model_id}\n")
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=512,
            messages=[{"role": "user", "content": "In one sentence, what is Drupal Commerce?"}],
        )
    except anthropic.PermissionDeniedError as e:
        # Expected until the Anthropic Marketplace agreement is in place (cloud/NOTES.md)
        print(f"ACCESS DENIED: {e.message}")
        sys.exit(1)
    except anthropic.APIStatusError as e:
        print(f"ERROR ({e.status_code}): {e.message}")
        sys.exit(1)
    except anthropic.APIConnectionError as e:
        print(f"CONNECTION ERROR: {e}")
        sys.exit(1)

    for block in response.content:
        if block.type == "text":
            print(block.text)
    print(f"\nUsage: {response.usage}")
    print(f"Stop reason: {response.stop_reason}")


if __name__ == "__main__":
    main()
