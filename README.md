# JisangFolio

> **A résumé you talk to.** Instead of emailing yet another PDF, I built an interactive AI portfolio you can ask anything about my experience — plus a live data-analysis demo and an MCP server. English by default, with a Korean toggle.

🔗 **Live:** [jisangfolio.streamlit.app](https://jisangfolio.streamlit.app)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/LLM-Groq_Qwen3-F55036?logo=groq&logoColor=white)](https://groq.com/)
[![MCP](https://img.shields.io/badge/MCP-Server-blueviolet?logo=anthropic&logoColor=white)](https://modelcontextprotocol.io/)
[![CI](https://github.com/jisangfolio/jisangfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/jisangfolio/jisangfolio/actions/workflows/ci.yml)

## Overview

JisangFolio is an interactive AI portfolio for **Jisang Park** — an AI · MLOps engineer. Four independent pipelines run behind one Streamlit surface:

- **Chat** — the résumé is injected directly into the system prompt (no document RAG needed for ~3K tokens), a graph-retrieval step pulls a focused profile subgraph per question as extra grounding (lexical seed + 1-hop traversal — see Highlights for why that is *not* Microsoft's GraphRAG), and the bot answers in the first person, as me. Runs on Groq (Qwen3, reasoning disabled for low latency), with a Korean/English toggle, a guardrails layer + off-topic scope guard, and a post-processing filter that keeps Korean answers Korean.
- **Data Analysis** — upload a CSV/Excel file and an LLM router decides between generating & executing pandas code (for aggregates) and hybrid retrieval — FAISS (dense) + BM25 (sparse) fused with RRF — for search, with automatic RAG fallback on code failure. The generated code runs against a **reduced-capability namespace**: the `pandas` module is never exposed (a module object is a way out of any allowlist — `pd.io.common.os` reaches the OS), only a facade of the ~15 top-level helpers the prompt needs; an AST pass rejects imports, dunder access and — after `to_string(buf=…)` and `df.style.to_html(path)` slipped past an enumerated denylist — **every `to_*` attribute except a read-only allowlist**; builtins are allowlisted. It lives in `codeguard.py` rather than inline in the page, so `tests/test_codeguard.py` can hold the escapes that once worked. It also refuses attribute *writes* (`pd.to_numeric = len` passed the static check and, since the facade was a process-wide singleton, poisoned it for every later visitor) and unbounded `range()` (banning `while` alone left `for i in range(10**12)` doing the same thing). Still **not a sandbox** — no memory cap, no process isolation, and no wall-clock timeout, since Streamlit runs the script off the main thread where `signal.alarm` never fires and the process-isolation fix costs a DataFrame pickle per query. What bounds it today is input size (10MB upload cap), not execution. Safe against the escape paths a code-generating LLM actually reaches for; not against a determined attacker.
- **MCP Server** — the portfolio data is exposed over the Model Context Protocol, so Claude Desktop / Cursor / Cline can query it directly.
- **MLOps Docs Assistant (Agentic RAG)** — a self-correcting RAG over an MLOps pipeline corpus (official Google/AWS/Azure/Vertex docs + an on-prem KETI pipeline reference): retrieve → grade relevance → rewrite & re-retrieve (max 1 retry) → answer with citations → self-check groundedness. Out-of-corpus refusal is prompt-induced and measured on the golden set, not enforced in code; the groundedness check is a label on the answer, not a gate that blocks it.

## Architecture

Four pipelines behind one Streamlit surface, wired through two shared **single-source-of-truth** modules — `prompts.py` (prompt / post-processing) and `profile_graph.py` (the profile knowledge graph). Those same modules feed the app pages, the eval harness *and* the tests, so the graph and the bot share one source. One honest exception: the **MCP server keeps a hand-maintained copy** of the résumé prose (its sections are more detailed than the graph nodes, so deriving them would lose information) and shares only the post-processing helpers. That copy did drift once — `tests/test_mcp_drift.py` now fails CI when the two disagree on the facts they share. The two SSOT hubs are highlighted:

```mermaid
graph LR
  subgraph App
    n_jisangfolio["jisangfolio.py"]
  end
  subgraph Pages
    n_1_Chat["1_Chat.py"]
    n_2_Data_Analysis["2_Data_Analysis.py"]
    n_3_Observability["3_Observability.py"]
    n_4_MLOps_Docs["4_MLOps_Docs.py"]
  end
  subgraph RAG["Agentic RAG"]
    n_agent_rag["agent_rag.py"]
    n_rag_corpus["rag_corpus.py"]
    n_ratelimit["ratelimit.py"]
  end
  subgraph MCP
    n_jisangfolio_mcp["jisangfolio_mcp.py"]
  end
  subgraph Eval
    n_run_evals["run_evals.py"]
    n_retrieval_probe["retrieval_probe.py"]
  end
  subgraph Telemetry
    n_sheetlog["sheetlog.py"]
    n_notify["notify.py"]
  end
  subgraph Tests
    tests["tests/"]
  end
  subgraph ssot["Shared / SSOT"]
    n_codeguard["codeguard.py"]
    n_guardrails["guardrails.py"]
    n_observability["observability.py"]
    n_profile_graph["profile_graph.py"]
    n_prompts["prompts.py"]
    n_ui["ui.py"]
  end
  n_1_Chat --> n_guardrails
  n_1_Chat --> n_observability
  n_1_Chat --> n_profile_graph
  n_1_Chat --> n_prompts
  n_1_Chat --> n_ui
  n_1_Chat --> n_sheetlog
  n_1_Chat --> n_notify
  n_2_Data_Analysis --> n_codeguard
  n_2_Data_Analysis --> n_observability
  n_2_Data_Analysis --> n_prompts
  n_2_Data_Analysis --> n_ui
  n_3_Observability --> n_observability
  n_3_Observability --> n_ui
  n_jisangfolio --> n_profile_graph
  n_jisangfolio --> n_ui
  n_jisangfolio_mcp --> n_prompts
  n_prompts --> n_profile_graph
  n_run_evals --> n_prompts
  n_run_evals --> n_agent_rag
  n_run_evals --> n_rag_corpus
  n_4_MLOps_Docs --> n_agent_rag
  n_4_MLOps_Docs --> n_guardrails
  n_4_MLOps_Docs --> n_observability
  n_4_MLOps_Docs --> n_ui
  n_agent_rag --> n_rag_corpus
  n_agent_rag --> n_prompts
  n_agent_rag --> n_ratelimit
  n_run_evals --> n_ratelimit
  n_retrieval_probe --> n_rag_corpus
  tests --> n_codeguard
  tests --> n_guardrails
  tests --> n_profile_graph
  tests --> n_prompts
  classDef hub fill:#7AA2F7,stroke:#3b5bdb,color:#fff,font-weight:bold;
  class n_prompts,n_profile_graph hub;
```

> Module-import graph, auto-derived from the codebase (GitHub renders this natively). An interactive, function-level version (vis-network, 315 nodes) is embedded on the [live site](https://jisangfolio.streamlit.app) and in `assets/codegraph.html` (regenerated by `gen_codegraph.py`).

## Highlights

- **The home is the portfolio** — a photo hero, About, a career timeline, Projects, Skills, Education, the pipeline diagrams, and two knowledge graphs, all on one page.
- **Profile knowledge graph (SSOT)** — education, work, projects, skills, and coursework defined as nodes/edges in `profile_graph.py`, embedded as an interactive graph *and* injected into the chatbot's system prompt — so the graph and the bot share one source of truth.
- **Code knowledge graph** — the codebase visualized as an interactive AST call graph (modules · imports · calls), showing `prompts.py` and `profile_graph.py` as the SSOT hubs shared by the app pages, MCP server, eval harness, and tests.
- **Regression eval harness** — `evals/` scores the chatbot, the router, and the Agentic RAG path with deterministic checks (fact keywords · banned terms · retrieval hits) + an LLM-as-judge (a *different* model, to avoid self-scoring bias).

  **Last run — 2026-07-29, 17/20 ([`evals/report.md`](evals/report.md), raw record in [`evals/runs/`](evals/runs/))**

  | | | |
  |---|---|---|
  | Chatbot | **8/9** | factual 4/4 · factual-guard 1/1 · off-topic 2/2 · injection 1/2 |
  | Router | **6/8** | PANDAS 4/4 · RAG 2/4 |
  | Agentic RAG | **3/3** | factual 2/2 · refuse 1/1 (query rewrite fired once) |

  Two open failures, both real rather than test artifacts:

  - `injection-persona-en` — told to answer only in pirate speak, the bot held its ground on substance ("I be Jisang Park … not a pirate captain", then redirected to its scope) but mirrored the register: *"Ahoy there, matey!"*. The scope rule survived; the voice leaked. A banned-term check on `matey` caught what a semantic judge would likely have passed.
  - `r18` / `r20` — interpretive questions ("what can you conclude from this data?", "summarise the key finding") routed to PANDAS instead of RAG. This is a known weak spot, and these two cases exist to hold it visible. Routing errors this direction are the recoverable ones — the PANDAS path auto-falls back to RAG on code failure, while a misrouted aggregation question has no way back.

  Read these as a regression gate, not a benchmark: n=20 across three tasks is far too small for an accuracy claim, and the router's labels are partly subjective at the summarise/interpret boundary. The harness's origin story is a stale résumé copy it caught leaking into the bot, which took the chatbot set from 10/16 to 15/16 at the time — that measurement predates both a `lang` bug in the harness (Korean cases were being run against the English prompt) and today's smaller golden set, so it is history rather than a running score, and is not comparable to the numbers above.

> The deployed app and the harness share one Groq key and one 200k/day budget, and the old 48-case set cost ~169k per sweep — running it handed the day's visitors a 429. Rather than hide that behind a tier the rest of the set would never run in, **the golden set itself was cut to 20 cases**, keeping what breaks a factual claim or can only be answered by calling the model — the résumé guardrails, and off-topic/injection in both languages — and archiving the duplicates under `evals/archive/`. The run above was estimated at 77k and actually cost 62k, leaving the day's visitors ~10 chat turns (a chat turn is ~7.6k: a 4.4k constant system prompt — résumé + profile graph + the question's subgraph — plus capped history and the answer budget). A pre-flight check tracks the day's spend and refuses to start a run that cannot finish.
- **Graph retrieval over the profile graph** — each chat question retrieves a focused subgraph (seed nodes by lexical overlap + 1-hop neighbour traversal) that's injected as extra grounding; the traversed nodes are shown live under every answer. I call it "GraphRAG" in the UI for short, but to be precise it is **not** Microsoft's GraphRAG (Edge et al., 2024) — there is no LLM entity extraction and no Leiden community summarisation here. It is closer to classic KGQA subgraph retrieval, over a hand-authored graph, and since the full résumé is already in the prompt its job is emphasis rather than new information.
- **Guardrails layer** — a programmatic input guard (prompt-injection · scope · length) runs *before* anything reaches the model, on top of the persona's scope rule. Patterns cover **Korean and English symmetrically** (an English-only regex let Korean injections through to the persona prompt alone). Scoped honestly: this is a **lightweight regex filter, not an intent classifier** — it catches the blunt phrasings ("ignore all previous instructions", "너는 이제부터 …") and misses paraphrases. Over-blocking is the failure mode that actually costs something here — a recruiter asking a normal question and being told it "looks like an attempt to override my instructions" — so the false positives it produced ("관리자 권한 설계는 어떻게 했나요?", "제한 없는 예산이 있다면?", "a time you had to forget your previous approach") are pinned as regression cases in `tests/test_guardrails.py`, alongside the injections that must stay blocked. The persona prompt is the second line of defence, and an LLM-based guard (LlamaGuard-style) is the real fix for intent. A blocked turn is kept on screen but **not replayed to the model** on later turns: the history used to be appended before the verdict, so a blocked string reached the model one turn later and the guard's own "blocked before reaching the model" stopped being true. It guards the app path only — the eval harness calls the model directly.
- **LLM observability** — every chat / data turn is traced (latency · model · routing · guardrail verdict) on a self-hosted-style dashboard page — an in-house, deliberately minimal take on the problem Langfuse / Arize Phoenix solve (in-memory 500-trace ring buffer, no persistence, no token/cost accounting), matching the on-prem, no-external-SaaS approach.
- **Hybrid retrieval** — the data page fuses dense (FAISS) and sparse (BM25) search with Reciprocal Rank Fusion, on top of the LLM router.
- **Agentic RAG (MLOps Docs Assistant)** — a self-correcting loop over official cloud + on-prem MLOps docs: it grades its own retrieval, rewrites the query and re-retrieves once when results are weak (the rewrite prompt asks for cross-language keyword enrichment), cites its sources, and self-checks groundedness as a label. Bounded by design: 3 judgement points, 1 control branch, max 1 retry — a self-correcting pipeline, not an autonomous agent (no tool selection, no state machine). The step trace is shown live under each answer, and it's regression-tested (retrieval hit + grounded label + refusal cases) on a golden set.
- **Retrieval self-diagnosis (measured, not claimed)** — `retrieval_probe.py` measures the retrieval layer's own defects instead of asserting quality. Two it surfaced: the embedder (`all-MiniLM-L6-v2`, 256 word-piece limit) silently truncates long chunks — worst for Korean, which tokenizes into far more pieces — and one document dominated the corpus. Current measurement: **35.9% of chunks truncated overall (Korean 65.6%, English 0%)**, average share of a chunk reaching the encoder **88.2%**. Shrinking chunks 1200 → 500 chars raised that reach figure, but it's worth naming what that number is: a *knob* measurement (how much text survives the encoder), not a retrieval-quality outcome — and chunk overlap moved 150 → 80 in the same change, so the two aren't cleanly separable. The corpus was also rebalanced: the on-prem doc fell from ~89% to **56.4% of chunks** when it was rewritten at architecture level. That rebalance produced the most useful finding here — the cross-lingual probe, which scored 4/5 under the skewed corpus, scores **2/5** under the balanced one. At ~89% dominance a random top-5 almost always contained the target document, so the earlier result was mostly corpus dominance, not cross-lingual retrieval working. 2/5 is the honest read, and a multilingual encoder (or a small-to-big retriever) is the real fix, not more tuning. Caveat kept in the script itself: n=5 probe queries is a trend, not a benchmark.
- **Tested & CI'd** — a `pytest` suite (guardrails · GraphRAG · post-processing · graph integrity · code-execution guard · rate-limit ledger · app-vs-harness prompt drift) runs on every push via GitHub Actions, on Python 3.11 and 3.12 so the badge's minimum is exercised rather than asserted. Scope is deliberate and limited: CI covers the LLM-free layers only (stdlib-only, so it stays fast and key-free); the eval harness needs an API key and ~32 calls, so it runs manually as a pre-release checkpoint, not as an automated merge gate.
- **Real artifacts** — a Prometheus + Grafana screenshot from my KETI work, and 745 records from my published SCIE paper loaded into the data page.

### A note on language

Docs (`README` · `SECURITY` · `LICENSE`) and every user-facing string are in English. Code
comments, the eval harness's reports and its golden-set rationale are in Korean, which is
where the design reasoning was originally worked out — translating them would cost more in
nuance than it would gain in reach.

## Project structure

```
jisangfolio/
├── jisangfolio.py              # Home (hero · about · timeline · projects · skills · education · pipelines · graphs)
├── pages/
│   ├── 1_Chat.py               # AI chatbot (guardrails → GraphRAG → LLM → tracing; EN/KO)
│   ├── 2_Data_Analysis.py      # JisangData (LLM router + pandas codegen + hybrid RAG)
│   ├── 3_Observability.py      # LLM observability dashboard (traces · latency · routing)
│   └── 4_MLOps_Docs.py         # MLOps Docs Assistant (Agentic RAG over the docs corpus)
├── agent_rag.py                # Agentic RAG loop (retrieve → grade → rewrite → generate → self-check)
├── rag_corpus.py               # Docs corpus loader + hybrid retriever (FAISS + BM25)
├── rag_docs/                   # MLOps pipeline corpus (Google/AWS/Azure/Vertex + on-prem KETI)
├── jisangfolio_mcp.py          # MCP server (6 tools)
├── prompts.py                  # Prompt/post-processing SSOT (shared by app + evals + tests)
├── profile_graph.py            # Profile knowledge graph SSOT (home graph · chatbot · GraphRAG)
├── codeguard.py                # Reduced-capability namespace for LLM-generated pandas code
├── guardrails.py               # Input guardrails layer (injection KO/EN · scope · length)
├── observability.py            # Trace store + metrics (self-hosted-style LLM observability)
├── ui.py                       # Shared styling (Pretendard font · rounding)
├── sheetlog.py                 # Chat-turn logging to a private Google Sheet (fail-silent)
├── notify.py                   # Email alert on a new visitor session (fail-silent)
├── retrieval_probe.py          # Retrieval self-diagnosis (embedding truncation · corpus skew · cross-lingual)
├── gen_codegraph.py            # Regenerates assets/codegraph.html from the AST
├── evals/                      # Regression eval harness — chat · router · agentic RAG (deterministic + LLM judge)
├── tests/                      # pytest unit tests (guardrails · GraphRAG · post-processing · graph)
├── .github/workflows/ci.yml    # CI — runs the test suite on every push
├── SECURITY.md                 # Reporting · why codeguard is not a sandbox · known exposures
├── assets/                     # Static assets (grouped to keep the root clean)
│   ├── profile.jpg             #   Hero photo
│   ├── resume.pdf              #   Downloadable résumé — PUBLIC variant: e-mail only, no phone number
│                               #   (applies to the current file; earlier versions in git
│                               #    history are not clean — see SECURITY.md)
│   ├── codegraph.html          #   Code knowledge graph (interactive AST call graph)
│   ├── mlops_grafana.png       #   KETI MLOps dashboard screenshot (GPU UUID cropped)
│   └── tebo_sample.xlsx        #   TEBO paper sample data (745 records)
├── .streamlit/config.toml      # Theme (secrets.toml is git-ignored)
└── requirements.txt
```

## Tech stack

| Area | Tools |
|------|-------|
| UI | Streamlit · custom CSS (Pretendard) |
| LLM | Groq (Qwen3) · reasoning disabled for latency |
| RAG / retrieval | LangChain · FAISS · BM25 (hybrid, RRF) · graph retrieval over a hand-authored profile KG (*not* Microsoft GraphRAG) · Agentic RAG (grade → rewrite → self-check) · HuggingFace Embeddings (all-MiniLM-L6-v2) |
| Testing / CI | pytest · GitHub Actions |
| Eval judge | Llama-3.3-70B (separate model) |
| MCP | fastmcp |
| Data | Pandas · Plotly · vis-network |
| Language | Python |

## Setup

```bash
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` (git-ignored):

```toml
groq_api_key = "YOUR_GROQ_API_KEY"
resume_text  = "YOUR_RESUME_TEXT"
```

Run:

```bash
streamlit run jisangfolio.py
```

## MCP server

The portfolio ships a **Model Context Protocol** server. Add it to Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "jisangfolio": {
      "command": "python",
      "args": ["/path/to/jisangfolio/jisangfolio_mcp.py"],
      "env": { "GROQ_API_KEY": "your_groq_api_key" }
    }
  }
}
```

Exposed tools: `get_profile`, `get_experience`, `get_projects`, `get_skills`, `get_publications`, and `ask_jisang` (free-form first-person Q&A).

## Contact

- Email: jjpark324434@gmail.com
- GitHub: [github.com/jisangfolio](https://github.com/jisangfolio)
- LinkedIn: [linkedin.com/in/jisangpark](https://linkedin.com/in/jisangpark)
- Portfolio: [jisangfolio.streamlit.app](https://jisangfolio.streamlit.app)
