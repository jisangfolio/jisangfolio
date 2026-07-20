"""
JisangFolio MCP Server
An MCP server that lets Claude Desktop / Cursor / Cline query Jisang Park's portfolio directly.

All portfolio data lives in the module-level constants below (single place to edit — no
copies scattered across the tool functions), keeping the MCP tools drift-free and in English.

Connect (claude_desktop_config.json):
{
  "mcpServers": {
    "jisangfolio": {
      "command": "python",
      "args": ["/Users/jjpark/Desktop/info/jisangfolio/jisangfolio_mcp.py"],
      "env": { "GROQ_API_KEY": "your_groq_api_key" }
    }
  }
}
"""

from fastmcp import FastMCP
from prompts import strip_foreign_cjk

mcp = FastMCP("JisangFolio — Jisang Park portfolio")

# ── Portfolio data (single source for the MCP tools) ─────────────────
_PROFILE = """
Name: Jisang Park (박지상)
Current: Researcher, AX Research Division, Korea Electronics Technology Institute (KETI) — AI agent development (contract, since Feb 2026)
Education: B.S. Information Science + Data Science (iSchool), UIUC · GPA 3.89/4.0 · Dec 2025
Prior: University of Washington, Seattle (Pre-Science, 2019–2024)
Military: ROK Navy, honorable discharge as Sergeant — English interpreter (Feb 2021–Oct 2022), incl. ~10 months aboard ROKS Gwangju and interpretation for ROK–US Combined Forces
Languages: Korean (native), English (near-native — TOEIC 970 · OPIc IH; ~10 years in the U.S.)
Contact: jjpark324434@gmail.com | linkedin.com/in/jisangpark | github.com/jisangfolio
Portfolio: jisangfolio.streamlit.app
"""

_KETI = """
[KETI — Researcher, AX Research Division (AI agent development)]
Period: Feb 2026 – present / contract

▸ Project 1: Songsan Green City digital-twin integration (Feb–Apr 2026, done)
  - Integrated 3 parts (data platform / SWMM simulator / Unity viz) and registered NGSI-LD data models
  - Analyzed the MQTT + HTTP hybrid comms structure; applied a Ports-and-Adapters pattern
  - Documented the integration & sequence diagrams and presented internally

▸ Project 2: Air-gapped, self-hosted MLOps platform (since Mar 2026, ongoing)
  - Led the design & build of a model-agnostic, open-source MLOps platform that serves/manages multiple models in an air-gapped network
    (the urban-cooling AI research is the backdrop — a PKNU 3D U-Net and an external team's PINNs run on top of it as use cases)
  - PKNU-provided PyTorch 3D U-Net (+CBAM +Attention Gate) → ONNX → Triton GPU serving
  - Unified 3 external (U-Ecotron) PINN models on the same Triton — voxel/point I/O heterogeneous models, the platform's first external use case
  - Round 1 (45 samples): MAE 0.53°C, R² 0.82 → Round 2 (291 samples integrated): MAE 0.26°C, R² 0.95 (MAE ↓51%)
  - CFD simulation (tens of minutes, PKNU-provided) → Triton inference ~200ms
  - Stack: MLflow (tracking·registry·artifact serving) + Gitea + Gitea Actions CI + Triton + Prometheus + Grafana
  - New (Jun 2026): Streamlit ops portal (6 pages) · Evidently drift dashboard (PoC) · ONNX validate→deploy CI (manual trigger)
  - Artifact store: MinIO was dropped over an AGPL license concern → MLflow local store (--serve-artifacts)
  - Self-hosting principle (org policy): avoid external SaaS/cloud → GitHub→Gitea, cloud monitoring→Prometheus+Grafana
  - Role: architecture design, tooling selection, environment build/ops, experiments, analysis, presentations
"""

_SDI = """
[Samsung SDI — Data Engineer Intern, DI (Data Intelligence) Group]
Period: Jun 2025 – Aug 2025

▸ Solo-built "SPA (SDI Patent Assistant)", an air-gapped patent-search RAG chatbot
  - Fully internet-blocked environment; self-hosted Ollama + Qwen2.5-72B
  - LangChain + FAISS vector DB; loaded patent.csv from MinIO
  - Kept context over the last 5 turns + stored prior RAG choices → auto re-retrieval on follow-ups
  - Rule-based agent: "chart/stats/filing" keywords → bypass the LLM → pandas aggregation + st.bar_chart
  - Streamlit UI + Docker; praised in an executive PoC
"""

_PROJECTS = """
[Key projects]

1. KETI air-gapped, self-hosted MLOps platform
   - PyTorch 3D U-Net + 3 external PINNs → ONNX → NVIDIA Triton heterogeneous serving
   - MLflow · Gitea · Gitea Actions · Prometheus · Grafana + Streamlit ops portal · Evidently drift (PoC)
   - Round 2 (291 samples) improved MAE by 51%, R² 0.95
   - Stack: PyTorch, ONNX, Triton, MLflow, Gitea, Docker Compose, Prometheus, Grafana, Evidently, Streamlit

2. Samsung SDI SPA — air-gapped patent RAG chatbot
   - Fully internet-blocked, solo-built
   - Rule-based agent + RAG hybrid; praised in an executive PoC
   - Stack: Ollama, Qwen2.5-72B, LangChain, FAISS, Streamlit, Docker

3. TEBO balance analysis · SCIE paper (co-author)
   - Applied Sciences (SCIE), Jul 2025
   - CoP time-series → 4th-order Butterworth (6Hz) + FFT → Rambling/Trembling decomposition
   - Individual abstract simulation: R² ≈ 0.85, Pearson r = 0.92 (p<0.001)
   - Stack: Python, NumPy, SciPy, Matplotlib

[Personal projects]

4. JisangFolio (jisangfolio.streamlit.app)
   - An AI interview chatbot built from my résumé + a data-analysis tool
   - Groq + Qwen3 27B, full résumé injected into the system prompt (no RAG needed)
   - LLM router → pandas codegen & sandbox exec, or FAISS RAG (with hybrid retrieval)
   - GraphRAG over a profile knowledge graph, a programmatic guardrails layer, and a self-hosted-style LLM observability dashboard
   - Regression eval harness + GitHub Actions CI
   - This MCP server is itself part of JisangFolio
   - Stack: Streamlit, Groq, LangChain, FAISS, Plotly, fastmcp
"""

_SKILLS = """
[AI / LLM]
LangChain, RAG, GraphRAG, FAISS, Prompt Engineering, Hugging Face, PyTorch, ONNX
Rule-based Agent, Ollama, Groq, MCP (fastmcp), LLM eval (LLM-as-judge), Guardrails

[MLOps / LLMOps]
MLflow (tracking + model registry + artifact serving), NVIDIA Triton Inference Server
Gitea (self-hosted Git), Gitea Actions & GitHub Actions (CI), ONNX Runtime
Prometheus, Grafana (PromQL, dashboards), Evidently (data drift, PoC)
LLM observability (tracing · latency · routing), Streamlit ops portal
Docker, Docker Compose

[Data Science]
Pandas, NumPy, Matplotlib, SciPy, spaCy
Butterworth filter, FFT, time-series analysis, hybrid retrieval (BM25 + dense)

[Visualization]
Streamlit, Plotly, Tableau, Power BI

[IoT / Platform]
NGSI-LD, MQTT, REST API, Postman, SWMM

[Languages]
Python (advanced), R, SQL

[Tools]
Git, GitHub, Gitea, Docker, VSCode, Claude Code
"""

_PUBLICATIONS = """
[Published paper]
Title: "Effect of Tai Chi Practice on the Adaptation to Sensory and Motor Perturbations While Standing in Older Adults"
Journal: Applied Sciences (SCIE)
Date: Jul 2025
Advisor: Dr. Manuel E. Hernandez (UIUC)

[My contribution]
- Solo-designed & implemented the full CoP (center-of-pressure) time-series analysis pipeline
- 4th-order Butterworth low-pass filter (6Hz cutoff) → sensor-noise filtering
- Zero-crossing equilibrium detection → cubic-spline interpolation to reconstruct Rambling
- FFT → integrated 0–0.3Hz → low-frequency Rambling power
- Compared Young (n=1) / Healthy Older (n=37) / TCOA clinical (n=22) groups
- Note: on the published paper I am a co-author (not first/corresponding author)

[Individual abstract — sole author; source of the simulation numbers below]
Title: "Postural Control in Healthy and TCOA Adults: Rambling-Component Analysis and Simulated CoP Trajectories"
Author: JJ Park (sole)
- A single Rambling-power metric explained 85%+ of sway variance (R² ≈ 0.85)
- Simulated area vs. actual stabilogram: Pearson r = 0.92 (p<0.001)
"""


@mcp.tool()
def get_profile() -> str:
    """Return Jisang Park's basic profile, education, and contact info."""
    return _PROFILE


@mcp.tool()
def get_experience(company: str = "") -> str:
    """Return work experience. Pass 'KETI' or 'Samsung' (Samsung SDI) to get only that role."""
    c = company.upper()
    if "KETI" in c:
        return _KETI
    if "SAMSUNG" in c or "SDI" in c or "삼성" in company:
        return _SDI
    return _KETI + "\n" + _SDI


@mcp.tool()
def get_projects() -> str:
    """Return key projects and personal projects."""
    return _PROJECTS


@mcp.tool()
def get_skills() -> str:
    """Return the tech stack by category."""
    return _SKILLS


@mcp.tool()
def get_publications() -> str:
    """Return publications and academic work."""
    return _PUBLICATIONS


@mcp.tool()
def ask_jisang(question: str) -> str:
    """Ask Jisang anything — Groq + Qwen3 27B answers in the first person.
    Requires the GROQ_API_KEY environment variable."""
    import os
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "GROQ_API_KEY is not set. Please check the 'env' section of claude_desktop_config.json."

    resume_context = "\n\n".join([
        _PROFILE, _KETI, _SDI, _PROJECTS, _SKILLS, _PUBLICATIONS,
    ])

    system_prompt = f"""/no_think
You are 'Jisang Park (JJ Park)', a data engineer and AI developer.
Answer the question in the first person, based on the [Résumé] below.
- Answer in English.
- Do not use bold text (**).
- Don't make up anything not in the résumé.

[Résumé]
{resume_context}"""

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        max_tokens=800,
        reasoning_effort="none",  # thinking off → faster
    )
    content = response.choices[0].message.content or ""
    if "</think>" in content:
        content = content.split("</think>", 1)[1].lstrip("\n")
    return strip_foreign_cjk(content.replace("**", ""))


if __name__ == "__main__":
    mcp.run()
