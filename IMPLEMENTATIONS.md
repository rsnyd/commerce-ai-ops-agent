# Three Implementations, One Agent

This repo implements the same merchandising agent three ways - raw Anthropic SDK,
LangGraph (twice: prebuilt and a custom graph), and CrewAI - and scores all four
with one outcome eval: the same reference expectations, the same LLM judge, the
same two SKUs.

What is held constant: the three tool functions in `tools.py` (including the
Haiku sentiment call inside `get_review_sentiment`), the mock catalog, the
orchestrator model (`claude-sonnet-4-6`), and the brand-voice guardrail in
`guardrail.py`, which every arm except the prebuilt one runs on its output. What
is *not* held constant is the prompt - see the last note. Each framework wants the
instructions expressed its own way, and this comparison let it.

Harness: [`evals/agent_eval.py`](evals/agent_eval.py).

## 1. Raw Anthropic SDK (`agent.py`)

The orchestrator-workers loop written by hand: send the conversation, execute
every `tool_use` block the model emits, append the results, repeat until
`end_turn` or 8 turns. The guardrail is a function call in the `end_turn`
branch. Every model call - orchestrator turns, the sentiment tool, the guardrail
- goes through `traced_messages_create`, so one run is one Langfuse trace with a
dollar figure on it. Nothing is hidden, and nothing is free.

## 2. LangGraph (`langgraph_version/`)

**Prebuilt (`agent_prebuilt.py`).** `create_agent` over the same three functions
wrapped with `@tool`. The tool loop is the framework's; the file is tool wrappers,
a prompt and one `invoke`. No guardrail, so it is the only arm whose output goes
out unreviewed.

**Custom graph (`agent_graph.py`).** A two-node `StateGraph`: `agent` runs the
prebuilt ReAct loop and writes a draft into typed state, `guardrail` rewrites it
and records the violations. The guardrail is a node with an edge into it, so it
shows up in `app.get_graph().draw_mermaid()` - the handoff is part of the
structure rather than a line inside a loop. Adding a retry is one conditional
edge from `guardrail` back to `agent`.

## 3. CrewAI (`crewai_demo.py`)

Two roles in a sequential crew: a Merchandising Analyst that holds the tools and
produces a factual brief, and a Brand Copywriter that turns the brief into the
recommendation. The guardrail attaches to the copywriter's task through
`Task(guardrail=...)`, which can either replace the output (what this repo does)
or send the task back for a retry with feedback. The unit of design is the role,
not the flow: you describe who the agents are and CrewAI decides how the prompts
are assembled.

## Results

2 SKUs x 3 trials per arm, 24 runs, 0 failures. Run 2026-09-18.

| Metric                   | Raw SDK | LG prebuilt | LG custom | CrewAI |
| ------------------------ | ------- | ----------- | --------- | ------ |
| Addresses required (0-5) |     3.8 |         3.8 |       4.0 |    3.8 |
| Grounded in data (1-5)   |     4.2 |         4.0 |       4.0 |    4.3 |
| Avoided errors           |     3/6 |         3/6 |       3/6 |    3/6 |
| Mean latency / run       |   24.7s |       17.5s |     16.3s |  32.2s |
| Guardrail violations/run |     2.3 |           - |       2.0 |    0.7 |

| Dimension             | Raw SDK                          | LangGraph                                  | CrewAI                                  |
| --------------------- | -------------------------------- | ------------------------------------------ | --------------------------------------- |
| Lines of code         | 108                              | 31 (prebuilt) / 44 (custom, + prebuilt's 31) | 70                                    |
| Control over flow     | total                            | low (prebuilt) / high (custom)             | medium                                  |
| Built-in tool loop    | no (you write it)                | yes                                        | yes                                     |
| Guardrail placement   | manual: a call inside the loop   | clean: an explicit graph node              | clean: a `Task(guardrail=...)` hook     |
| Multi-agent native    | no                               | possible (subgraphs, supervisor)           | yes (core) - two roles here             |
| Tracing in this repo  | full, with cost                  | sentiment + guardrail calls only           | sentiment + guardrail calls only        |
| Debuggability         | high                             | medium                                     | lower                                   |
| Best for              | understanding, perf-critical     | production single agents                   | role-based teams                        |

The outcome scores are the least interesting rows, and that is the finding: the
four arms are indistinguishable. Every arm scored 5/5/pass on all three BB-002
trials and failed all three GM-001 trials. The split runs along the SKU, not the
framework.

Three things the numbers say that the going-in expectations did not:

1. **The GM-001 failure is the reference's, not the agents'.** All 12 GM-001 runs
   recommended a reorder, and the judge marked every one against the "should not
   recommend an urgent reorder (stock is fine)" expectation. But GM-001 has 42
   units selling 4.6 a day - 9.1 days of stock. Every implementation read the
   same numbers and reached the same defensible conclusion; the expectation was
   written from "42 is above the reorder point of 30" alone. Four frameworks
   agreeing 12 times out of 12 is a strong hint the eval is what needs fixing.
2. **CrewAI needed the guardrail least - because of its prompt, not its
   framework.** Its output averaged 0.7 guardrail violations a run with no
   forbidden words in any run; the raw and custom-graph arms averaged 2.3 and
   2.0, and used a forbidden word ("premium", every time) in 4 and 3 of their 6
   runs. The copywriter's backstory contains `BRAND_RULES`; the other arms'
   system prompts only mention hyphens and meet the brand rules for the first
   time in the guardrail. CrewAI's role structure pushed the brand voice into
   the writer's prompt, and that is a move any arm could copy.
3. **"Guardrails are awkward in CrewAI" is out of date.** In CrewAI
   1.x a task guardrail is a first-class parameter that returns
   `(passed, result)` and can trigger a retry with feedback. It is awkward only
   when the check belongs somewhere other than a task's output - between two
   tool calls, say - which LangGraph expresses as just another node.

Latency tracks call count more than framework. CrewAI is slowest because the
second agent is an extra model hop before the guardrail's. The custom graph beat
the prebuilt one despite running the guardrail, which says per-run latency here
swings more (raw ranged 16-34s) than six samples can average out.

## When to use which

**Raw SDK when you need to see everything.** It is the only arm where every call
lands in Langfuse with a cost on it, because every call goes through code this
repo owns. The price is the loop and tool dispatch the frameworks give you for
free, plus the Langfuse plumbing that makes it a trace rather than a
print statement. For a single agent this size that is a fair trade, and it is
the version to reach for when latency or token cost has to be controlled
per call.

**LangGraph when the flow is going to grow.** The custom graph is the one to
ship: state is typed, the guardrail is visible in the generated diagram, and
the next obvious features - retry on guardrail failure, a human-approval
interrupt before a price change, checkpointing - are each an edge or a
compile option rather than a rewrite of the loop. The prebuilt agent is the
fastest way to a working tool loop and the wrong place to stop.

**CrewAI when the work really is a team.** Splitting "gather the facts" from
"write it on brand" produced the cleanest copy here, and the role/task
vocabulary makes that split easy to read. For one analyst with three tools it
is overhead: the slowest arm, the least visible prompts, and a second agent
whose job a better system prompt could do.

The choice is about the shape of the workflow and who maintains it, not about
which one writes better recommendations. On this agent none of them does.

## Note on the line counts

Counts exclude blank lines, comments and docstrings (`code_lines()` in the
eval), and exclude the shared `tools.py`, `guardrail.py` and `observability.py`.
Read them as "lines you write to port the agent to this framework". The raw
108 includes its Langfuse instrumentation - the tool-span dispatcher, the
metadata updates - which the other arms do not have. The custom graph's 44
imports its tool wrappers and system prompt from `agent_prebuilt.py`, so a
standalone version is about 75.

## Note on what these numbers do not settle

Two SKUs is a smoke test, not a benchmark. Three trials each is enough to see
that the arms agree, not to rank them - the score differences are all within
one judge point on one run. The prompts differ across arms (the raw arm's
system prompt is the most detailed, the LangGraph prompt the shortest, CrewAI's
is spread across roles, goals, backstories and task descriptions), so a score
gap, had there been one, would not have been attributable to the framework
alone. And cost is not compared: the LangGraph and CrewAI orchestrator calls go
through `langchain-anthropic` and CrewAI's own provider rather than
`traced_messages_create`, so Langfuse sees only the Haiku sentiment call and
the guardrail. Wiring a Langfuse callback handler into both is the next step before
cost belongs in this table.
