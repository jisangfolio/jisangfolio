# JisangFolio

> **A résumé you talk to.** Instead of emailing yet another PDF, I built an interactive AI portfolio you can ask anything about my experience — plus a live data-analysis demo and an MCP server. English by default, with a Korean toggle.

🔗 **Live:** [jisangfolio.streamlit.app](https://jisangfolio.streamlit.app)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/LLM-Groq_Qwen3-F55036?logo=groq&logoColor=white)](https://groq.com/)
[![MCP](https://img.shields.io/badge/MCP-Server-blueviolet?logo=anthropic&logoColor=white)](https://modelcontextprotocol.io/)

## Overview

JisangFolio is an interactive AI portfolio for **Jisang Park** — an AI · MLOps engineer. Three independent pipelines run behind one Streamlit surface:

- **Chat** — the résumé is injected directly into the system prompt (no RAG needed for ~3K tokens) and the bot answers in the first person, as me. Runs on Groq (Qwen3, reasoning disabled for low latency), with a Korean/English toggle, an off-topic scope guard, and a post-processing filter that keeps Korean answers Korean.
- **Data Analysis** — upload a CSV/Excel file and an LLM router decides between generating & sandbox-executing pandas code (for aggregates) and FAISS RAG (for search), with automatic RAG fallback on code failure.
- **MCP Server** — the portfolio data is exposed over the Model Context Protocol, so Claude Desktop / Cursor / Cline can query it directly.

## Highlights

- **The home is the portfolio** — a photo hero, About, Experience, Projects, Skills, Education, and Contact, all in one page.
- **Profile knowledge graph (SSOT)** — education, work, projects, skills, and coursework defined as nodes/edges in `profile_graph.py`, embedded as an interactive graph *and* injected into the chatbot's system prompt — so the graph and the bot share one source of truth.
- **Code knowledge graph** — the codebase visualized as an interactive call graph (Graphify, local AST), showing `prompts.py` as the hub that links the app pages and the eval harness.
- **Regression eval harness** — `evals/` scores the chatbot and router with deterministic checks (fact keywords · banned terms) + an LLM-as-judge (a *different* model, to avoid self-scoring bias). It once caught a stale résumé copy leaking into the bot and lifted factual accuracy from 62% to 94%.
- **Real artifacts** — a Prometheus + Grafana screenshot from my KETI work, and 745 records from my published SCIE paper loaded into the data page.

## Project structure

```
jisangfolio/
├── jisangfolio.py              # Home (hero · about · experience · projects · skills · education · contact · graphs)
├── pages/
│   ├── 1_Chat.py               # AI chatbot (EN/KO)
│   └── 2_Data_Analysis.py      # JisangData (LLM router + pandas codegen + RAG)
├── jisangfolio_mcp.py          # MCP server (6 tools)
├── prompts.py                  # Prompt/post-processing SSOT (shared by app + evals)
├── profile_graph.py            # Profile knowledge graph SSOT (home graph + chatbot injection)
├── ui.py                       # Shared styling (Pretendard font · rounding)
├── evals/                      # Regression eval harness (deterministic + LLM judge)
├── tebo_sample.xlsx            # TEBO paper sample data (745 records)
├── mlops_grafana.png           # KETI MLOps dashboard screenshot
├── codegraph.html              # Code knowledge graph (Graphify)
├── profile.jpg                 # Hero photo
├── resume.pdf                  # Downloadable résumé
├── .streamlit/config.toml      # Theme (secrets.toml is git-ignored)
└── requirements.txt
```

## Tech stack

| Area | Tools |
|------|-------|
| UI | Streamlit · custom CSS (Pretendard) |
| LLM | Groq (Qwen3) · reasoning disabled for latency |
| RAG / Vector DB | LangChain · FAISS · HuggingFace Embeddings (all-MiniLM-L6-v2) |
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
