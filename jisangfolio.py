import streamlit as st
import plotly.express as px
import pandas as pd
import os

st.set_page_config(
    page_title="JisangFolio",
    page_icon="🧑‍💻",
    layout="centered"
)

# SNS 공유용 OG 메타태그
st.markdown("""
<meta property="og:title" content="JisangFolio - 읽지 말고 대화하는 이력서">
<meta property="og:description" content="박지상의 AI 인터랙티브 포트폴리오. AI와 대화하며 경험과 역량을 확인하세요.">
<meta property="og:url" content="https://jisangfolio.streamlit.app">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="JisangFolio - 읽지 말고 대화하는 이력서">
<meta name="twitter:description" content="박지상의 AI 인터랙티브 포트폴리오. AI와 대화하며 경험과 역량을 확인하세요.">
""", unsafe_allow_html=True)

# --- 사이드바: 언어 선택 + 링크 ---
with st.sidebar:
    lang = st.radio("Language / 언어", ["한국어", "English"], horizontal=True)
    st.divider()
    st.markdown("**박지상 (Jisang Park)**")
    st.markdown("✉️ jjpark324434@gmail.com")
    st.markdown("🔗 [LinkedIn](https://linkedin.com/in/jisangpark)")
    st.markdown("💻 [GitHub](https://github.com/jisangfolio)")
    st.divider()

    resume_path = os.path.join(os.path.dirname(__file__), "resume.pdf")
    if os.path.exists(resume_path):
        with open(resume_path, "rb") as f:
            st.download_button(
                label="📄 이력서 다운로드" if lang == "한국어" else "📄 Download Resume",
                data=f,
                file_name="Jisang_Park_Resume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        st.caption("(resume.pdf를 프로젝트 루트에 넣으면 다운로드 버튼이 활성화됩니다)")
    st.divider()
    st.caption("AI는 실수를 할 수 있습니다. 중요한 정보는 직접 확인해 주세요.")

# ── 언어별 텍스트 ────────────────────────────────────────────────
T = {
    "한국어": {
        "title": "박지상 (Jisang Park)",
        "subtitle": "Data Engineer · AI Researcher",
        "location": "📍 KETI AX연구본부 &nbsp;|&nbsp; 🎓 UIUC Information Science + Data Science",
        "tagline_head": "## 📖 읽지 말고 대화하는 이력서",
        "tagline_body": (
            "정적인 PDF 이력서의 한계를 넘어, 저의 모든 경험과 역량을 AI가 직접 전달합니다.  \n"
            "채용 담당자가 궁금한 것을 바로 물어볼 수 있는 인터랙티브 포트폴리오입니다."
        ),
        "how_head": "## ⚙️ 이 포트폴리오, 직접 만들었습니다",
        "how_intro": "단순 소개 페이지가 아닙니다. 세 개의 독립적인 AI 파이프라인이 실시간으로 작동하고 있습니다.",
        "arch_tab1": "💬 채팅 파이프라인",
        "arch_tab2": "📂 데이터 분석 파이프라인",
        "arch_tab3": "🔌 MCP 서버 파이프라인",
        "arch": [
            "📄 **마스터 이력서**\n\nStreamlit Secrets에 주입된 이력서 전문\n_(~3K 토큰 · RAG 불필요)_",
            "✨ **Groq · Qwen3 32B**\n\n시스템 프롬프트 전문 주입\n`/no_think` · `<think>` 스트리밍 필터",
            "💬 **1인칭 스트리밍**\n\n멀티턴 대화 이력 유지\n박지상 본인처럼 실시간 답변",
        ],
        "arch_data": [
            "📤 **파일 업로드**\n\nCSV/Excel → DataFrame\nchunk_size=1000 분할 + FAISS 임베딩",
            "🔀 **LLM 라우터**\n\n질문 유형 자동 판별\n`PANDAS` or `RAG` 2분기",
            "⚙️ **PANDAS 경로**\n\n코드 생성 → 샌드박스 exec\n실패 시 RAG 자동 폴백",
            "🔍 **RAG 경로**\n\nFAISS + HuggingFace 임베딩\n멀티턴 컨텍스트 포함 답변",
        ],
        "arch_mcp": [
            "🤖 **MCP 클라이언트**\n\nClaude Desktop · Cursor · Cline\nstdio로 서버 연결",
            "🔌 **fastmcp 서버**\n\n프로필·경력·프로젝트·기술·논문\n6개 툴 노출",
            "✨ **동적 Q&A**\n\n`ask_jisang` → Groq · Qwen3 32B\n1인칭 실시간 답변",
        ],
        "rag_note": "",
        "timeline_head": "## 📅 경력 타임라인",
        "proj_head": "## 🛠️ 주요 프로젝트",
        "projects": [
            {
                "title": "🔬 KETI AX연구본부 AI 에이전트 연구",
                "period": "2026.02 ~ 현재 · AI 연구원",
                "desc": "MLOps 도시냉각 AI 서빙 인프라 구축(주력): 부경대 제공 PyTorch 3D U-Net을 ONNX 변환 → Triton GPU 서빙으로 운영 배포(CFD 수십 분 대비 추론 ~200ms). MLflow Tracking·Registry 도입으로 v1↔v2 비교 검증 — MAE 0.53→0.26°C, R² 0.82→0.95(MAE 51%↓). 자체호스팅 스택(MLflow·MinIO·Gitea·Triton) 아키텍처 설계·기술 선정. (별도) 송산그린시티 디지털 트윈 3파트 운영 환경 연동·검증.",
                "tags": "`PyTorch` `Triton` `ONNX` `MLflow` `MinIO` `NGSI-LD` `Docker`",
            },
            {
                "title": "🏭 삼성SDI 폐쇄망 RAG",
                "period": "2025.06 ~ 08 · 인턴",
                "desc": "완전 인터넷 차단 환경에서 특허 검색 RAG 챗봇 **1인 단독 개발**. 대화 이력 기반 재검색 로직 설계, 핵심 지표 집계·시각화 기능 포함 → 임원 PoC 호평",
                "tags": "`Ollama` `LangChain` `FAISS` `Docker` `Streamlit`",
            },
            {
                "title": "📊 TEBO 균형 분석 · SCIE 논문",
                "period": "Applied Sciences, 2025.07 게재",
                "desc": "CoP 시계열에 Butterworth Filter(4차) + FFT 적용, Rambling/Trembling 분해로 데이터 설명력 **85%+ 달성**",
                "tags": "`Python` `SciPy` `FFT` `시계열 분석`",
            },
        ],
        "stack_head": "## 🧰 기술 스택",
        "stacks": [
            ("**AI / LLM**", "LangChain · RAG · FAISS  \nOllama · Groq · PyTorch  \nRule-based Agent · Prompt Engineering"),
            ("**Data Engineering**", "Pandas · NumPy · spaCy  \nTableau · Power BI · Streamlit  \nSQL · Docker · Git"),
            ("**MLOps / Infra**", "MLflow · NVIDIA Triton  \nONNX · MinIO · Docker  \nNGSI-LD · MQTT · HTTP"),
        ],
        "personal_head": "## 💡 개인 프로젝트",
        "personal_projects": [
            {
                "title": "🧑‍💻 JisangFolio",
                "desc": "지금 보고 계신 이 포트폴리오입니다. 이력서 전문(~3K 토큰)을 시스템 프롬프트에 직접 주입해 RAG 없이 1인칭 AI 챗봇을 구현했습니다. Qwen3 thinking 모드를 `/no_think` + 스트리밍 필터로 제어합니다.",
                "tags": "`Groq · Qwen3 32B` `Streamlit` `Python` `스트리밍 필터`",
                "link": "https://jisangfolio.streamlit.app",
            },
            {
                "title": "📂 JisangData",
                "desc": "LLM 라우터가 질문 유형을 판별해 집계·통계 질문은 pandas 코드를 생성·샌드박스 실행하고, 검색·요약 질문은 FAISS RAG로 처리합니다. 코드 실행 실패 시 RAG 자동 폴백.",
                "tags": "`LangChain` `FAISS` `HuggingFace` `Pandas 코드 생성` `Streamlit`",
                "link": "page:데이터분석",
            },
            {
                "title": "🔌 JisangFolio MCP Server",
                "desc": "Claude Desktop에서 제 포트폴리오를 직접 조회하는 MCP 서버입니다. FastMCP로 프로필·경력·프로젝트·기술·논문 조회 툴과 1인칭 Q&A(`ask_jisang`) 툴을 구현했습니다.",
                "tags": "`fastmcp` `MCP` `Claude Desktop` `Groq`",
                "link": "",
            },
        ],
        "cta_head": "## 💬 직접 물어보세요",
        "cta_body": "AI와 대화하듯 저의 경험, 기술, 프로젝트를 질문해 보세요.",
        "cta_btn": "대화 시작하기 →",
        "data_btn": "📂 데이터 분석 해보기",
    },
    "English": {
        "title": "Jisang Park (박지상)",
        "subtitle": "Data Engineer · AI Researcher",
        "location": "📍 KETI AX Research Division &nbsp;|&nbsp; 🎓 UIUC Information Science + Data Science",
        "tagline_head": "## 📖 A Resume You Talk To",
        "tagline_body": (
            "Going beyond static PDF resumes — my AI delivers my experience and skills in real conversation.  \n"
            "Ask anything you'd want to know in an interview, and get an answer instantly."
        ),
        "how_head": "## ⚙️ This Portfolio Is a Project",
        "how_intro": "Not just an introduction page — three independent AI pipelines running live.",
        "arch_tab1": "💬 Chat Pipeline",
        "arch_tab2": "📂 Data Analysis Pipeline",
        "arch_tab3": "🔌 MCP Server Pipeline",
        "arch": [
            "📄 **Master Resume**\n\nFull resume text injected via Streamlit Secrets\n_(~3K tokens · RAG not needed)_",
            "✨ **Groq · Qwen3 32B**\n\nFull resume in system prompt\n`/no_think` · `<think>` streaming filter",
            "💬 **1st-person Streaming**\n\nMulti-turn conversation history\nAnswers as Jisang in real-time",
        ],
        "arch_data": [
            "📤 **File Upload**\n\nCSV/Excel → DataFrame\nchunk_size=1000 split + FAISS embedding",
            "🔀 **LLM Router**\n\nAuto-classifies question type\n`PANDAS` or `RAG`",
            "⚙️ **PANDAS Path**\n\nCode gen → sandboxed exec\nAuto-fallback to RAG on error",
            "🔍 **RAG Path**\n\nFAISS + HuggingFace embeddings\nMulti-turn context in answer",
        ],
        "arch_mcp": [
            "🤖 **MCP Client**\n\nClaude Desktop · Cursor · Cline\nConnects via stdio",
            "🔌 **fastmcp Server**\n\nProfile·Experience·Projects·Skills·Publications\n6 tools exposed",
            "✨ **Dynamic Q&A**\n\n`ask_jisang` → Groq · Qwen3 32B\nFirst-person real-time answers",
        ],
        "rag_note": "",
        "timeline_head": "## 📅 Career Timeline",
        "proj_head": "## 🛠️ Key Projects",
        "projects": [
            {
                "title": "🔬 KETI AX Research Division · AI Agent Research",
                "period": "Feb 2026 ~ Present · AI Researcher",
                "desc": "MLOps serving infrastructure for urban cooling AI (primary): PKNU-provided PyTorch 3D U-Net → ONNX → Triton GPU serving in production (~200ms inference vs. tens of minutes for CFD). MLflow Tracking·Registry for v1↔v2 comparison — MAE 0.53→0.26°C, R² 0.82→0.95 (MAE 51%↓). Architecture design & tooling selection for a self-hosted stack (MLflow·MinIO·Gitea·Triton). (Separately) Songsan Green City digital twin — production integration & validation of 3 parts.",
                "tags": "`PyTorch` `Triton` `ONNX` `MLflow` `MinIO` `NGSI-LD` `Docker`",
            },
            {
                "title": "🏭 Samsung SDI Air-Gapped RAG",
                "period": "Jun ~ Aug 2025 · Intern",
                "desc": "**Solo-built** patent search RAG chatbot in a fully internet-blocked environment. Designed re-search logic using conversation history and provided key metric aggregation & visualization → executive PoC praised",
                "tags": "`Ollama` `LangChain` `FAISS` `Docker` `Streamlit`",
            },
            {
                "title": "📊 TEBO Balance Analysis · SCIE Paper",
                "period": "Applied Sciences, Jul 2025",
                "desc": "Applied Butterworth Filter(4th order) + FFT on CoP time-series, decomposed Rambling/Trembling achieving **85%+ explanatory power**",
                "tags": "`Python` `SciPy` `FFT` `Time-series Analysis`",
            },
        ],
        "stack_head": "## 🧰 Tech Stack",
        "stacks": [
            ("**AI / LLM**", "LangChain · RAG · FAISS  \nOllama · Groq · PyTorch  \nRule-based Agent · Prompt Engineering"),
            ("**Data Engineering**", "Pandas · NumPy · spaCy  \nTableau · Power BI · Streamlit  \nSQL · Docker · Git"),
            ("**MLOps / Infra**", "MLflow · NVIDIA Triton  \nONNX · MinIO · Docker  \nNGSI-LD · MQTT · HTTP"),
        ],
        "personal_head": "## 💡 Personal Projects",
        "personal_projects": [
            {
                "title": "🧑‍💻 JisangFolio",
                "desc": "This portfolio itself. Full resume (~3K tokens) injected into the system prompt — no RAG needed. Qwen3 thinking mode controlled via `/no_think` + streaming filter.",
                "tags": "`Groq · Qwen3 32B` `Streamlit` `Python` `Streaming Filter`",
                "link": "https://jisangfolio.streamlit.app",
            },
            {
                "title": "📂 JisangData",
                "desc": "An LLM router classifies each question: aggregation/stats queries generate and sandbox-execute pandas code; search/summary queries use FAISS RAG. Auto-fallback to RAG on code error.",
                "tags": "`LangChain` `FAISS` `HuggingFace` `Pandas Code Gen` `Streamlit`",
                "link": "page:데이터분석",
            },
            {
                "title": "🔌 JisangFolio MCP Server",
                "desc": "An MCP server that lets Claude Desktop query my portfolio directly. Built with FastMCP — tools for profile/experience/projects/skills/publications plus a first-person Q&A tool (`ask_jisang`).",
                "tags": "`fastmcp` `MCP` `Claude Desktop` `Groq`",
                "link": "",
            },
        ],
        "cta_head": "## 💬 Ask Me Anything",
        "cta_body": "Chat with my AI to explore my experience, skills, and projects — just like an interview.",
        "cta_btn": "Start Chatting →",
        "data_btn": "📂 Try Data Analysis",
    },
}

t = T[lang]

# ── 타임라인 데이터 (공통) ─────────────────────────────────────────
COLOR_MAP = {
    "학력" if lang == "한국어" else "Education": "#4C9BE8",
    "군복무" if lang == "한국어" else "Military": "#A0A0A0",
    "경력" if lang == "한국어" else "Work": "#2ECC71",
    "논문" if lang == "한국어" else "Research": "#F39C12",
    "활동" if lang == "한국어" else "Activity": "#9B59B6",
}

if lang == "한국어":
    timeline_rows = [
        {"구분": "학력",  "항목": "University of Washington",      "시작": "2019-09-01", "종료": "2020-06-30", "상세": "Pre-Science (INFO · CSE · STAT)"},
        {"구분": "학력",  "항목": "University of Washington",      "시작": "2022-12-01", "종료": "2024-06-30", "상세": "Pre-Science (INFO · CSE · STAT) · 복학"},
        {"구분": "군복무", "항목": "어학병 (제3함대 · 한미연합사)", "시작": "2021-02-15", "종료": "2022-10-14", "상세": "영어 통역 병과"},
        {"구분": "학력",  "항목": "UIUC · BSIS+DS",               "시작": "2024-06-01", "종료": "2025-12-20", "상세": "Information Science + Data Science, GPA 3.89/4.0"},
        {"구분": "경력",  "항목": "삼성SDI · 데이터 엔지니어 인턴", "시작": "2025-06-01", "종료": "2025-08-31", "상세": "폐쇄망 RAG 챗봇 1인 개발 → 임원 PoC 호평"},
        {"구분": "논문",  "항목": "TEBO · SCIE 논문 게재",          "시작": "2025-01-01", "종료": "2025-07-31", "상세": "Applied Sciences, CoP 분석 설명력 85%+"},
        {"구분": "활동",  "항목": "KSA 웹팀 (UIUC)",               "시작": "2024-08-01", "종료": "2025-06-30", "상세": "한인 학생회 웹사이트 사용성 및 성능 개선"},
        {"구분": "경력",  "항목": "KETI · AI 에이전트 연구원",      "시작": "2026-02-01", "종료": "2026-12-31", "상세": "디지털 트윈 · MLOps · LLM 자율 제어 · NGSI-LD IoT"},
    ]
    col_구분, col_항목, col_시작, col_종료, col_상세 = "구분", "항목", "시작", "종료", "상세"
else:
    timeline_rows = [
        {"구분": "Education", "항목": "University of Washington",        "시작": "2019-09-01", "종료": "2020-06-30", "상세": "Pre-Science (INFO · CSE · STAT)"},
        {"구분": "Education", "항목": "University of Washington",        "시작": "2022-12-01", "종료": "2024-06-30", "상세": "Pre-Science (INFO · CSE · STAT) · Return"},
        {"구분": "Military",  "항목": "Military Service (ROKN)",         "시작": "2021-02-15", "종료": "2022-10-14", "상세": "English Interpreter · 3rd Fleet & USFK"},
        {"구분": "Education", "항목": "UIUC · BSIS+DS",                  "시작": "2024-06-01", "종료": "2025-12-20", "상세": "Information Science + Data Science, GPA 3.89/4.0"},
        {"구분": "Work",      "항목": "Samsung SDI · Data Eng. Intern",  "시작": "2025-06-01", "종료": "2025-08-31", "상세": "Solo-built air-gapped RAG chatbot → praised by executives"},
        {"구분": "Research",  "항목": "TEBO · SCIE Publication",         "시작": "2025-01-01", "종료": "2025-07-31", "상세": "Applied Sciences, CoP analysis 85%+ explanatory power"},
        {"구분": "Activity",  "항목": "KSA Web Team (UIUC)",              "시작": "2024-08-01", "종료": "2025-06-30", "상세": "Improved usability and performance of Korean Student Association website"},
        {"구분": "Work",      "항목": "KETI · AI Agent Researcher",      "시작": "2026-02-01", "종료": "2026-12-31", "상세": "Digital Twin · MLOps · LLM Autonomous Control · NGSI-LD IoT"},
    ]
    col_구분, col_항목, col_시작, col_종료, col_상세 = "구분", "항목", "시작", "종료", "상세"

df = pd.DataFrame(timeline_rows)
df[col_시작] = pd.to_datetime(df[col_시작])
df[col_종료] = pd.to_datetime(df[col_종료])

# ── 헤더 ──────────────────────────────────────────────────────────
st.title(t["title"])
st.caption(t["subtitle"])
st.markdown(t["location"], unsafe_allow_html=True)

st.divider()

# ── 경력 타임라인 ─────────────────────────────────────────────────
st.markdown(t["timeline_head"])

fig = px.timeline(
    df,
    x_start=col_시작,
    x_end=col_종료,
    y=col_항목,
    color=col_구분,
    color_discrete_map=COLOR_MAP,
    hover_name=col_항목,
    hover_data={col_상세: True, col_시작: "|%Y.%m", col_종료: "|%Y.%m", col_구분: False, col_항목: False},
    labels={col_항목: "", col_구분: ""},
)
fig.update_yaxes(autorange="reversed")
fig.update_layout(
    height=320,
    margin=dict(l=0, r=10, t=10, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis_title="",
    yaxis_title="",
    font=dict(size=12),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
)
fig.update_traces(marker_line_width=0)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 주요 프로젝트 ─────────────────────────────────────────────────
st.markdown(t["proj_head"])
# Row 1: KETI (full width)
with st.container(border=True):
    st.markdown(f"**{t['projects'][0]['title']}**")
    st.caption(t["projects"][0]["period"])
    st.markdown(t["projects"][0]["desc"])
    st.caption(t["projects"][0]["tags"])
    grafana_path = os.path.join(os.path.dirname(__file__), "mlops_grafana.png")
    if os.path.exists(grafana_path):
        st.image(
            grafana_path,
            caption="Prometheus + Grafana 모니터링 대시보드 (Triton 실시간 메트릭)" if lang == "한국어" else "Prometheus + Grafana Monitoring Dashboard (Triton live metrics)",
            use_container_width=True,
        )
# Row 2: Samsung SDI + TEBO (side by side)
row2 = st.columns(2)
for col, proj in zip(row2, t["projects"][1:]):
    with col:
        with st.container(border=True):
            st.markdown(f"**{proj['title']}**")
            st.caption(proj["period"])
            st.markdown(proj["desc"])
            st.caption(proj["tags"])

st.divider()

# ── 기술 스택 ─────────────────────────────────────────────────────
st.markdown(t["stack_head"])
cols = st.columns(3)
for col, (header, body) in zip(cols, t["stacks"]):
    with col:
        st.markdown(header)
        st.markdown(body)

st.divider()

# ── 태그라인 ──────────────────────────────────────────────────────
st.markdown(t["tagline_head"])
st.markdown(t["tagline_body"])

st.divider()

# ── 작동 원리 ─────────────────────────────────────────────────────
st.markdown(t["how_head"])
st.caption(t["how_intro"])
tab1, tab2, tab3 = st.tabs([t["arch_tab1"], t["arch_tab2"], t["arch_tab3"]])
with tab1:
    col1, col2, col3, col4, col5 = st.columns([3, 1, 3, 1, 3])
    with col1:
        st.info(t["arch"][0])
    with col2:
        st.markdown("<div style='font-size:2rem; text-align:center; padding-top:0.6rem;'>→</div>", unsafe_allow_html=True)
    with col3:
        st.info(t["arch"][1])
    with col4:
        st.markdown("<div style='font-size:2rem; text-align:center; padding-top:0.6rem;'>→</div>", unsafe_allow_html=True)
    with col5:
        st.info(t["arch"][2])
with tab2:
    d1, d2, d3, d4, d5, d6, d7 = st.columns([3, 1, 3, 1, 3, 1, 3])
    for box, content in zip([d1, d3, d5, d7], t["arch_data"]):
        box.info(content)
    for arrow in [d2, d4, d6]:
        arrow.markdown("<div style='font-size:2rem; text-align:center; padding-top:0.6rem;'>→</div>", unsafe_allow_html=True)
with tab3:
    m1, m2, m3, m4, m5 = st.columns([3, 1, 3, 1, 3])
    for box, content in zip([m1, m3, m5], t["arch_mcp"]):
        box.info(content)
    for arrow in [m2, m4]:
        arrow.markdown("<div style='font-size:2rem; text-align:center; padding-top:0.6rem;'>→</div>", unsafe_allow_html=True)

st.divider()

# ── 개인 프로젝트 ─────────────────────────────────────────────────
st.markdown(t["personal_head"])
cols = st.columns(len(t["personal_projects"]))
for col, proj in zip(cols, t["personal_projects"]):
    with col:
        with st.container(border=True):
            if proj["link"] and proj["link"].startswith("page:"):
                st.markdown(f"**{proj['title']}**")
            elif proj["link"]:
                st.markdown(f"**[{proj['title']}]({proj['link']})**")
            else:
                st.markdown(f"**{proj['title']}**")
            st.markdown(proj["desc"])
            st.caption(proj["tags"])
            if proj["link"] and proj["link"].startswith("page:"):
                if st.button("사용해 보기 →" if lang == "한국어" else "Try it →", key=proj["title"], use_container_width=True):
                    st.switch_page("pages/2_데이터분석.py")

st.divider()

# ── CTA ───────────────────────────────────────────────────────────
st.markdown(t["cta_head"])
st.markdown(t["cta_body"])
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    if st.button(t["cta_btn"], type="primary", use_container_width=True):
        st.switch_page("pages/1_대화하기.py")
with btn_col2:
    if st.button(t["data_btn"], use_container_width=True):
        st.switch_page("pages/2_데이터분석.py")
