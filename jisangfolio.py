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
        "location": "📍 KETI 자율형IoT연구센터 &nbsp;|&nbsp; 🎓 UIUC Information Science + Data Science",
        "tagline_head": "## 📖 읽지 말고 대화하는 이력서",
        "tagline_body": (
            "정적인 PDF 이력서의 한계를 넘어, 저의 모든 경험과 역량을 AI가 직접 전달합니다.  \n"
            "채용 담당자가 궁금한 것을 바로 물어볼 수 있는 인터랙티브 포트폴리오입니다."
        ),
        "how_head": "## ⚙️ 어떻게 작동하나요?",
        "arch": [
            "📄 **마스터 이력서**\n\nStreamlit Secrets에 주입된 전체 이력서 텍스트",
            "✨ **Groq · Qwen3 32B**\n\n이력서 전문을 시스템 프롬프트에 주입, 빠른 스트리밍 답변",
            "💬 **1인칭 스트리밍**\n\n박지상 본인처럼 면접 질문에 실시간으로 답변",
        ],
        "rag_note": "",
        "timeline_head": "## 📅 경력 타임라인",
        "proj_head": "## 🛠️ 주요 프로젝트",
        "projects": [
            {
                "title": "🏭 삼성SDI 폐쇄망 RAG",
                "period": "2025.06 ~ 08 · 인턴",
                "desc": "완전 인터넷 차단 환경에서 특허 검색 RAG 챗봇 **1인 단독 개발**. 대화 이력 기반 재검색 로직 설계, 핵심 지표 집계·시각화 기능 포함 → 임원 PoC 호평",
                "tags": "`Ollama` `LangChain` `FAISS` `Docker` `Streamlit`",
            },
            {
                "title": "🔬 KETI 자율형 AI 에이전트 연구",
                "period": "2026.02 ~ 현재 · AI 연구원",
                "desc": "LLM 결합형 디지털 트윈 인프라 구축: NGSI-LD 기반 실시간 데이터 적재·조회, MQTT/HTTP 하이브리드 통신 설계, Ports & Adapters 아키텍처로 자율 상황 판단 에이전트 PoC 수행. 도시냉각 AI 모델(3D U-Net)을 ONNX 변환 후 Triton 서빙 배포까지 완료",
                "tags": "`PyTorch` `Triton` `ONNX` `NGSI-LD` `MQTT` `Docker`",
            },
            {
                "title": "📊 TEBO 균형 분석 · SCIE 논문",
                "period": "Applied Sciences, 2025.07 게재",
                "desc": "CoP 시계열에 Butterworth Filter(4차) + FFT 적용, Rambling/Trembling 분해로 데이터 설명력 **85%+ 달성**",
                "tags": "`Python` `SciPy` `FFT` `시계열 분석`",
            },
            {
                "title": "🧠 감성 분석 · 멀티모달 AI",
                "period": "2024.08 ~ 12 · UIUC 프로젝트",
                "desc": "Hugging Face + PyTorch로 감성 분석 및 멀티모달 모델 성능 개선. Pandas + Matplotlib으로 데이터 전처리 및 시각화 자동화, Computer Vision 툴 배포",
                "tags": "`PyTorch` `Hugging Face` `Pandas` `Matplotlib`",
            },
        ],
        "stack_head": "## 🧰 기술 스택",
        "stacks": [
            ("**AI / LLM**", "LangChain · RAG · FAISS  \nOllama · Groq · PyTorch  \nRule-based Agent · Prompt Engineering"),
            ("**Data Engineering**", "Pandas · NumPy · spaCy  \nTableau · Power BI · Streamlit  \nSQL · Docker · Git"),
            ("**MLOps / Infra**", "Kubeflow · MLflow  \nNVIDIA Triton Inference Server  \nNGSI-LD · MQTT · HTTP"),
        ],
        "personal_head": "## 💡 개인 프로젝트",
        "personal_projects": [
            {
                "title": "🧑‍💻 JisangFolio",
                "desc": "지금 보고 계신 이 포트폴리오입니다. 이력서 전문을 시스템 프롬프트에 직접 주입해 RAG 없이 1인칭 AI 면접 챗봇을 구현했습니다.",
                "tags": "`Groq · Qwen3 32B` `Streamlit` `Python`",
                "link": "https://jisangfolio.streamlit.app",
            },
            {
                "title": "📂 JisangData (AnyData)",
                "desc": "CSV/Excel 파일을 업로드하면 RAG 기반으로 데이터에 대해 질문할 수 있는 챗봇입니다. HuggingFace Embeddings + FAISS + LangChain으로 구성, Rate Limit 대응 배치 처리를 적용했습니다.",
                "tags": "`LangChain` `FAISS` `HuggingFace` `Streamlit`",
                "link": None,
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
        "location": "📍 KETI IoT Research Center &nbsp;|&nbsp; 🎓 UIUC Information Science + Data Science",
        "tagline_head": "## 📖 A Resume You Talk To",
        "tagline_body": (
            "Going beyond static PDF resumes — my AI delivers my experience and skills in real conversation.  \n"
            "Ask anything you'd want to know in an interview, and get an answer instantly."
        ),
        "how_head": "## ⚙️ How Does It Work?",
        "arch": [
            "📄 **Master Resume**\n\nFull resume text injected via Streamlit Secrets",
            "✨ **Groq · Qwen3 32B**\n\nFull resume injected into system prompt, fast streaming responses",
            "💬 **1st-person Streaming**\n\nAnswers interview questions in real-time as Jisang himself",
        ],
        "rag_note": "",
        "timeline_head": "## 📅 Career Timeline",
        "proj_head": "## 🛠️ Key Projects",
        "projects": [
            {
                "title": "🏭 Samsung SDI Air-Gapped RAG",
                "period": "Jun ~ Aug 2025 · Intern",
                "desc": "**Solo-built** patent search RAG chatbot in a fully internet-blocked environment. Designed re-search logic using conversation history and provided key metric aggregation & visualization → executive PoC praised",
                "tags": "`Ollama` `LangChain` `FAISS` `Docker` `Streamlit`",
            },
            {
                "title": "🔬 KETI Autonomous AI Agent Research",
                "period": "Feb 2026 ~ Present · AI Researcher",
                "desc": "Building LLM-integrated digital twin infrastructure: real-time NGSI-LD data ingestion/query, MQTT/HTTP hybrid communication, Ports & Adapters architecture for autonomous situation-assessment agent PoC. Deployed urban cooling AI model (3D U-Net) via ONNX conversion + Triton serving",
                "tags": "`PyTorch` `Triton` `ONNX` `NGSI-LD` `MQTT` `Docker`",
            },
            {
                "title": "📊 TEBO Balance Analysis · SCIE Paper",
                "period": "Applied Sciences, Jul 2025",
                "desc": "Applied Butterworth Filter(4th order) + FFT on CoP time-series, decomposed Rambling/Trembling achieving **85%+ explanatory power**",
                "tags": "`Python` `SciPy` `FFT` `Time-series Analysis`",
            },
            {
                "title": "🧠 Sentiment Analysis · Multimodal AI",
                "period": "Aug ~ Dec 2024 · UIUC Project",
                "desc": "Improved sentiment analysis and multimodal model performance using Hugging Face + PyTorch. Automated data preprocessing & visualization with Pandas + Matplotlib, deployed Computer Vision tools",
                "tags": "`PyTorch` `Hugging Face` `Pandas` `Matplotlib`",
            },
        ],
        "stack_head": "## 🧰 Tech Stack",
        "stacks": [
            ("**AI / LLM**", "LangChain · RAG · FAISS  \nOllama · Groq · PyTorch  \nRule-based Agent · Prompt Engineering"),
            ("**Data Engineering**", "Pandas · NumPy · spaCy  \nTableau · Power BI · Streamlit  \nSQL · Docker · Git"),
            ("**MLOps / Infra**", "Kubeflow · MLflow  \nNVIDIA Triton Inference Server  \nNGSI-LD · MQTT · HTTP"),
        ],
        "personal_head": "## 💡 Personal Projects",
        "personal_projects": [
            {
                "title": "🧑‍💻 JisangFolio",
                "desc": "This portfolio itself. Injects the full resume into the system prompt without RAG, enabling a 1st-person AI interview chatbot.",
                "tags": "`Groq · Qwen3 32B` `Streamlit` `Python`",
                "link": "https://jisangfolio.streamlit.app",
            },
            {
                "title": "📂 JisangData (AnyData)",
                "desc": "Upload a CSV/Excel file and chat with your data using RAG. Built with HuggingFace Embeddings + FAISS + LangChain, with batch processing to handle rate limits.",
                "tags": "`LangChain` `FAISS` `HuggingFace` `Streamlit`",
                "link": None,
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
        {"구분": "경력",  "항목": "KETI · AI 에이전트 연구원",      "시작": "2026-02-01", "종료": "2026-12-31", "상세": "멀티모달 AI 에이전트 · MLOps · NGSI-LD IoT"},
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
        {"구분": "Work",      "항목": "KETI · AI Agent Researcher",      "시작": "2026-02-01", "종료": "2026-12-31", "상세": "Multimodal AI Agent · MLOps · NGSI-LD IoT"},
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

# ── 태그라인 ──────────────────────────────────────────────────────
st.markdown(t["tagline_head"])
st.markdown(t["tagline_body"])

st.divider()

# ── 작동 원리 ─────────────────────────────────────────────────────
st.markdown(t["how_head"])
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
st.markdown(t["rag_note"])

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
row1 = st.columns(2)
row2 = st.columns(2)
for col, proj in zip(row1 + row2, t["projects"]):
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

# ── 개인 프로젝트 ─────────────────────────────────────────────────
st.markdown(t["personal_head"])
cols = st.columns(2)
for col, proj in zip(cols, t["personal_projects"]):
    with col:
        with st.container(border=True):
            if proj["link"]:
                st.markdown(f"**[{proj['title']}]({proj['link']})**")
            else:
                st.markdown(f"**{proj['title']}**")
            st.markdown(proj["desc"])
            st.caption(proj["tags"])

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
