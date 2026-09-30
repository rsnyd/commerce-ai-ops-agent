# Study Guide: Weeks 1-10

A review guide for everything through Week 10. It follows the walkthroughs in
`docs/walkthroughs/`, but where your code or measured results differ from the
walkthrough, it goes with what you actually built and measured.

Weeks 7-9 (agents, frameworks, MCP) get the most space because that is where the
interviews go. Everything else is here so you can review it quickly.

**How to use it**

1. Read the "Core ideas" list for a phase and see whether you can explain each one out loud without notes.
2. Answer the self-test questions before opening the answers.
3. For Weeks 7-9, do the "rebuild from memory" drills. If you can write the agent loop and the traced helper on a blank page, you understand them.

## Repos

All of them live under `~/projects/`. The local links are relative to this file, so they work in your editor. The GitHub links work from anywhere.

| Repo | Weeks | Local | GitHub |
|---|---|---|---|
| llm-fundamentals | 1 | [~/projects/llm-fundamentals](../../llm-fundamentals) | private |
| cert-rag-cli | 2-6 | [~/projects/cert-rag-cli](../../cert-rag-cli) | [rsnyd/cert-rag-cli](https://github.com/rsnyd/cert-rag-cli) |
| drupal-rag-cli | 3-4 (earlier Drupal version) | [~/projects/drupal-rag-cli](../../drupal-rag-cli) | [rsnyd/drupal-rag-cli](https://github.com/rsnyd/drupal-rag-cli) |
| commerce-ai-ops-agent | 7, 8, 10 | [~/projects/commerce-ai-ops-agent](..) | [rsnyd/commerce-ai-ops-agent](https://github.com/rsnyd/commerce-ai-ops-agent) |
| drupal-mcp-server | 9 | [~/projects/drupal-mcp-server](../../drupal-mcp-server) | [rsnyd/drupal-mcp-server](https://github.com/rsnyd/drupal-mcp-server) |

Key documents in those repos:
- Weeks 3-4 results: [cert-rag-cli/evals/EVAL_REPORT.md](https://github.com/rsnyd/cert-rag-cli/blob/main/evals/EVAL_REPORT.md)
- Week 5 framework comparison: [cert-rag-cli/FRAMEWORKS.md](https://github.com/rsnyd/cert-rag-cli/blob/main/FRAMEWORKS.md)
- Week 6 fine-tuning write-up: [cert-rag-cli/finetune/FINE_TUNING_NOTES.md](https://github.com/rsnyd/cert-rag-cli/blob/main/finetune/FINE_TUNING_NOTES.md)
- Week 8 agent comparison: [IMPLEMENTATIONS.md](../IMPLEMENTATIONS.md)
- Week 9 blog draft: [drupal-mcp-server/BLOG_POST_DRAFT.md](https://github.com/rsnyd/drupal-mcp-server/blob/main/BLOG_POST_DRAFT.md)
- Week 10 deployment and cost: [cloud/CLOUD_DEPLOYMENT.md](../cloud/CLOUD_DEPLOYMENT.md) and [cloud/cost_analysis.md](../cloud/cost_analysis.md)
- The walkthroughs themselves: [docs/walkthroughs/](walkthroughs/)

---

## Contents

- [Course map](#course-map)
- [Weeks 1-2](#weeks-1-2)
- [Weeks 3-4](#weeks-3-4)
- [Weeks 5-6](#weeks-5-6)
- [Weeks 7-9: Agents, frameworks, MCP (the core)](#weeks-7-9-agents-frameworks-mcp)
  - [Week 7: The raw-SDK agent](#week-7-the-raw-sdk-agent)
  - [Week 8: LangGraph and CrewAI](#week-8-langgraph-and-crewai)
  - [Week 9: The Drupal MCP server](#week-9-the-drupal-mcp-server)
  - [Weeks 7-9 interview drill](#weeks-7-9-interview-drill)
  - [Rebuild-from-memory drills](#rebuild-from-memory-drills)
- [Week 10: Bedrock](#week-10-bedrock)
- [Cross-cutting lessons](#cross-cutting-lessons)
- [Glossary](#glossary)

---

## Course map

| Weeks | Theme | Repo | What you leave with |
|---|---|---|---|
| 1 | LLM API fundamentals | `llm-fundamentals` | Messages API, tokens, temperature, tool use, structured output, caching, cost |
| 2 | RAG from scratch | `cert-rag-cli` | Clause-aware ingestion and chunking, Voyage + Chroma, refusal-first answering |
| 3 | Evaluation | `cert-rag-cli/evals` | Golden set, deterministic metrics, five-axis judge, EVAL_REPORT |
| 4 | Observability + advanced retrieval | `cert-rag-cli` | Langfuse, BM25 hybrid + RRF, reranking. Vanilla stayed in production |
| 5 | Frameworks | `cert-rag-cli` | LCEL and LangGraph ports, grade-and-rewrite agentic RAG |
| 6 | Fine-tuning | `cert-rag-cli/finetune` | QLoRA brand-voice adapter `rsnyd/spice-voice-lora` and a three-arm eval |
| **7** | **Agents (raw SDK)** | `commerce-ai-ops-agent` | **Orchestrator loop, 3 tools, guardrail, tracing, eval** |
| **8** | **Agent frameworks** | `commerce-ai-ops-agent` | **LangGraph prebuilt and custom, CrewAI, measured comparison** |
| **9** | **MCP** | `drupal-mcp-server` | **Published server (v0.1.0): 3 tools + 1 resource, blog draft** |
| 10 | Cloud (Bedrock) | `commerce-ai-ops-agent/cloud` | Bedrock port, least-privilege IAM, measured cost and latency, SA document |

**The through-line:** each phase reuses the one before it.
- The Week 1 tool loop becomes the Week 7 agent.
- Week 1's forced-tool structured output becomes the Week 3 judge, the Week 7 guardrail and the agent eval.
- Weeks 3-4 evals and tracing become the Week 7-8 comparison method.
- Week 5's LangGraph becomes Week 8's custom graph.
- Week 6's brand-voice rubric becomes Week 7's guardrail rules.
- Weeks 2-4 RAG is the planned backend for Week 9's `explain_hook`.

---

# Weeks 1-2

Code: [~/projects/llm-fundamentals](../../llm-fundamentals) (Week 1, private repo) and [~/projects/cert-rag-cli](../../cert-rag-cli) ([GitHub](https://github.com/rsnyd/cert-rag-cli)) (Week 2).

**Week 1** (`llm-fundamentals`): eight single-concept scripts and 40+ raw API calls. **Week 2** (`cert-rag-cli`): a framework-free RAG over SQF Fundamentals 1.1 documents that cites clauses and refuses when the answer isn't there.

## Core ideas: Week 1

- **The Messages API is stateless.** The model remembers nothing between calls, so the client resends the full history every time. This is the most important mental model in the course. If you drop the assistant turn from the history, the model "forgets" what it said.
- **Tokens** are about 4 characters or 0.75 words each. `1234567` is 2 tokens and `1,234,567` is 5. Output costs roughly 4-5x input. Sonnet 4.6 has a 200K context window.
- **Temperature** ranges 0-1 on Anthropic and 0-2 on OpenAI. Use about 0 for extraction, classification and code, and 0.7-1.0 for brainstorming. 0 means "nearly deterministic," not guaranteed identical.
- **Vendor parity:** the two APIs share about 90% of their shape. Anthropic uses `messages.create` and `content[0].text` and requires `max_tokens`. OpenAI uses `chat.completions.create` and `choices[0].message.content`.
- **The tool-use loop** (`weather_tool.py`) is the seed of everything in Weeks 7-9. The model never runs a tool itself: it returns `stop_reason: tool_use`, you run the function, and you send back a `tool_result` with the matching `tool_use_id`.
- **Structured output** (`extract_orders.py`): a forced `tool_choice` makes `input_schema` your output schema.
- **Prompt caching** (`caching_demo.py`): put `cache_control: {"type": "ephemeral"}` on a long, stable prefix.
  - The cache lasts about 5 minutes.
  - Reads cost about 0.1x the input price.
  - The first call reports `cache_creation_input_tokens`; later calls report `cache_read_input_tokens`.
  - The prefix has to exceed a minimum length.
- **Cost formula** (`cost_calc.py`): `(input − cache_read)·p_in + cache_read·p_cache + output·p_out`, all per million tokens.

## Core ideas: Week 2

- **RAG** is retrieve → augment → generate. It exists because of context-window limits, data freshness, and the need to ground answers.
- **Ingestion** (`ingest.py`):
  - PyMuPDF for PDFs and python-docx for Word files, with table cells joined by ` | `.
  - PDFs averaging under 50 characters per page are treated as scanned and OCR'd with `ocrmypdf`.
  - Lines that repeat on 60% or more of pages are stripped as boilerplate.
  - A `MANIFEST` sets `doc_type` and `edition`.
- **Tracked-changes bug:** `Paragraph.text` silently skips text inside `<w:ins>` (tracked insertions). The fix is to walk every `<w:t>` element. Silent partial extraction is the worst kind of failure, because answers stay confident while a requirement is missing.
- **Clause-aware chunking** (`chunk.py`):
  - Two header forms: inline (`2.4.3.1 Title`) and standalone (a bare number on its own line).
  - Sub-splits at `MAX_CHARS=2400` with 200 characters of overlap.
  - Result: 971 chunks. 816 get their clause from a header, 87 from the filename, and 68 have none.
- **Embedding:** `voyage-3-lite`, with `input_type="document"` for chunks and `"query"` for questions. Chroma uses cosine distance.
  - The free tier allows 3 requests per minute, so batches of 8 with a 21s sleep take about 45 minutes.
  - Chroma rejects `None` metadata values.
- **Answering:** a refusal-first system prompt ("Not found in the provided documents") and a required `(source, clause, p.page)` citation.
  - `TOP_K` went from 5 to 14 because clause chunks are small (about 690 characters). Completeness rose from 3.85 to 4.24.

## What differs from the walkthrough

- Week 1 scripts use a Drupal Commerce framing rather than SQF.
- `hello.py` has no `load_dotenv()`.
- The optional second weather tool wasn't added.
- The full clause chunker landed in Week 3 (`524799f`), not Week 2.
- The `<w:ins>` fix came later (`f6bc8be`).
- The SQF source documents remain in git history even though they were later removed from the repo.

<details><summary><b>Self-test: Weeks 1-2</b></summary>

1. *Why resend the history each call?* The API is stateless.
2. *Which usage fields prove caching worked?* `cache_creation_input_tokens` on the first call, then `cache_read_input_tokens`.
3. *What is the guaranteed way to get structured output?* Forced tool_choice with an input_schema. Read `block.input`.
4. *Why walk `<w:t>` instead of `Paragraph.text`?* Text inside `<w:ins>` is dropped otherwise. `<w:delText>` is excluded automatically.
5. *Why chunk on clauses rather than fixed windows?* A clause is an auditable requirement, and a fixed window blurs requirements together and loses citation metadata.
6. *Why BATCH=8 + 21s sleep?* The Voyage free tier allows 3 requests per minute and 10K tokens per minute.
7. *Why TOP_K=14?* Chunks are small. At 14, completeness rose to 4.24 while citation stayed around 97%.
8. *What must happen on an out-of-corpus question (for example, OSHA fines)?* A refusal. A confident answer is a failure.
</details>

---

# Weeks 3-4

Code: [~/projects/cert-rag-cli](../../cert-rag-cli) ([GitHub](https://github.com/rsnyd/cert-rag-cli)), in `evals/`, `retrievers/` and `tracing.py`. There's also an earlier Drupal version at [~/projects/drupal-rag-cli](../../drupal-rag-cli) ([GitHub](https://github.com/rsnyd/drupal-rag-cli)).

**Week 3:** build a measuring instrument for the RAG. **Week 4:** tracing, then hybrid retrieval and reranking, measured against each other.

## Core ideas: evaluation (Week 3)

- **Why evals:** output isn't deterministic, so `assert response == expected` doesn't work. You need four things: a golden set, a scoring function, a baseline, and stored results.
- **Golden set** (`evals/golden.jsonl`): 34 scored questions (11 easy, 12 medium, 11 hard) plus 5 refusal probes, 39 rows in total.
  - **The constraint is coverage of all 14 requirement areas.** The difficulty split is reported, not targeted.
  - IDs are slugs (`internal-audits-m1`), not counters.
- **The clause is the ground truth.** Whether the right clause was retrieved can be checked without a judge.
- **`expected_clause` has to be parsed.** 25 of the 34 records use a list or range (for example `2.1.2.1-6`).
- **Probes** sound like they belong in the corpus but don't. The reference answer starts with "Not found..." and names the near miss.
- **Asymmetric cost:** in compliance, a fluent answer citing the wrong clause is worse than a refusal.
- **Five-axis judge** (Sonnet 4.6 with a forced `score_answer` tool): factual, completeness, relevance, **citation**, **grounding**.
  - **One defect, one axis.** A wrong clause lowers citation only; an invented requirement lowers grounding and factual.
  - Reasoning comes before the scores.
  - **Calibrate the judge** with three cases: a correct answer (expect all 5s), the right answer with the wrong clause (citation 1-2), and a fabricated detail (grounding 1-2).
- **Deterministic metrics** (`metrics.py`):
  - `clause_hit_at_k` matches on **integer segments**, because as strings `"2.1.10".startswith("2.1.1")` is true.
  - `is_refusal` accepts the literal marker, or a reference to the documents plus a negation **in the opening sentence**. A phrase-list version moved the refusal rate 20 points with no change in behavior.
  - `citation_grounding` returns **`None`, not 0**, when nothing is cited.
  - `answer_cites_expected_clause` works with any chunker.
- **Noise floor:** two identical runs drifted by at most 0.06, so only changes above about 0.1 count as signal.

## Core ideas: tracing and retrieval (Week 4)

- **Langfuse:** the SDK is a no-op without keys. `tracing.py` checks credentials at startup, because otherwise a bad key only produces 401s on a background thread. Traces are tagged with the git SHA as the release, and each eval run is one session.
- **Why hybrid retrieval:** embeddings handle paraphrase well but exact identifiers badly (clause numbers, "corrective" vs "preventative"). BM25 is TF-IDF with term saturation and length normalization.
- **RRF:** each document scores `Σ 1/(rank + 60)` across the lists it appears in. Raw score scales are ignored.
- **Tokenizer fix:** keep dotted tokens whole (`2.5.5`).
- **Fusion join key:** use the full text. A 100-character prefix merged two SOPs that start with the same introduction.
- **Rerank** (`rerank-2.5`, a cross-encoder): candidates are trimmed to a **token budget of 6000**, not a fixed count, because chunk sizes vary 7x and the free tier caps tokens at 10K per minute.
- **Pacing plus retry:** one shared `paced_call` gate (21s spacing). Back off 10/20/40s, capped at 60s. Retry only transient error types.

## Your results (`cert-rag-cli/evals/EVAL_REPORT.md`)

Source: [EVAL_REPORT.md](https://github.com/rsnyd/cert-rag-cli/blob/main/evals/EVAL_REPORT.md)

**Baseline (k=5):**

| Metric | Result |
|---|---|
| Probe refusal | 5/5 |
| False refusal | 1/34 |
| hit@3 | 97.1% |
| Cites expected clause | 97.1% |
| Overall | 4.44 |

**Fixed 2000-character window:**
- hit@3 dropped to 0%. That's an artifact: those chunks have no `clause` field.
- The real signal is that cites-expected fell from 97.1% to 73.5% (p=0.022).

**Strategies at k=14:**

| | Vanilla | Hybrid | Rerank |
|---|---|---|---|
| Overall | 4.52 | 4.46 | 4.55 |
| hit@1 | 85.3% | 58.8% | 58.8% |

Everything is within noise. BM25 favored parent section chunks over the specific sub-clause, so **vanilla stayed in production.**

**The earlier Drupal corpus** (`drupal-rag-cli`) went the other way: rerank 4.32 vs vanilla 4.11. The same technique gave different results on different corpora.

<details><summary><b>Self-test: Weeks 3-4</b></summary>

1. *Why add citation and grounding axes?* An answer can be right but cite the wrong clause, or invent a specific detail. The standard three axes catch neither.
2. *Why match clauses on integer segments?* String prefixes treat 2.1.10 as a child of 2.1.1.
3. *Why does citation_grounding return None?* A correct refusal cites nothing and shouldn't be penalized.
4. *A chunker scored 0% hit@3. Was it broken?* No, its chunks had no clause field. Use answer_cites_expected_clause instead.
5. *What is the noise floor, and why does it matter?* 0.06 drift between identical runs, so treat anything under about 0.1 as noise.
6. *What is RRF, and why use it?* Σ 1/(rank+60). It's independent of scale, so cosine and BM25 scores can be combined.
7. *Why does rerank use a token budget?* The 10K TPM cap, combined with a 7x variance in chunk size.
8. *Why did vanilla stay?* The alternatives were within noise, and BM25 promoted parent sections over specific sub-clauses.
9. *What if better retrieval drops probe refusal from 5/5 to 3/5 while overall rises 0.2?* That's a regression in a compliance setting.
10. *How is Langfuse misconfiguration caught?* A startup auth check. The eval runner refuses to start with broken keys.
</details>

---

# Weeks 5-6

Code: [~/projects/cert-rag-cli](../../cert-rag-cli) ([GitHub](https://github.com/rsnyd/cert-rag-cli)), in `langchain_rag.py`, `langgraph_rag.py` and `finetune/`. The adapter is on Hugging Face as `rsnyd/spice-voice-lora`.

**Week 5:** port the SQF RAG to LCEL and LangGraph and measure all three. **Week 6:** understand fine-tuning well enough to talk a customer out of it, and train one QLoRA adapter.

## Core ideas: frameworks (Week 5)

- **LCEL:** `prompt | model | parser`. Every part is a `Runnable` (`invoke`, `stream`, `batch`, async).
  - The RAG shape is `{"context": retriever, "question": RunnablePassthrough()} | ...`.
  - Use `RunnablePassthrough.assign` to carry the chunks through so you don't retrieve twice.
  - Ignore pre-1.0 classes (`LLMChain`, `RetrievalQA`).
- **Keep your own chunker.** `RecursiveCharacterTextSplitter` would cut across clauses and lose citation metadata.
- **Single source of truth:** import the prompt, model, TOP_K and formatter from `ask.py`. If the prompt drifts between versions, the difference shows up as a fake "framework effect."
- **LangGraph agentic RAG** (`langgraph_rag.py`): retrieve → grade → generate, or rewrite and loop.
  - `MAX_ATTEMPTS=2`.
  - Rewrite the *current* question, but answer the *original*.
- **Gotchas you hit:**
  - `langchain_voyageai` has `max_retries=0`, so a 429 escapes. The fix is a custom `PacedVoyageEmbeddings`.
  - A `("system", ...)` tuple is parsed as a template, so braces break it. Use `SystemMessage`.
  - Create the Langfuse CallbackHandler for each call, not once per module.
  - Setting temperature on one path only creates a fake difference, and newer models reject temperature anyway.
- **Your result (`FRAMEWORKS.md`):**
  - Compliance metrics were identical to the decimal (probe refusal 100%, false refusal 2.9%, hit@3 97.1%).
  - Overall: raw 4.58, LCEL 4.54, LangGraph 4.60.
  - The loop fired on 6 of 39 records and tripled probe latency (62s vs 20s).
  - **Frameworks change developer experience, not answer quality.** Raw stays in production. This is the same conclusion you reached with agents in Week 8.

## Core ideas: fine-tuning (Week 6)

- **Fine-tuning teaches behavior, not facts.** Tone, format and structure, yes. Knowledge belongs in RAG.
- **Full fine-tuning vs LoRA vs QLoRA:**
  - Full fine-tuning of a 7B model needs about 84GB and risks catastrophic forgetting.
  - LoRA freezes the base and trains under 1% of parameters (an adapter of about 100MB).
  - QLoRA uses a 4-bit base, so an 8B model fits a 16GB T4 with a quality gap of about 1-2%.
- **Decision tree:**
  - Facts → RAG.
  - Style → prompting and few-shot first, LoRA only if that's inconsistent or too long.
  - Both → combine them.
  - The default answer for most business problems is "RAG or better prompting."
- **Data quality matters more than quantity.** Derive the rubric **from the corpus.** The template banned "gourmet," but the real catalog uses it 43 times.
- **Three-arm eval:** base vs few-shot vs fine-tune. A fine-tune only earns its cost if it beats a *good prompt*.
- **What you actually trained:**
  - 454 real descriptions (439 train / 15 test).
  - `max_seq_length=2048`, because 512 would truncate 33% of records and drop their EOS token.
  - 2 epochs instead of `max_steps=60`.
  - Base (not Instruct) Llama 3.1 8B, Alpaca format.
- **Results** (voice / structure / fabricated names per description):

  | | Voice | Structure | Fabricated names |
  |---|---|---|---|
  | base | 1.53 | 1.27 | 0.00 |
  | few-shot | 1.87 | 2.33 | 1.00 |
  | fine-tune | 3.07 | 4.20 | 1.87 |

  The fine-tune beat prompting, and **fabrication rose with fluency**.
- **Data leak you caught:** the eval was scoring an outdated test split whose products were in the current training set. The fix was `assert_held_out()`.

<details><summary><b>Self-test: Weeks 5-6</b></summary>

1. *What does LCEL's `|` give you?* A Runnable with invoke, stream, batch and async for free.
2. *When LangGraph over LCEL?* When you need loops, branches, state, or a human in the loop. LCEL is acyclic.
3. *Did agentic RAG reduce false refusals?* No: 2.9% in all arms. It added latency on probes.
4. *A customer wants the model to "know our products." Fine-tune?* No, use RAG. Your adapter invented 1.87 names per description.
5. *Why a few-shot arm?* A fine-tune has to beat a good prompt, not just the base model.
6. *Why is max_seq_length=512 dangerous?* It silently truncates records and drops EOS, which teaches the model never to stop.
7. *LoRA vs QLoRA?* QLoRA runs LoRA over a 4-bit quantized base, so it needs roughly 10x less hardware.
8. *What's the common conclusion of Week 5 and Week 8?* Frameworks change developer experience, not answer quality.
</details>

---

# Weeks 7-9: Agents, frameworks, MCP

**What you built**

- `commerce-ai-ops-agent`: a merchandising agent that takes a SKU and returns pricing, inventory and promo recommendations. It has three tools, a brand-voice guardrail, Langfuse tracing and an LLM-judge eval. You built it four ways: raw SDK, LangGraph prebuilt, LangGraph custom graph, and CrewAI.
- `drupal-mcp-server` (tagged `v0.1.0`): three tools and one resource for Drupal development, usable from Claude Desktop and Claude Code.

**The idea behind the whole phase:** an agent is an LLM in a loop with tools and a goal. Frameworks, MCP and guardrails are all layers on top of that loop. Once you can write the loop by hand, the rest is choosing which layers you need.

---

## Week 7: The raw-SDK agent

### 7.1 The seven patterns (from Anthropic's "Building Effective Agents")

You should be able to name all seven, say when to use each, and say which one your agent uses.

| # | Pattern | Shape | Use when | Where it appears in your work |
|---|---------|-------|----------|--------------------------|
| 1 | **Augmented LLM** | One call, plus retrieval, tools or memory | Always: it is the building block | Every RAG query in Weeks 3-6 |
| 2 | **Prompt chaining** | Fixed sequence of calls | The subtasks are known and sequential | - |
| 3 | **Routing** | Classify the input, then send it to a specialist | Inputs fall into distinct categories | - |
| 4 | **Parallelization** | Sectioning (split the work) or voting (same task N times) | You need speed, or several perspectives combined | 3 trials per arm in the eval is informal voting |
| 5 | **Orchestrator-workers** | A central LLM decides the subtasks on the fly and delegates | You can't predict the subtasks ahead of time | **The Commerce agent** |
| 6 | **Evaluator-optimizer** | Generate, critique, revise | The criteria are clear and iterating helps | **The brand-voice guardrail**, and Week 5's grade-and-rewrite |
| 7 | **Autonomous agent** | Open-ended plan-and-act loop | The path is unknowable and you can tolerate unpredictability | - |

**The judgment call interviewers look for: use the simplest pattern that works.** More autonomy costs more, adds latency, and makes behavior less predictable.

**Why orchestrator-workers for this agent?** The model decides which tools to call, and one tool's output feeds the next tool's input: `get_internal_metrics` returns the product *name*, and `get_competitor_prices` needs that name, not the SKU. That dependency is decided at run time, which makes it orchestration rather than a fixed chain.

**Is it a strict fit?** Not quite. The three "workers" are mostly plain functions, not worker LLMs (only the sentiment tool calls a model). A fair description is "a single tool-using agent in an orchestrator-workers shape." Saying that yourself in an interview shows you understand the taxonomy rather than just reciting it.

### 7.2 Tools: build them standalone first

Code: [tools.py](../tools.py), [mock_data.json](../mock_data.json)

`tools.py` has three functions. Each one works with no LLM involved (`uv run python tools.py`).

| Tool | Input | Returns | Notes |
|------|-------|---------|-------|
| `get_internal_metrics` | `sku` | inventory, 30-day sales, price, reorder point, **`below_reorder_point`**, **`units_above_reorder_point`**, **`days_until_reorder_point`**, `days_of_stock_left` | Mock data from `mock_data.json` |
| `get_competitor_prices` | `product_name` (not SKU) | competitor list plus avg/min/max | Mocked. In production: Tavily, Serper or Brave |
| `get_review_sentiment` | `sku` | avg rating, count, **a Haiku-written summary** | Contains a hidden model call |

**Lessons:**

1. **If a tool is broken, the agent confidently produces nonsense.** Test tools before any LLM touches them.
2. **Deterministic work belongs in the tool, not the model.** Given only `inventory: 42` and `reorder_point: 30`, the agent sometimes claimed stock was "already below the reorder point." The fix was to compute `below_reorder_point` and related fields inside the tool. Comparisons, arithmetic and thresholds go in code; the model judges what the numbers *mean*.
3. The mock data for the two SKUs, worth memorizing because every eval result refers to it:
   - **GM-001 Garam Masala:** 42 on hand, reorder point 30, 4.6 per day, about 9.1 days of stock, $8.99 vs a competitor average of $8.16.
   - **BB-002 Berbere:** 12 on hand, reorder point 20. Already below it, so a reorder is clearly needed.

### 7.3 Tool schemas: descriptions are instructions

The model never sees your Python. It sees `name`, `description` and `input_schema`, and it uses the description to decide *when* to call a tool and *how* to fill in the arguments.

Your schemas do real work:

- `get_internal_metrics`: "...**Call this first** to understand the product's current state." This sets the order of tool calls.
- `get_competitor_prices`: "...by its name (**not SKU**)... **Use the product name from get_internal_metrics.**" This makes the chaining explicit.

The same rule shows up again in the guardrail (`maxItems: 4`, "15 words max") and in MCP ("the docstring is the interface").

### 7.4 The agent loop: memorize this

Code: [agent.py](../agent.py)

```python
for turn in range(max_turns):                         # hard cap: 8
    response = client.messages.create(model=..., system=SYSTEM_PROMPT,
                                      tools=TOOL_SCHEMAS, messages=messages)
    if response.stop_reason == "end_turn":
        return guardrail(response.content[0].text)    # done
    if response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:                # may be SEVERAL tool_use blocks
            if block.type == "tool_use":
                result = TOOL_FUNCTIONS[block.name](**block.input)
                tool_results.append({"type": "tool_result",
                                     "tool_use_id": block.id,   # pairs result with call
                                     "content": json.dumps(result)})
        messages.append({"role": "user", "content": tool_results})
return "Agent stopped: max turns reached..."
```

**Protocol rules to know cold:**

- `stop_reason == "tool_use"` means the model wants tools run. `"end_turn"` means it has a final answer.
- Append the assistant turn **with all of its content blocks**, not just the text, or the next call fails. The `tool_use` block has to be in the history for its result to pair with.
- Tool results go back as a **user** message of `tool_result` blocks, each carrying the matching `tool_use_id`.
- One response can contain several `tool_use` blocks (you usually see `get_competitor_prices` and `get_review_sentiment` together in turn 2). Run all of them and return all the results in **one** user message.
- `max_turns` is your safety valve against a loop that never ends.

**Three weak spots, fixed on 2026-09-30 in [agent.py](../agent.py) and [cloud/agent_bedrock.py](../cloud/agent_bedrock.py).** These make good interview talking points, because the walkthrough's loop has all three:

| Weak spot | What went wrong | Fix |
|---|---|---|
| Unhandled `stop_reason` | For `"max_tokens"` or `"refusal"`, neither branch ran, so the loop resent the identical request until `max_turns` ran out | Anything other than `end_turn`/`tool_use` now returns immediately and flags the span `WARNING` |
| `response.content[0].text` | Assumes the first block is text, which breaks if a thinking or reasoning block comes first | `final_text()` joins all text blocks |
| No tool error handling | A tool exception, or a tool name the model invented, crashed the whole run | `run_requested_tool` catches the error and returns `{"error": ...}`. `tool_result_block()` sets `is_error: true` so the model can recover |

### 7.5 System prompt design

`SYSTEM_PROMPT` in `agent.py:65`: a role (merchandising analyst for Spices Inc), a three-part output (pricing, inventory, promo angle), tool-order guidance, "Base every claim on tool data. Do not invent numbers," a 150-word limit, and "plain hyphens, never em dashes."

Note that the raw prompt has **no** forbidden-word list. That is why raw and LangGraph drafts used "premium" in 4 and 3 of their 6 eval runs (see 8.6).

### 7.6 The brand-voice guardrail (evaluator-optimizer as a gate)

Code: [guardrail.py](../guardrail.py)

`guardrail.py`. After the loop ends, a second Sonnet call checks the draft against the brand rules and returns a revised version.

**The main lesson of the week: don't ask the model to do a regex's job.**

| Rule type | Examples | Who checks it |
|-----------|----------|------------|
| Exact string match | forbidden words (elevate, premium, artisanal, gourmet, curated, luxurious, decadent), em dashes and en dashes | `scan_exact_rules()`, with a regex on **stems** (`elevat`, `curat`) so "elevated" and "curating" are caught |
| Judgment | patronizing or hype tone, evocative before concrete, vague heat descriptions | Sonnet |

Why the split: asked to check dashes, Sonnet flagged plain hyphens as em dashes, then argued with itself inside the violations list. It also reported "premium" once per occurrence. The scan is never wrong about string rules, so it owns them, and the model is told not to report them. The scan's findings are **passed into the prompt** so a single revision fixes everything.

**Structured output with a forced tool call:**

```python
tools=[CHECK_TOOL],
tool_choice={"type": "tool", "name": "report_check"},   # the model MUST call this tool
```

The tool's `input_schema` becomes your output schema (`violations: array, maxItems 4`, `revised_text: string`). You used the same technique for the eval judge and in earlier weeks.

**Design details worth copying:**

- **`passes` is derived** (`not violations`), not asserted by the model. Earlier, the model could return `passes: true` next to a non-empty violations list.
- **Schema constraints are instructions.** `maxItems: 4` and "15 words max. No reasoning" in the item description keep the list readable in the console and in Langfuse.
- **Fail open.** If no tool_use block comes back (unreachable with a forced tool_choice, but still), return the original text rather than `None`, because callers index into the result.
- **Test the scan like ordinary code**, with asserts: plain hyphens pass, an em dash is caught, "accurate" is not "curat", "premium" twice is one violation.
- **Test the whole gate on clean text too.** A guardrail that invents violations on good text is worse than none, because people learn to ignore it.

**Evaluator-optimizer purists will note:** this is a single pass (critique and revise in one call), not a loop until the critique passes. The custom LangGraph graph is where a retry loop would be natural: one conditional edge from `guardrail` back to `agent`.

### 7.7 Observability with Langfuse 4.x

Code: [observability.py](../observability.py). Local Langfuse UI: http://localhost:3000

**Concept 1: the important spans are the ones outside your loop.** Only 3 of the 5 model calls happen in `run_agent`. The Haiku call is **inside a tool**, and the guardrail call happens **after** the loop. If you instrument only the loop, the trace looks complete while under-reporting cost by about a third.

**Rule:** every Anthropic call goes through one traced helper, `traced_messages_create` in `observability.py`. No module calls `client.messages.create` directly. (Exception: the eval judge in `evals/agent_eval.py` is still untraced.)

**Concept 2: a span doesn't record cost on its own.** Langfuse computes dollars from `model` plus `usage_details` on a **generation** observation. A plain span shows `$0.00`, which looks exactly like "a cheap call." That is the most common silent failure.

**The trace for one run:**

```
merchandising-agent          AGENT
  orchestrator-turn-1        GENERATION   Sonnet decides which tools to call
  get_internal_metrics       TOOL
  orchestrator-turn-2        GENERATION
  get_competitor_prices      TOOL
  get_review_sentiment       TOOL
    sentiment-summary        GENERATION   Haiku, nested inside the tool
  orchestrator-turn-3        GENERATION   writes the recommendation
  brand-guardrail            GUARDRAIL
    guardrail-check          GENERATION   Sonnet checks brand voice
```

**Five model calls to answer one question.** This is the "agents are expensive" point, and you have measured it (see Week 10: about $0.03 per run).

**v2 → v4 API (most tutorials are out of date):**

| v2 (gone since v3) | v4 (what you use) |
|---|---|
| `from langfuse.decorators import observe` | `from langfuse import observe` |
| `langfuse_context.update_current_observation()` | `get_client().update_current_span()` / `.update_current_generation()` |
| n/a | `@observe(as_type="agent" \| "tool" \| "guardrail")` |
| n/a | `langfuse.start_as_current_observation(name=..., as_type="generation")` context manager |

**Decisions in your code, and why:**

1. **`run_requested_tool` uses a context manager, not `@observe`**, because the span has to be named after the tool the model asked for (`block.name`). A decorator would name all three spans `run_requested_tool`.
2. **The tool functions in `tools.py` are not decorated.** One dispatcher covers all three, and `tools.py` stays free of the observability stack.
3. **You set cost yourself** (`PRICES_PER_MTOK`: Sonnet 4.6 at $3/$15, Haiku 4.5 at $1/$5 per million tokens). Langfuse's own model catalog lags new model IDs and shows a blank cost when it misses.
4. **Prices match on prefix** because `response.model` is the resolved snapshot (for example `claude-sonnet-4-6-20250929`), not the alias you sent.
5. **Prompt cache pricing:** reads cost **0.1x** the input price, writes **1.25x**. Anthropic's `input_tokens` already *excludes* cached tokens, so the cache counts are extra keys, not a subset.
6. **Metadata on the agent span** (`sku`, `orchestrator_model`, `turns_used`, `guardrail_passed`), because Langfuse filters traces on metadata, not on the input blob. Hitting max turns sets `level="WARNING"`.
7. **`langfuse.flush()` in `__main__`**, because spans are exported on a background thread and a short script can exit before they are sent.
8. **`get_trace_url()` only works inside the active span.** Call it from `__main__` after the agent span closes and you get `None`.

**Troubleshooting checklist:**

- No trace at all: missing `flush()`, or bad `LANGFUSE_*` keys. Failures happen silently per span, so check with `get_client().auth_check()`.
- Spans present but $0.00: you are not on the generation path, or `usage_details`/`model` isn't reaching the span.
- Scripted queries return 404: the server is in v4 `events_only` mode. Use `GET /api/public/v2/observations` (and remember it returns a slim projection without usage, so trust the UI).

### 7.8 Evaluating the agent

Code: [evals/agent_eval.py](../evals/agent_eval.py)

**Agents are harder to evaluate than RAG.** RAG has question/answer pairs. An agent has a goal and a process.

- **Outcome eval:** was the final recommendation good? (LLM as judge.) This is what you built.
- **Process/trajectory eval:** did it call the right tools in a sensible order? Your trace makes this possible, but you only did it lightly.

**`evals/agent_eval.py`:**

- `REFERENCE` per SKU: `must_address` and `should_not` lists.
- Judge: Sonnet with a forced `score` tool. It returns `reasoning`, `addresses_required` (0-5), `grounded_in_data` (1-5) and `avoided_errors` (bool). `reasoning` comes **first** so the model reasons before scoring.
- **Bug you found:** at `max_tokens=512`, the long `reasoning` field used up the budget and the scores after it were **silently dropped** from the truncated tool input. The fix: raise it to 1500 and `raise` if `stop_reason == "max_tokens"`. The general lesson is that with a forced tool call, truncation produces valid-looking but partial output.
- Run it **from the project root**, because `tools.py` resolves `mock_data.json` against the current directory.
- `sys.path.insert(0, ROOT)` works around the missing `[build-system]`, since uv doesn't install the project into the venv.

**What the results told you (8.6):** every arm failed GM-001 in all 12 runs, and **the reference was wrong, not the agents**. 42 units at 4.6 per day is 9.1 days of stock, so recommending a reorder is defensible. The expectation had been written from "42 > 30" alone. When four frameworks agree 12 out of 12 times, suspect the eval.

**But in Week 10:** the *conclusion* held while the *reasoning* sometimes didn't. Some runs justified the reorder by claiming 42 was "already below" 30. That led to the tool-side `below_reorder_point` fields and a new `should_not` entry. **Grade the reasoning, not just the verdict.**

When a score is low, open the trace and decide whether it is a **tool problem** (bad data) or a **reasoning problem** (good data, weak recommendation).

---

## Week 8: LangGraph and CrewAI

### 8.1 LangGraph concepts

- **State:** a typed dict carried through the graph (`AgentState: sku, draft, final, guardrail_violations`).
- **Nodes:** functions from state to state updates.
- **Edges:** fixed (always fire) or conditional (branch on state). `START` and `END` are special nodes.
- **Compile:** `graph.compile()` produces a runnable `app`. Checkpointing and interrupts are compile-time options.
- **Why LangGraph for agents:** state, branching and retries are *explicit and visible*, instead of buried inside a `for` loop.

### 8.2 Prebuilt agent (`langgraph_version/agent_prebuilt.py`)

Code: [langgraph_version/agent_prebuilt.py](../langgraph_version/agent_prebuilt.py)

```python
@tool
def get_internal_metrics(sku: str) -> dict:
    """<docstring = tool description>"""
    return t.get_internal_metrics(sku)

model = init_chat_model("claude-sonnet-4-6", temperature=0)
agent = create_agent(model, tools=[...], system_prompt=SYSTEM)
agent.invoke({"messages": [("user", "...SKU GM-001")]})["messages"][-1].content
```

- **Framework churn (a trade-off worth naming):** in LangGraph 0.x this was `create_react_agent` from `langgraph.prebuilt` with a `prompt=` argument. In 1.0 it became `create_agent` from **`langchain.agents`** with **`system_prompt=`**. The old import raises `LangGraphDeprecatedSinceV10`. Your raw-SDK loop needed no migration.
- There is **no guardrail**. It is the only arm whose output goes out unreviewed.
- About 31 lines of code.

### 8.3 Custom graph (`langgraph_version/agent_graph.py`)

Code: [langgraph_version/agent_graph.py](../langgraph_version/agent_graph.py)

```python
graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)          # runs the prebuilt ReAct loop, writes draft
graph.add_node("guardrail", guardrail_node)  # apply_brand_guardrail(draft) -> final, violations
graph.add_edge(START, "agent")
graph.add_edge("agent", "guardrail")
graph.add_edge("guardrail", END)
app = graph.compile()
```

- The guardrail is now **part of the structure**. It appears in `app.get_graph().draw_mermaid()`, which you pasted into the README unedited so the diagram can't drift from the code.
- Obvious next steps are each one edge or one compile option: a retry (a conditional edge from `guardrail` back to `agent`), a human-approval interrupt before a price change, checkpointing.
- Idiom note: your nodes mutate `state` and return all of it. Idiomatic LangGraph returns a **partial dict of updates** (`return {"draft": ...}`), which matters once you add reducers or parallel branches.

**Gotchas you hit:**

- **`mock_data.json` depends on the working directory.** Running from `langgraph_version/` seeded a *second* `mock_data.json` there. New SKUs added at the root won't show up in the LangGraph versions.
- **`sys.path.insert(0, "..")`** means different things depending on where you run from. From the project root it puts `~/projects` first. The eval pre-imports `tools`, `guardrail` and `observability` so later imports resolve from `sys.modules`.
- LangGraph and CrewAI never import `observability`, so they don't load `.env` themselves. The eval imports it for them.

### 8.4 CrewAI (`crewai_demo.py`)

Code: [crewai_demo.py](../crewai_demo.py)

**Mental model:** roles and collaboration, compared with LangGraph's nodes and state and the raw SDK's loop. The underlying mechanics are the same; the abstractions differ.

```python
llm = LLM(model="anthropic/claude-sonnet-4-6")
analyst    = Agent(role=..., goal=..., backstory=..., tools=[3 tools], llm=llm)
copywriter = Agent(role=..., backstory=f"...{BRAND_RULES}", llm=llm)      # no tools
analyze_task = Task(description="Analyze SKU {sku}...", expected_output=..., agent=analyst)
write_task   = Task(..., agent=copywriter, context=[analyze_task],
                    guardrail=brand_voice_guardrail)
crew = Crew(agents=[...], tasks=[...], process=Process.sequential)
crew.kickoff(inputs={"sku": sku}).raw
```

- `{sku}` in task descriptions is filled in from `kickoff(inputs=...)`.
- `context=[analyze_task]` is how the copywriter receives the analyst's brief.
- **Task guardrails (CrewAI 1.x)** take a `TaskOutput` and return `(passed, result)`. `(True, revised_text)` replaces the output (what you do). `(False, feedback)` sends the agent back to retry with that feedback.

**Gotchas you hit:**

- **Without `llm=`, CrewAI silently uses OpenAI** (`gpt-4.1-mini`) with whatever `OPENAI_API_KEY` is set. The `anthropic/` prefix routes to its native Anthropic provider.
- **Don't pass `temperature`.** Anthropic SDK 1.x removed sampling parameters from `messages.create`, and CrewAI forwards them unchanged.

### 8.5 How the comparison was run

`evals/agent_eval.py --impl ... --trials N` loads each implementation lazily, runs every reference SKU N times, judges each run, times it, and counts lines of code with `code_lines()` (an AST and tokenizer pass that skips blank lines, comments and docstrings, so chatty files aren't penalized).

### 8.6 Results (2026-09-18: 2 SKUs × 3 trials × 4 arms = 24 runs, 0 failures)

Source: [IMPLEMENTATIONS.md](../IMPLEMENTATIONS.md)

| Metric | Raw SDK | LG prebuilt | LG custom | CrewAI |
|---|---|---|---|---|
| Addresses required (0-5) | 3.8 | 3.8 | 4.0 | 3.8 |
| Grounded in data (1-5) | 4.2 | 4.0 | 4.0 | 4.3 |
| Avoided errors | 3/6 | 3/6 | 3/6 | 3/6 |
| Mean latency | 24.7s | 17.5s | 16.3s | 32.2s |
| Guardrail violations per run | 2.3 | - | 2.0 | 0.7 |
| Lines of code | 108 | 31 | 44 (+31) | 70 |

**The three findings (be ready to tell these as stories):**

1. **Outcomes were indistinguishable.** The results split by SKU, not by framework: every arm passed BB-002 and failed GM-001, and the GM-001 failure was the reference's fault (see 7.8).
2. **CrewAI needed the guardrail least because of its prompt, not its framework.** `BRAND_RULES` was in the copywriter's backstory, while the other arms only saw the brand rules at the guardrail. Its role structure pushed brand voice into the writer's prompt, and any arm could copy that.
3. **"Guardrails are awkward in CrewAI" is out of date.** `Task(guardrail=...)` is a first-class feature. It's only awkward when the check belongs somewhere other than a task's output (for example, between two tool calls).

**Latency tracks the number of calls more than the framework.** CrewAI adds a second agent hop. Raw ranged from 16 to 34 seconds, so six samples can't rank the arms.

**What the numbers don't settle:** 2 SKUs is a smoke test. The prompts differ across arms, so any score gap wouldn't be attributable to the framework alone. Cost isn't compared, because the LangGraph and CrewAI orchestrator calls go through their own providers and Langfuse sees only the sentiment and guardrail calls. The next step is a Langfuse callback handler.

### 8.7 When to use which (your answer)

| | Raw SDK | LangGraph | CrewAI |
|---|---|---|---|
| Control over flow | total | low (prebuilt) / high (custom) | medium |
| Built-in tool loop | no | yes | yes |
| Where the guardrail goes | a call inside the loop | an explicit node | a `Task(guardrail=)` hook |
| Multi-agent support | no | possible (subgraphs, supervisor) | core feature |
| Tracing in this repo | full, with cost | sentiment and guardrail only | sentiment and guardrail only |
| Debuggability | high | medium | lower |
| Best for | understanding, perf/cost-critical paths | production single agents whose flow will grow | work that really is a team of roles |

> "All four produce indistinguishable recommendations. The raw SDK taught me what's happening and is the only version where every call has a cost on it. LangGraph is what I'd ship, because state and branching are explicit and retries or human approval are one edge away. CrewAI fits genuine role-based collaboration, but for one analyst with three tools it's overhead. The choice is about the shape of the workflow and who maintains it, not answer quality."

---

## Week 9: The Drupal MCP server

Code: [~/projects/drupal-mcp-server](../../drupal-mcp-server) ([GitHub](https://github.com/rsnyd/drupal-mcp-server), tag `v0.1.0`)

### 9.1 MCP vs function calling (the most common interview question on this)

| | Function calling | MCP |
|---|---|---|
| Where tools are defined | JSON schema sent **in every API call** | A **server** you run once |
| Scope | Per application, vendor-specific | Vendor-neutral. Any compliant host (Claude Desktop, Claude Code, Cursor, ChatGPT, VS Code Copilot) discovers and calls the tools |
| Integration effort | Custom code for each app | Write once, use everywhere |
| Relationship | - | MCP doesn't replace tool use. The host still turns MCP tools into tool definitions for the model. MCP standardizes **discovery and transport** |

Origin: Anthropic open-sourced MCP in late 2024. OpenAI and others adopted it, and there are 2,000+ public servers.

### 9.2 The three primitives

| Primitive | Analogy | Who controls it | In your server |
|---|---|---|---|
| **Tools** | POST endpoints: they do work | The **model** decides when to call them | `explain_hook`, `list_services`, `scaffold_content_entity` |
| **Resources** | GET endpoints: read-only context, addressed by URI | The **application/user** loads them | `drupal://hooks/common` |
| **Prompts** | Reusable templates | The **user** invokes them | none |

### 9.3 The SDK: `MCPServer` (formerly `FastMCP`)

```python
from mcp.server.mcpserver import MCPServer      # mcp 2.x
mcp = MCPServer("drupal-dev")

@mcp.tool()
def explain_hook(hook_name: str) -> str:
    """Explain a Drupal hook: its purpose, signature, parameters, and common use cases.

    Args:
        hook_name: The hook name, e.g. 'hook_entity_presave' or 'hook_form_alter'.
    """

@mcp.resource("drupal://hooks/common")
def common_hooks() -> str: ...

if __name__ == "__main__":
    mcp.run()     # stdio transport by default
```

- **Type hints become the JSON Schema; the docstring becomes the description.** The SDK also validates inputs and handles the protocol.
- **Renamed:** mcp 1.x was `from mcp.server.fastmcp import FastMCP`. mcp 2.x is `MCPServer` in `mcp.server.mcpserver`. The decorators and `run()` are unchanged, and the old path raises an error that tells you what happened. Your `pyproject.toml` pins `mcp[cli]>=2.2.0`.
- The [README](https://github.com/rsnyd/drupal-mcp-server#readme) now uses the `MCPServer` name and includes a version note for readers coming from FastMCP tutorials. Code: [server.py](https://github.com/rsnyd/drupal-mcp-server/blob/main/server.py).

### 9.4 The tools and why each one earns its place

"Aim for tools that do something the model can't do from memory."

- **`explain_hook`:** a static dictionary of two hooks. What makes it valuable is the *gotcha* line: use `hook_ENTITY_TYPE_presave` rather than `hook_entity_presave` for a single type, and `hook_form_FORM_ID_alter` rather than `hook_form_alter`. That's convention knowledge models tend to gloss over.
- **`list_services`:** parses `*.services.yml` with `yaml.safe_load` into a flat list of IDs, classes and arguments. It gives the model *your* service definitions instead of plausible guesses.
- **`scaffold_content_entity`:** generates a `ContentEntityBase` class with the `@ContentEntityType` annotation (id, label, base_table, entity_keys, handlers) and field stubs. Long, fiddly, nearly memorable boilerplate is exactly where generators help.
- **Resource `drupal://hooks/common`:** shows the model the shape of the hook system so it knows which questions to ask.

### 9.5 Testing and hosting

- **MCP Inspector first:** `npx @modelcontextprotocol/inspector uv run server.py`. It gives you a browser UI to list and call tools and see the raw protocol traffic. It separates "my tool is broken" from "my client config is broken."
- **Claude Desktop config** (`%APPDATA%\Claude\claude_desktop_config.json` on Windows):
  ```json
  {"mcpServers": {"drupal-dev": {"command": "uv",
    "args": ["--directory", "/abs/path/drupal-mcp-server", "run", "server.py"]}}}
  ```
  Use an absolute path and restart the app.
- **WSL2 caveat:** Windows Claude Desktop launching a WSL server has path translation problems. Either use HTTP transport and point the host at a URL, or run Claude Code inside WSL.
- **Transports:** stdio (the host launches the server as a subprocess, which is local and simple) vs HTTP (a remote server that can be shared across hosts).

### 9.6 What building it taught you (from your blog draft)

Source: [BLOG_POST_DRAFT.md](https://github.com/rsnyd/drupal-mcp-server/blob/main/BLOG_POST_DRAFT.md)

1. **The docstring is the interface.** "Explains hooks" got ignored. "Explain a Drupal hook: its purpose, signature, parameters, and common use cases" got called. An `e.g.` in `Args` teaches the argument's shape.
2. **Return text, not data structures.** The consumer is a model, and a labeled prose block produced better answers than a dict.
3. **Keep the scope small and ship.** Two hooks are enough to prove the interface. Stubs are cheap to fill in; interfaces are expensive to change.
4. **The payoff moment:** the assistant called `explain_hook` *unprompted* from a plain-English question and included the `hook_ENTITY_TYPE_presave` caveat. There was no prompt engineering involved.

**Next step you identified:** back `explain_hook` with the Weeks 3-4 Drupal RAG index. The MCP server is the delivery mechanism the RAG system was missing.

**Open items on the MCP deliverable:** screenshots aren't in the repo yet, and the server hasn't been submitted to an MCP directory. The blog post is due in Week 12. The README's Claude Code and Claude Desktop setup sections were filled in on 2026-09-30.

---

## Weeks 7-9 interview drill

Answer out loud first, then check.

<details><summary><b>1. What is an agent, in one sentence?</b></summary>
An LLM in a loop with tools and a goal. The model chooses actions, your code runs them and feeds the results back, and the loop continues until the model says it's done or you hit a turn cap.
</details>

<details><summary><b>2. Name the seven patterns. Which one is your agent, and why not a simpler one?</b></summary>
Augmented LLM, prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer, autonomous agent. Mine is orchestrator-workers with an evaluator-optimizer guardrail. The model decides the tool sequence and chains outputs (name from metrics → competitor search). A fixed chain would work for exactly these three tools, and I'd say so. The loop earns its place once tools become conditional (for example, skip competitor search when there's no data).
</details>

<details><summary><b>3. Walk through one run: how many model calls, and where are they?</b></summary>
Five: three Sonnet orchestrator turns (turn 1 metrics, turn 2 competitor plus sentiment in parallel, turn 3 writes the recommendation), one Haiku call hidden inside get_review_sentiment, and one Sonnet guardrail call after the loop. About $0.03 per run.
</details>

<details><summary><b>4. Why doesn't the model compare inventory with the reorder point?</b></summary>
It got it wrong: it claimed 42 was "already below" 30. Deterministic comparisons and arithmetic go in the tool (below_reorder_point, units_above_reorder_point, days_until_reorder_point). The model interprets; code calculates.
</details>

<details><summary><b>5. Why is your guardrail split between a regex and an LLM?</b></summary>
Exact-match rules (forbidden words, em dashes) are string scans that code never gets wrong. Sonnet mistook hyphens for em dashes and duplicated violations. Judgment rules (tone, concrete-before-evocative) need the model. The scan's findings go into the prompt so one revision fixes everything. The general principle: use the LLM only for the parts that need judgment.
</details>

<details><summary><b>6. How do you get reliable structured output from Claude?</b></summary>
A forced tool call: define a tool whose input_schema is the output shape and set tool_choice={"type":"tool","name":...}. Use schema constraints (maxItems, min/max, descriptions) as instructions. Derive booleans such as passes in code rather than trusting the model's version. Watch max_tokens: truncation silently drops the fields that come later (the judge bug).
</details>

<details><summary><b>7. Your Langfuse trace showed $0.00 for a call. What went wrong?</b></summary>
It was recorded as a plain span instead of a generation, or model/usage_details weren't passed, or the model ID didn't match a price. Langfuse computes cost from model plus usage on generation observations. I set cost_details myself with prefix matching because the catalog lags new models.
</details>

<details><summary><b>8. How do you evaluate an agent differently from RAG?</b></summary>
Outcome (LLM judge against per-case must_address / should_not) plus process (trajectory: the right tools in a sensible order, which the trace makes checkable). Run multiple trials, because variance is high. Grade reasoning as well as the conclusion. My GM-001 runs reached a defensible reorder call with a false justification.
</details>

<details><summary><b>9. All four implementations failed GM-001. What did you conclude?</b></summary>
The reference was wrong. 42 units at 4.6/day is 9.1 days of stock, so a reorder is reasonable. When independent systems agree 12 out of 12 times against the eval, check the eval. Later I tightened the eval to catch the false "already below" claim instead.
</details>

<details><summary><b>10. Raw SDK vs LangGraph vs CrewAI: which would you ship?</b></summary>
LangGraph custom graph for a single production agent: typed state, a visible guardrail node, and retry, human-in-the-loop and checkpointing each one edge or compile option away. Raw SDK when I need per-call control of cost and latency, or full tracing. CrewAI when the work really is a team of roles. Outcomes were identical, so the decision is about workflow shape and maintainability.
</details>

<details><summary><b>11. What does a framework cost you?</b></summary>
Churn (create_react_agent → create_agent, prompt → system_prompt), hidden prompts, less visibility (my Langfuse lost the orchestrator calls on the framework arms), and surprising defaults (CrewAI quietly uses OpenAI without llm=; it forwards temperature, which the Anthropic SDK rejects).
</details>

<details><summary><b>12. MCP vs function calling?</b></summary>
Function calling puts tool schemas in each API request and is per app. MCP is a protocol: stand up a server once and any compliant host discovers and calls its tools. MCP standardizes discovery and transport. The host still turns MCP tools into function-calling definitions for the model.
</details>

<details><summary><b>13. What are the three MCP primitives, and who controls each?</b></summary>
Tools (the model calls them to do things), Resources (read-only URI-addressed context loaded by the app/user), Prompts (templates the user invokes).
</details>

<details><summary><b>14. What makes a good MCP tool?</b></summary>
It does something the model can't do from memory (local conventions, your real data, exact boilerplate). It has a precise docstring with an example argument, because the docstring is the only thing the model sees. It returns readable text. Its scope is narrow.
</details>

<details><summary><b>15. How would you make your agent production-ready?</b></summary>
Handle stop reasons other than end_turn/tool_use. Catch tool errors and return is_error tool results. Add a retry edge on guardrail failure and a human approval step before price changes. Replace mocks with real APIs (Drupal Commerce, Yotpo, Tavily). Route every call (including the judge and the framework arms) through tracing. Build a larger eval set with trajectory checks. Run on Bedrock with least-privilege IAM (Week 10).
</details>

<details><summary><b>16. Why does the guardrail "fail open"? When would you fail closed?</b></summary>
Brand voice is a quality gate, so returning the original text is better than crashing. For safety or compliance gates (PII, regulated claims) you would fail closed: block the output or send it to a human.
</details>

---

## Rebuild-from-memory drills

Do each one on a blank page (or an empty file), then diff against the real file.

1. **The agent loop** (`agent.py`): messages list, `stop_reason` branches, appending the assistant content, collecting `tool_result` with `tool_use_id`, the `max_turns` fallback. *Target: under 10 minutes.*
2. **One tool schema**: `get_competitor_prices` with a description that enforces "name, not SKU."
3. **`scan_exact_rules`**: the stem regex `\b{stem}\w*` with `re.IGNORECASE`, deduplicated, plus the dash check. Then write the four asserts.
4. **The forced-tool guardrail call**: `CHECK_TOOL` schema plus `tool_choice`, and derive `passes`.
5. **`traced_messages_create`**: `start_as_current_observation(as_type="generation")`, then `generation.update(model=response.model, usage_details=..., cost_details=...)`.
6. **The custom `StateGraph`**: TypedDict, two nodes, three edges, compile. Then add a conditional retry edge from the guardrail back to the agent (new code, good practice).
7. **A new MCP tool**: e.g. `explain_hook` for `hook_ENTITY_TYPE_access`, or a new `explain_plugin_type`. Test it in the Inspector.

---

# Week 10: Bedrock

Code: [cloud/](../cloud/). Start with [CLOUD_DEPLOYMENT.md](../cloud/CLOUD_DEPLOYMENT.md), [iam-policy.json](../cloud/iam-policy.json), [agent_bedrock.py](../cloud/agent_bedrock.py) and [measure_runs.py](../cloud/measure_runs.py). Working notes are in [NOTES.md](../cloud/NOTES.md).

**Goal:** run the agent's inference through AWS Bedrock (us-east-1), lock it down with least-privilege IAM, measure it, and write it up as an SA would for a customer (`cloud/CLOUD_DEPLOYMENT.md`).

## Core ideas

- **Bedrock runs the same model as the direct API; only the surrounding pieces change.** Auth (IAM instead of API keys), region, billing (the AWS bill) and the request envelope differ. On GM-001, Bedrock produced the same recommendation *and the same reasoning error* as the direct API.
- **Why enterprises want it:**
  - procurement through the existing AWS bill
  - data residency
  - IAM instead of long-lived keys
  - CloudTrail audit
  - cost allocation through tagged application inference profiles
- **Two clients:**

  | | Converse (boto3) | AnthropicBedrock (`anthropic[bedrock]`) |
  |---|---|---|
  | Models | Any (Nova, Claude, ...) | Claude only |
  | Shape | AWS envelope (`inferenceConfig`, `[{"text":...}]`) | Native Messages API |
  | Latency field | `metrics.latencyMs` | none (use Langfuse timings) |
  | Access-denied error | `ClientError` / `AccessDeniedException` | HTTP 403 `PermissionDeniedError` |
  | Choose when | You may switch model families | You want the smallest port of a Claude agent (what you did) |

- **Inference profiles:** current Claude models *require* a profile ID such as `us.anthropic.claude-sonnet-4-6`. A bare ID fails with "on-demand throughput isn't supported."
  - `us.` keeps requests in us-east-1, us-east-2 and us-west-2. This is the compliance choice, at about a 10% premium.
  - `global.` can route anywhere, with more capacity and a lower price.
- **The three gates to model access:**
  1. Anthropic's use-case form, once per account.
  2. Per-account, per-model approval from AWS.
  3. IAM `bedrock:InvokeModel`.

  Your account can use Sonnet 4.6, Sonnet 4.5, Haiku 4.5 and Nova Lite. It is **denied** Sonnet 5 and Opus 5, and AWS Support says access depends on "regional factors, payment history, and account usage." The only reliable check is **one cheap real invoke**: list-foundation-models and the availability API both misled you.
- **Least-privilege IAM** (`cloud/iam-policy.json`):
  - It allows `InvokeModel` and `InvokeModelWithResponseStream`. There is no separate Converse action.
  - It covers the **profile ARN plus the foundation-model ARN in each region the profile routes to**. If you allow only us-east-1, calls fail intermittently.
  - For production, use a workload IAM role instead of an IAM user.
- **Guardrails come in layers:**
  - **Bedrock Guardrails** (content filters, denied topics, PII redaction) is the platform layer, owned by the security team, and applies even if the app code is wrong.
  - **`guardrail.py`** (brand voice) is the application layer.
  - Neither replaces the other. This was a design deliverable only; the platform layer isn't implemented.
- **Throughput:** 1,000 runs a day is under one per minute, so **on-demand**. Provisioned throughput is for steady, high volume or guaranteed capacity.

## Your measurements (10 runs, GM-001, 2026-09-29, `cloud/cost_analysis.md`)

Source: [cloud/cost_analysis.md](../cloud/cost_analysis.md)

| Per run | Value |
|---|---|
| Model calls | 5 (3 Sonnet orchestrator calls, 1 Haiku sentiment call, 1 Sonnet guardrail call) |
| Tokens | 6,138 (5,326 in / 812 out) |
| Cost | ≈ $0.029 as routed ($0.030 all on `us.`, $0.027 all on `global.`) |
| Latency | average 17.0s, p50 16.6s, p95 25.1s |
| Monthly at 1,000 runs/day | ≈ $877 as routed / $904 all `us.` / $822 all `global.` |

- **The guardrail is the most expensive single call:** $0.0097 and 4.7s, about a third of the cost.
- **Input is 87% of tokens**, because each orchestrator turn resends the system prompt, tools and history. So **prompt caching is the first optimization** (reads cost 0.1x). The second is evaluating Haiku for the guardrail, gated on evals.
- Tool execution takes about 1ms, so latency is all model time.
- The WSL2 clock drifts (about 6% slow), so p50 is only good to about ±1s. Re-measure from EC2 before quoting an SLA.

## The caveat to state before anyone asks

**The agent isn't fully on Bedrock yet.** `guardrail.py` and `tools.get_review_sentiment` create their own `Anthropic()` clients, so 2 of the 5 calls still go to the direct API. The cost difference is small; for a customer who needs all traffic inside AWS, it's a blocker. To finish the port, inject the client, and add Haiku 4.5 to the IAM policy.

## Gotchas

- Error handling doesn't carry over between the two clients.
- The first port wasn't traced (only orphan guardrail and sentiment traces appeared).
- Langfuse v4's v1 trace endpoint returns 404. Use `observations.get_many(fields="core,basic,time,model,usage")`.
- Sonnet 5 and newer reject `temperature`.
- Don't assume `content[0]` is text: a reasoning block can come first.
- The `sys.path` issue from the `cloud/` directory has the same cause as the one in `evals/`: there's no `[build-system]`.

<details><summary><b>Self-test: Week 10</b></summary>

1. *Is Claude on Bedrock a different model?* No. Auth, region, billing and the request envelope differ; the output (including errors) was the same.
2. *Converse or AnthropicBedrock?* Converse if you might switch model families; AnthropicBedrock for the smallest Claude port.
3. *Why does `anthropic.claude-sonnet-4-6` fail?* A profile ID (`us.` or `global.`) is required.
4. *(SA) A healthcare customer asks about us. vs global.* Recommend `us.` for residency and budget the roughly 10% premium.
5. *Why does a policy allowing only the us-east-1 model ARN fail intermittently?* The profile routes to 3 regions, so allow all of them plus the profile ARN.
6. *How do you verify model access?* One real invoke. The list and availability APIs don't reflect approval.
7. *(SA) Cost and latency at 1,000 runs/day?* About $900/month, p50 about 17s, 5 calls per run.
8. *First optimization?* Prompt caching, since input is 87% of tokens. Then consider Haiku for the guardrail.
9. *Is it fully on Bedrock?* No, 2 of 5 calls go to the direct API. State that proactively.
10. *Bedrock Guardrails vs your guardrail?* Platform safety vs application brand voice. They're layers, not substitutes.
11. *Provisioned throughput?* No. Under one run per minute means on-demand.
</details>

**Coming next (Week 11):** the AWS AIF-C01 certification sprint and portfolio polish.

---

## Cross-cutting lessons

These lessons came up in more than one week. They make good interview answers because each one is backed by something you measured.

1. **Use code where it can be exact, and the model where judgment is needed.** Examples: the regex brand scan (W7), `below_reorder_point` in the tool (W7/W10), clause metrics beside the judge (W3), and the fabrication regex (W6).
2. **Forced tool use is how you get structured output.** You used it in the extractor (W1), the RAG judge (W3), the voice judge (W6), the guardrail (W7) and the agent judge (W7). Watch `max_tokens`: truncation silently drops the later fields.
3. **Schema descriptions and docstrings are instructions, not documentation.** See tool descriptions (W7), `maxItems` / "15 words max" (W7), and MCP docstrings (W9).
4. **Frameworks change developer experience, not answer quality.** RAG: raw ≈ LCEL ≈ LangGraph (W5). Agents: all four arms were indistinguishable (W8). Both times you kept the raw version wherever visibility mattered.
5. **Question the eval before the system.** Examples: the GM-001 reference (W8), the refusal-regex undercount (W3), the 0% hit@3 artifact (W3), and the held-out leak (W6).
6. **Know your noise floor.** Judge drift was about 0.06 (W3), agent latency ranged 16-34s (W8), and the WSL2 clock is off by about ±1s (W10). Don't rank things that fall within noise.
7. **A silent failure looks like success.** Examples: `<w:ins>` text dropped (W2), $0.00 spans (W7), broken Langfuse keys (W4/W7), a missing `flush()` (W7), CrewAI quietly using OpenAI (W8), and a stale second `mock_data.json` (W8).
8. **Agents are expensive, and you can quantify it.** Five calls per run instead of one or two for RAG, about $0.03 and about 17s per run. The biggest costs are in calls outside the loop (the guardrail, the sentiment tool).
9. **Trace every model call, including the ones you forget.** The hidden Haiku call in a tool and the guardrail after the loop. One traced helper, and no direct `messages.create` calls.
10. **Framework and API churn is a real cost.** Langfuse v2 → v4, `create_react_agent` → `create_agent`, FastMCP → MCPServer, and temperature removed on newer models.
11. **Pick the simplest thing that works, and say why.** Vanilla retrieval stayed (W4), raw RAG stayed (W5), and the agent uses a single orchestrator rather than a multi-agent design (W7-8).

---

## Glossary

**API and LLM basics**
- **Messages API:** Stateless chat endpoint. The client resends the full history on every call.
- **Token:** Unit of pricing and context, roughly 4 characters of English.
- **stop_reason:** Why the model stopped. `end_turn` means it finished, `tool_use` means it wants a tool run, `max_tokens` means it hit the output limit.
- **tool_use / tool_result:** A request from the model to call a tool, and your reply, paired by `tool_use_id`.
- **tool_choice (forced):** Makes the model call a specific tool. This is how you get structured output.
- **Prompt caching:** Reuses a stable prompt prefix. Cached reads bill at 0.1x the input rate, writes at 1.25x, and the cache lasts about 5 minutes.

**RAG and retrieval**
- **RAG:** Retrieval-augmented generation: retrieve relevant text, add it to the prompt, then generate.
- **Embedding / vector DB:** An embedding is a vector representing meaning; a vector database runs K-nearest-neighbor search over them (Chroma here).
- **Clause-aware chunking:** Splitting documents on SQF clause boundaries so each chunk carries clause and page metadata.
- **BM25:** Keyword ranking: TF-IDF with term saturation and length normalization.
- **RRF:** Reciprocal Rank Fusion. Each document scores the sum of 1/(rank+60) across result lists.
- **Cross-encoder reranker:** Scores (query, document) pairs to reorder candidates.

**Evaluation**
- **Golden set / probe:** Hand-written eval questions with reference answers; a probe is one the corpus can't answer, so it should be refused.
- **LLM-as-judge:** A strong model scoring answers against a rubric and a reference answer.
- **Noise floor:** Score drift between identical runs. Differences smaller than this aren't meaningful.
- **Outcome vs trajectory eval:** Scoring the final answer vs checking the path taken (which tools, in what order).

**Frameworks**
- **LCEL / Runnable:** LangChain's pipe syntax and its shared invoke/stream/batch interface.
- **LangGraph StateGraph:** A graph of typed state, nodes, fixed and conditional edges, and `compile()`.
- **create_agent:** LangChain 1.0's prebuilt ReAct agent (formerly `create_react_agent`).
- **ReAct:** A reason-act loop in which the model alternates thinking and tool calls.
- **CrewAI Agent / Task / Crew:** A role (with goal and backstory), a unit of work (with `expected_output`, `context` and `guardrail`), and the team that runs them (`Process.sequential`).

**Fine-tuning**
- **LoRA / QLoRA:** Low-rank adapters on a frozen base model; QLoRA does the same over a 4-bit quantized base.
- **Catastrophic forgetting:** Loss of general skills after full fine-tuning.

**Agents and guardrails**
- **Augmented LLM, prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer, autonomous agent:** Anthropic's seven agent patterns.
- **Guardrail:** A check on output before it's returned. Fail open (return the output anyway) for quality gates; fail closed (block it) for safety gates.

**Observability**
- **Generation (Langfuse):** An observation type that carries model and usage, which is what lets cost be calculated.
- **as_type:** Langfuse observation type: agent, tool, guardrail, generation or span.
- **flush():** Sends buffered spans before the process exits.

**MCP**
- **MCP:** Model Context Protocol, an open standard that lets any compliant host discover and call a server's tools.
- **Tools / Resources / Prompts:** MCP primitives. Tools are called by the model, resources are read-only context addressed by URI, prompts are templates the user invokes.
- **MCPServer (FastMCP):** The Python SDK class that turns typed, documented functions into MCP tools.
- **MCP Inspector:** Browser tool for calling a server's tools and viewing the protocol traffic.
- **stdio vs HTTP transport:** A local subprocess vs a remote, shareable server.

**Bedrock and AWS**
- **Converse API:** Bedrock's chat API that works across model families.
- **AnthropicBedrock:** Anthropic SDK client for Bedrock that keeps the Messages API shape.
- **Inference profile (`us.` / `global.`):** Routing ID that sends requests across regions (US-only vs worldwide).
- **Least privilege:** Granting only the actions and resources a workload needs.
- **Bedrock Guardrails:** Platform-level content filters, PII redaction and denied topics.
- **On-demand vs provisioned throughput:** Pay per token vs reserved capacity.
- **p50 / p95:** Median and 95th-percentile latency.
