"""Week 10 Day 2: First Bedrock call via boto3 Converse API.

Pick the model with a CLI arg or the BEDROCK_MODEL_ID env var (CLI wins).
Either an alias from MODELS or a full Bedrock model / inference profile ID:

    uv run python cloud/bedrock_hello.py                    # DEFAULT_MODEL
    uv run python cloud/bedrock_hello.py claude
    BEDROCK_MODEL_ID=claude uv run python cloud/bedrock_hello.py
    uv run python cloud/bedrock_hello.py us.amazon.nova-pro-v1:0
"""
import os
import sys

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"

# Current Claude models need inference profile IDs (us./global. prefix);
# bare model IDs fail with "on-demand throughput isn't supported".
MODELS = {
    "nova-lite": "us.amazon.nova-lite-v1:0",
    "claude": "us.anthropic.claude-sonnet-5",
}

# Nova Lite while Anthropic Marketplace access is blocked (see cloud/NOTES.md).
# Flip back to "claude" once access is enabled.
DEFAULT_MODEL = "nova-lite"


def resolve_model_id(argv: list[str], default: str = DEFAULT_MODEL) -> str:
    """CLI arg > BEDROCK_MODEL_ID env var > default; aliases expand via MODELS."""
    choice = argv[1] if len(argv) > 1 else os.environ.get("BEDROCK_MODEL_ID", default)
    return MODELS.get(choice, choice)


def main() -> None:
    model_id = resolve_model_id(sys.argv)
    client = boto3.client("bedrock-runtime", region_name=REGION)

    conversation = [
        {"role": "user", "content": [{"text": "In one sentence, what is Drupal Commerce?"}]}
    ]

    # Sonnet 5 rejects sampling params (temperature/top_p) with a 400, so only
    # send temperature to non-Anthropic models.
    inference_config = {"maxTokens": 512}
    if "anthropic." not in model_id:
        inference_config["temperature"] = 0

    print(f"Model: {model_id}\n")
    try:
        response = client.converse(
            modelId=model_id,
            messages=conversation,
            inferenceConfig=inference_config,
        )
    except ClientError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Reasoning blocks can precede the text block, so don't assume content[0].
    content = response["output"]["message"]["content"]
    print(next(block["text"] for block in content if "text" in block))
    print(f"\nUsage: {response['usage']}")
    print(f"Stop reason: {response['stopReason']}")


if __name__ == "__main__":
    main()
