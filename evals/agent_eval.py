"""Week 7 Day 6: Agent outcome evaluation.

Week 8 Day 12: the same judge and reference set, run across every implementation
of the agent - raw SDK, LangGraph (prebuilt + custom graph), CrewAI - so the
outcome scores sit next to lines of code and latency in one comparison.

    uv run python evals/agent_eval.py                       # all implementations
    uv run python evals/agent_eval.py --impl raw-sdk langgraph-custom --trials 3

Run from the project root: tools.py reads mock_data.json relative to the cwd.
"""
import argparse
import ast
import importlib
import io
import statistics
import sys
import time
import tokenize
from pathlib import Path

from anthropic import Anthropic

# Running `python evals/agent_eval.py` puts evals/ on sys.path, not the project
# root, so `import agent` fails. This project has no [build-system], so uv never
# installs it into the venv and there is nothing else putting the root on the
# path. Same bootstrap as the Week 4 evals/ modules.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "langgraph_version"))

# The LangGraph modules do `sys.path.insert(0, "..")` before importing tools and
# guardrail, which from the project root puts ~/projects ahead of this repo. Importing
# both here first means those later imports resolve from sys.modules, never from
# whatever happens to sit in the parent directory. `observability` loads .env, which
# the LangGraph and CrewAI modules never import on their own.
import observability  # noqa: E402,F401
import tools  # noqa: E402,F401
import guardrail  # noqa: E402,F401

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

# Each implementation loads lazily, so importing CrewAI (slow, noisy) or building the
# LangGraph agents only happens for the implementations actually being run.
# `files` is what the implementation adds on top of the shared tools.py/guardrail.py -
# the part you would actually write to port the agent to that framework.
IMPLEMENTATIONS = {
    "raw-sdk": {
        "load": lambda: importlib.import_module("agent").run_agent,
        "files": ["agent.py"],
        "guardrail": True,
    },
    "langgraph-prebuilt": {
        "load": lambda: importlib.import_module("agent_prebuilt").run,
        "files": ["langgraph_version/agent_prebuilt.py"],
        "guardrail": False,
    },
    "langgraph-custom": {
        "load": lambda: importlib.import_module("agent_graph").run,
        # Reuses the @tool wrappers and system prompt from agent_prebuilt.py.
        "files": ["langgraph_version/agent_graph.py", "langgraph_version/agent_prebuilt.py"],
        "guardrail": True,
    },
    "crewai": {
        "load": lambda: importlib.import_module("crewai_demo").run,
        "files": ["crewai_demo.py"],
        "guardrail": True,
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


def code_lines(path: Path) -> int:
    """Lines that carry code: no blanks, comments, or docstrings.

    Raw line counts would mostly measure how much each file explains itself, and
    agent.py and crewai_demo.py are far chattier than the LangGraph modules.
    """
    src = path.read_text()
    docstring_lines = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) \
                and ast.get_docstring(node) is not None:
            doc = node.body[0]
            docstring_lines.update(range(doc.lineno, doc.end_lineno + 1))
    skip = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
    lines = set()
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type not in skip:
            lines.update(l for l in range(tok.start[0], tok.end[0] + 1) if l not in docstring_lines)
    return len(lines)


def evaluate(name: str, trials: int) -> list[dict]:
    """Run one implementation over every reference SKU, `trials` times each."""
    impl = IMPLEMENTATIONS[name]
    run = impl["load"]()
    rows = []
    for sku, ref in REFERENCE.items():
        for trial in range(trials):
            print(f"\n--- {name} / {sku} (trial {trial + 1}/{trials}) ---")
            start = time.perf_counter()
            # One implementation failing (rate limit, framework quirk) should cost
            # that row, not the whole comparison.
            try:
                rec = run(sku)
            except Exception as e:  # noqa: BLE001
                print(f"  [error] {type(e).__name__}: {e}")
                rows.append({"impl": name, "sku": sku, "error": f"{type(e).__name__}: {e}"})
                continue
            latency = time.perf_counter() - start
            scores = judge(sku, rec, ref)
            print(f"  addresses_required: {scores['addresses_required']}/5")
            print(f"  grounded_in_data:   {scores['grounded_in_data']}/5")
            print(f"  avoided_errors:     {scores['avoided_errors']}")
            print(f"  latency:            {latency:.1f}s")
            print(f"  reasoning: {scores['reasoning']}")
            rows.append({"impl": name, "sku": sku, "latency": latency, **scores})
    return rows


def summarize(results: dict[str, list[dict]]) -> str:
    """Markdown table of the measured dimensions, one column per implementation."""
    names = list(results)

    def ok(name):
        return [r for r in results[name] if "error" not in r]

    def mean(name, key, fmt):
        vals = [r[key] for r in ok(name)]
        return fmt.format(statistics.mean(vals)) if vals else "-"

    rows = {
        "Lines of code": [str(sum(code_lines(ROOT / f) for f in IMPLEMENTATIONS[n]["files"])) for n in names],
        "Guardrail in the flow": ["yes" if IMPLEMENTATIONS[n]["guardrail"] else "no" for n in names],
        "Addresses required (0-5)": [mean(n, "addresses_required", "{:.1f}") for n in names],
        "Grounded in data (1-5)": [mean(n, "grounded_in_data", "{:.1f}") for n in names],
        "Avoided errors": [f"{sum(r['avoided_errors'] for r in ok(n))}/{len(ok(n))}" for n in names],
        "Latency per run (s)": [mean(n, "latency", "{:.1f}") for n in names],
        "Failed runs": [str(len(results[n]) - len(ok(n))) for n in names],
    }
    lines = [
        "| Dimension | " + " | ".join(names) + " |",
        "| --- | " + " | ".join("---" for _ in names) + " |",
    ]
    lines += [f"| {dim} | " + " | ".join(vals) + " |" for dim, vals in rows.items()]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--impl", nargs="+", choices=list(IMPLEMENTATIONS), default=list(IMPLEMENTATIONS))
    parser.add_argument("--trials", type=int, default=1, help="runs per SKU per implementation")
    args = parser.parse_args()

    results = {name: evaluate(name, args.trials) for name in args.impl}

    table = summarize(results)
    print(f"\n=== Comparison ({len(REFERENCE)} SKUs x {args.trials} trial(s)) ===\n{table}")

    # Langfuse batches spans on a background thread; flush before the process exits
    # or the last runs' traces never arrive.
    observability.langfuse.flush()
