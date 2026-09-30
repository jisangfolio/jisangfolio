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
      "args": ["/absolute/path/to/jisangfolio/jisangfolio_mcp.py"],
      "env": { "GROQ_API_KEY": "your_groq_api_key" }
    }
  }
}
"""

from fastmcp import FastMCP
from prompts import clean_response

# ⚠️ 드리프트 주의: 아래 _PROFILE/_KETI/... 는 profile_graph.py(프로필 SSOT)에서 파생된 게 아니라
# 손으로 관리하는 2차 사본이다. profile_graph 노드보다 서술이 상세해 자동 파생이 어렵기 때문인데,
# 그래서 이력서 사실이 바뀌면 **여기도 같이 고쳐야 한다**. tests/test_mcp_drift.py 가
# 두 소스가 공유하는 핵심 사실이 어긋나면 실패시켜 이 위험을 붙잡는다.

mcp = FastMCP("JisangFolio — Jisang Park portfolio")

# ── Portfolio data (single source for the MCP tools) ─────────────────
_PROFILE = """
Name: Jisang Park (박지상)
Current: Financial Engineering Research Institute, Yonhap Infomax (since Sep 2026)
Education: B.S. Information Science + Data Science (iSchool), UIUC · GPA 3.89/4.0 · Dec 2025
Prior role: Research engineer, AX Research Division, Korea Electronics Technology Institute (KETI) — on-prem MLOps (contract, Feb–Sep 2026)
Prior school: University of Washington, Seattle (Pre-Science, 2019–2024)
Military: ROK Navy, honorable discharge as Sergeant — English interpreter (Feb 2021–Oct 2022), incl. ~10 months aboard ROKS Gwangju and interpretation for ROK–US Combined Forces
Languages: Korean (native), English (near-native — TOEIC 970 · OPIc IH; ~10 years in the U.S.)
Contact: jjpark324434@gmail.com | linkedin.com/in/jisangpark | github.com/jisangfolio
Portfolio: jisangfolio.streamlit.app
"""

_KETI = """
[KETI — Research Engineer (Contract), AX Research Division]
Period: Feb 2026 – Sep 2026 / contract

▸ Project 1: A municipal digital-twin integration (Feb–Apr 2026, done)
  - Integrated 3 parts (data platform / SWMM simulator / Unity viz) and registered NGSI-LD data models
  - Analyzed the MQTT + HTTP hybrid comms structure; applied a Ports-and-Adapters pattern
  - Documented the integration & sequence diagrams and presented internally

▸ Project 2: Self-hosted on-premise MLOps platform, built for closed-network constraints (since Mar 2026, ongoing)
  - Led the design & build of a model-agnostic, open-source MLOps platform that serves/manages multiple models without external SaaS or cloud
    (the urban-cooling AI research is the backdrop — a partner university's 3D U-Net and an external team's PINNs run on top of it as use cases)
  - Partner-university PyTorch 3D U-Net (+CBAM +Attention Gate) → ONNX → Triton GPU serving
  - Unified 3 PINN models from an external team on the same Triton — voxel/point I/O heterogeneous models, the platform's first external use case
  - Consolidating training data that had arrived in separate splits and retraining improved the error and fit, compared version-to-version in MLflow (the project's metric values are not disclosed — they are a national-programme deliverable, not mine to publish)
  - Latency: a 100-point PINN request in 22–32 ms on an L40S (the CFD runtime of tens of minutes is the partner university's figure, not my measurement)
  - Stack: MLflow (tracking·registry·artifact serving) + Gitea + Gitea Actions CI + Triton + Prometheus + Grafana
  - Jun 2026: Streamlit ops portal (5 views) · Evidently drift dashboard (PoC) · ONNX validate→deploy CI (manual trigger, 1 end-to-end run)
  - Aug–Sep 2026: eight Gitea Actions workflows — weekly train → manifest-driven gate (thresholds live in a project manifest, not in code) → ONNX export attached to the registry version → checksum-verified deploy; first unattended end-to-end run 2026-09-12 (Google MLOps Level 1). Gate rejected 2 versions (v6, v8); deployed v12's ONNX hash matches the serving file. A 10-menu operations console (Python http.server + Vue, no build step) calls the gate when training finishes, auto-recovers serving every 60 s, reconciles declared vs. actual, and triggers retraining on input-range drift (fired once in a demo with lowered thresholds (5 samples / 1 day vs. the default 50 / 3 days), 17–19 samples). A twice-daily check publishes console findings as Gitea issues and closes them automatically.
  - Known limits: no training-data refresh path (retraining does not improve the model), CI has syntax checks only (no behavioral tests), no rollback, inference traffic still smoke-level
  - Artifact store: MinIO was dropped over an AGPL license concern → MLflow local store (--serve-artifacts)
  - Self-hosting principle (org policy): avoid external SaaS/cloud → GitHub→Gitea, cloud monitoring→Prometheus+Grafana
  - Role: architecture design, tooling selection, environment build/ops, experiments, analysis, presentations
"""

_SDI = """
[Samsung SDI — Data Engineer Intern, DI (Data Intelligence) Group]
Period: Jun 2025 – Aug 2025

▸ Built "SPA (SDI Patent Assistant)", an air-gapped patent-search RAG chatbot — my part was retrieval, routing and UI; LLM serving was set up by my mentor
  - Fully internet-blocked environment; the LLM runtime was Ollama + Qwen2.5-72B, set up by my mentor
  - LangChain + FAISS vector DB; loaded patent.csv from MinIO
  - Kept context over the last 5 turns + stored prior RAG choices → auto re-retrieval on follow-ups
  - Rule-based agent: on "chart/stats/filing" keywords the chart is computed straight from the DataFrame and the LLM is instructed not to answer that query — so the numbers come from data. Worth stating plainly: the code streams the LLM on every query, so that silence is a prompt instruction, not a structural guarantee
  - Streamlit UI + Docker; praised in an executive PoC
"""

_PROJECTS = """
[Key projects]

1. KETI self-hosted on-prem MLOps platform (built for closed-network constraints)
   - PyTorch 3D U-Net + 3 external PINNs → ONNX → NVIDIA Triton heterogeneous serving
   - MLflow · Gitea · Gitea Actions · Prometheus · Grafana + Streamlit ops portal · Evidently drift (PoC)
   - Consolidated training data + retraining improved error and fit, judged by version-to-version comparison in MLflow (metric values not disclosed)
   - Stack: PyTorch, ONNX, Triton, MLflow, Gitea, Docker Compose, Prometheus, Grafana, Evidently, Streamlit

2. Samsung SDI SPA — air-gapped patent RAG chatbot
   - Fully internet-blocked; I owned retrieval, routing and the UI (LLM serving was my mentor's)
   - Rule-based agent + RAG hybrid; praised in an executive PoC
   - Stack: Ollama, Qwen2.5-72B, LangChain, FAISS, Streamlit, Docker

3. TEBO balance analysis · SCIE paper (co-author, 7th of 10)
   - Applied Sciences (SCIE), Jul 2025
   - My part started after data collection: reconciled two cohorts' overlapping subject IDs,
     scored and aggregated the FES-I (fear-of-falling) survey by group, produced simulated
     stabilogram visualisations (not measured sway, and not figures in the published paper)
   - CRediT roles: formal analysis, data curation, visualization. The signal filtering and
     component decomposition were the research team's work, not mine
   - Stack: Python, Pandas, NumPy, Matplotlib

[Personal projects]

4. JisangFolio (jisangfolio.streamlit.app)
   - An AI interview chatbot built from my résumé + a data-analysis tool
   - Groq + Qwen3 27B, full résumé injected into the system prompt (no RAG needed)
   - LLM router → pandas codegen executed in a reduced-capability namespace (not a sandbox), or FAISS RAG (with hybrid retrieval)
   - Graph retrieval over a profile knowledge graph (lexical seed + 1-hop traversal; not Microsoft GraphRAG),
     a programmatic guardrails layer, and a self-hosted-style LLM observability dashboard
   - MLOps Docs Assistant (Agentic RAG): self-correcting loop over cloud + on-prem MLOps docs —
     retrieve → grade → rewrite & re-retrieve → cite → self-check groundedness; refuses out-of-corpus questions
   - Hybrid retrieval (FAISS dense + BM25 sparse, fused with RRF)
   - Regression eval harness + GitHub Actions CI
   - This MCP server is itself part of JisangFolio
   - Stack: Streamlit, Groq, LangChain, FAISS, Plotly, fastmcp
"""

_SKILLS = """
[AI / LLM]
LangChain, RAG, Agentic RAG (self-correcting retrieve-grade-rewrite loop), graph retrieval, FAISS
Hybrid retrieval (BM25 + dense, RRF), Prompt Engineering, Hugging Face, PyTorch, ONNX
Rule-based Agent, Ollama, Groq, MCP (fastmcp), LLM eval (LLM-as-judge), Guardrails

[MLOps / LLMOps]
MLflow (tracking + model registry + artifact serving), NVIDIA Triton Inference Server
Gitea (self-hosted Git), Gitea Actions & GitHub Actions (CI), ONNX Runtime
Prometheus, Grafana (PromQL, dashboards), Evidently (data drift, PoC)
LLM observability (tracing · latency · routing), Streamlit ops portal
Docker, Docker Compose

[Data Science]
Pandas, NumPy, Matplotlib, spaCy
Survey scoring & group aggregation, stabilogram visualisation (vector EPS), hybrid retrieval (BM25 + dense)

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

[My contribution — CRediT: formal analysis, data curation, visualization]
- Reconciled two participant datasets (PCD · TCOA) and resolved overlapping subject IDs by
  reassigning them into a separate range, so the cohorts could be merged without collision
- Scored the fear-of-falling (FES-I) survey and aggregated it by group
- Produced stabilogram visualisations as vector EPS — simulated trajectories scaled to the band-power
  metrics the lab supplied, not measured sway. The published paper contains no stabilogram either
- Groups compared in the paper: healthy young (23) / healthy older (21) / Tai-Chi-practising
  older adults, TCOA (15) — 59 participants in total. TCOA is a Tai Chi group, not a clinical one
- I am the 7th of 10 authors (not first or corresponding)

[Not my work — stated so it is not inferred]
The signal-processing stage — low-pass filtering, decomposing sway into its low- and
high-frequency components, and integrating spectral band power — was the research team's; the paper's CRediT methodology/software roles do
not include me, and I consumed those metrics as spreadsheet inputs. An individual abstract I
wrote in 2025 claimed that pipeline in the first person and reported correlation numbers for it;
both were wrong and are retired — the figures in question were simulated trajectories, and the
published paper contains no stabilogram to compare against.
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
    # 후처리는 prompts.clean_response 하나만 쓴다. 예전엔 여기서 </think> 를 직접 잘랐고,
    # 그 사본이 두 경우에 앱과 다르게 굴었다:
    #   · 닫히지 않은 <think> → 앱은 ""       / 여기선 **사고 과정을 원문 그대로 노출**
    #   · 문장 중간 <think>   → 앱은 앞뒤 보존 / 여기선 앞 문장을 통째로 버림
    # README 가 "MCP 서버는 후처리 헬퍼를 공유한다"고 적어둔 바로 그 지점이었다.
    return clean_response(content)


if __name__ == "__main__":
    mcp.run()
