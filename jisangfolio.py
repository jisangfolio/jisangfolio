import base64 as _b64m
import streamlit as st
import plotly.express as px
import pandas as pd
import streamlit.components.v1 as components
import os
from ui import apply_style
import profile_graph

st.set_page_config(
    page_title="JisangFolio",
    page_icon="🧑‍💻",
    layout="centered"
)
apply_style()

# OG 메타태그를 st.markdown 으로 주입하던 코드가 여기 있었다 — 제거했다.
#
# 왜 죽은 코드였나: st.markdown 은 브라우저에서 JS 로 <body> 안에 렌더된다. 링크
# 미리보기는 <head> 를 읽으므로 그 태그들은 순위에 낄 수조차 없었다.
# 왜 그래도 미리보기가 뜨나: Streamlit Community Cloud 가 크롤러 UA 에 프리렌더된
# HTML 을 주고, 그 <head> 에 자기 OG 태그(제목·설명·스크린샷 og:image)를 이미 넣는다.
# 즉 링크는 지금도 카드로 펼쳐지며, 그 값은 st.set_page_config 와 Cloud 설정에서 온다.
#
# 여기서 태그를 다시 넣어봐야 body 에 두 번째로 앉을 뿐 아무것도 바뀌지 않는다.
# 제목·설명을 정말 바꾸려면 Cloud 앱 설정이나 커스텀 도메인 앞단(리버스 프록시)이
# 필요하다 — 코드 한 줄로 되는 일이 아니라서, 착각을 남기지 않으려고 지운다.

# --- 사이드바: 언어 선택 + 링크 ---
with st.sidebar:
    lang = st.radio("Language / 언어", ["English", "한국어"], horizontal=True)
    st.divider()
    st.markdown("**박지상 (Jisang Park)**")
    st.markdown("✉️ jjpark324434@gmail.com")
    st.markdown("🔗 [LinkedIn](https://linkedin.com/in/jisangpark)")
    st.markdown("💻 [GitHub](https://github.com/jisangfolio)")
    st.divider()

    resume_path = os.path.join(os.path.dirname(__file__), "assets", "resume.pdf")
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
        st.caption("(assets/resume.pdf를 넣으면 다운로드 버튼이 활성화됩니다)" if lang == "한국어" else "(Add assets/resume.pdf to enable the download button.)")
    st.divider()
    st.caption("이 챗봇은 제(박지상) 이력서로 답하는 AI라 가끔 헷갈릴 수 있습니다. 정확한 건 이력서 PDF나 메일로 직접 확인 바랍니다 :)" if lang == "한국어" else "This chatbot answers from my (Jisang's) resume, so it can occasionally get things wrong. For anything important, check the resume PDF or just email me :)")

# ── 언어별 텍스트 ────────────────────────────────────────────────
T = {
    "한국어": {
        "title": "박지상 (Jisang Park)",
        "subtitle": "Data Engineer · AI Researcher",
        "location": "📍 연합인포맥스 금융공학연구소<br>🎓 UIUC Information Science + Data Science",
        "tagline_head": "## 대화하는 이력서",
        "hero_tagline": "읽지 말고, 물어보세요. 저에 대해 무엇이든 제 AI에게 직접 질문할 수 있습니다.",
        "edu_head": "## 학력",
        "edu_body": "**University of Illinois Urbana-Champaign (UIUC)** — Information Science + Data Science 학사 · GPA 3.89/4.0 · 2025.12  \n**University of Washington, Seattle** — Pre-Science · Dean's List\n\n**주요 이수 과목** (강의 프로젝트 수준): CS307 Models of Learning · IS327 Machine Learning (RF 회귀) · IS477 Data Curation (ETL) · IS467 Data Ethics · CSE160 (k-means 직접구현) · INFO330 Database (T-SQL) · STAT207 · MATH227",
        "how_head": "## 파이프라인",
        "how_intro": "챗봇·데이터분석·MCP 서버·MLOps 문서 Agentic RAG가 각각 별도의 파이프라인으로 돌아갑니다. 왜 이렇게 나눴는지는 아래 탭에서 볼 수 있습니다.",
        "graph_head": "## 코드베이스 구조 그래프",
        "graph_bullets": (
            "- **단일 소스(SSOT):** 프롬프트·후처리(`prompts.py`)를 앱 페이지와 평가 하니스가 공유합니다 — 그래프에서 `build_system_prompt`이 여러 파이프라인을 잇는 허브로 나타납니다.  \n"
            "- **회귀 평가 하니스:** 결정적 채점(사실 키워드·금지어) + LLM-judge로 챗봇 답변의 사실성을 릴리스마다 검증합니다."
        ),
        "graph_caption": "노드를 클릭하면 이웃 관계를 탐색할 수 있습니다. (vis-network 인터랙티브 · 이 사이트 코드의 실제 콜그래프)",
        "graph_missing": "(assets/codegraph.html을 넣으면 코드 지식그래프가 표시됩니다)",
        "arch_tab1": "채팅 파이프라인",
        "arch_tab2": "데이터 분석 파이프라인",
        "arch_tab3": "MCP 서버 파이프라인",
        "arch": [
            "**Guardrail + GraphRAG**\n\n입력 가드(인젝션·스코프) 통과 후\n프로필 그래프에서 관련 서브그래프 탐색·주입",
            "**Groq · Qwen3 27B**\n\n이력서 + 서브그래프 주입\n추론 OFF로 저지연",
            "**1인칭 스트리밍 + 트레이스**\n\n실시간 답변 + 지연·라우팅을\n옵저버빌리티에 기록",
        ],
        "arch_data": [
            "**파일 업로드**\n\nCSV/Excel → DataFrame\nchunk_size=1000 분할 + FAISS 임베딩",
            "**LLM 라우터**\n\n질문 유형 자동 판별\n`PANDAS` or `RAG` 2분기",
            "**PANDAS 경로**\n\n코드 생성 → 축소 권한 네임스페이스에서 실행\n실패 시 RAG 자동 폴백",
            "**RAG 경로**\n\n하이브리드: FAISS(dense) + BM25(sparse)\nReciprocal Rank Fusion으로 융합",
        ],
        "arch_mcp": [
            "**MCP 클라이언트**\n\nClaude Desktop · Cursor · Cline\nstdio로 서버 연결",
            "**fastmcp 서버**\n\n프로필·경력·프로젝트·기술·논문\n6개 툴 노출",
            "**동적 Q&A**\n\n`ask_jisang` → Groq · Qwen3 27B\n1인칭 실시간 답변",
        ],
        "arch_tab4": "Agentic RAG 파이프라인",
        "arch_agentic": [
            "**하이브리드 검색**\n\nFAISS(dense) + BM25(sparse)\nRRF로 융합",
            "**관련성 평가 + 재작성**\n\n부실하면 쿼리 재작성 후\n재검색 (자기교정 루프)",
            "**근거 인용 생성**\n\n검색된 청크만 근거로 [n] 인용\n코퍼스 밖이면 거절",
            "**근거 자기점검**\n\n답이 컨텍스트로 뒷받침되나\nfaithfulness 확인",
        ],
        "rag_note": "",
        "timeline_head": "## 경력 타임라인",
        "proj_head": "## 주요 프로젝트",
        "projects": [
            {
                "title": "KETI AX연구본부 — 온프레미스 MLOps 플랫폼",
                "period": "2026.02 ~ 2026.09 · 위촉연구원",
                "desc": "온프레미스 자체호스팅(폐쇄망 대응 설계) MLOps 플랫폼을 주도적으로 설계·구축했습니다. 부경대 제공 PyTorch 3D U-Net을 ONNX로 변환해 Triton GPU에 서빙하고, 입출력이 다른 외부 PINN 3종까지 같은 Triton에 통합했습니다(좌표 100개 지점 단일 요청 22–32ms, L40S). MLflow(실험·레지스트리·거버넌스)·Gitea Actions·Prometheus+Grafana(7패널)를 docker-compose로 묶고, 8~9월엔 주간 학습 → 매니페스트 기준 판정 → ONNX 변환 → 체크섬 대조 배포를 워크플로 8개로 이어 사람 개입 없이 한 바퀴 도는 것을 확인했습니다(2026-09-12, Google MLOps Level 1). 판정이 미달 버전 2건을 실제로 막았고, 판정 호출·서빙 자동 복구·정합성 대조는 운영 콘솔이 맡습니다. 나뉘어 있던 학습 데이터를 통합해 재학습한 뒤 버전 간 지표를 MLflow 비교 체계에서 대조했고, 그 판정이 승격 여부를 갈랐습니다(지표 수치는 과제 산출물이라 공개하지 않습니다). (한계) 학습 데이터 갱신 경로가 없어 재학습이 모델을 개선하진 않고, CI 동작시험·롤백은 미착수, 추론 트래픽은 아직 스모크 수준입니다. (별도) 송산그린시티 디지털 트윈 3파트 연동·검증.",
                "tags": "`Triton` `ONNX` `MLflow` `Gitea Actions` `Prometheus` `Grafana` `Docker` `PyTorch`",
            },
            {
                "title": "이미지 분류 MLOps 레일 + CCTV PoC",
                "period": "2026.07 · KETI 자발 과제",
                "desc": "계속 남이 만든 모델을 받아 서빙했던 터라, 이번엔 카탈로그부터 학습·품질 게이트·ONNX 내보내기까지 직접 짰습니다. 레일과 태스크 설정을 분리해 같은 코드로 CIFAR-10 → EuroSAT → 실 CCTV 3종을 클래스 수가 10에서 2로 바뀌어도 코드 수정 없이 통과시켰습니다. 게이트는 test 지표가 임계치에 못 미치면 레지스트리 승격을 건너뜁니다. 지표를 판정보다 먼저 기록해두니 차단된 런도 사유가 남습니다. 실데이터는 공개 교통 CCTV OpenAPI 키를 직접 신청해 확보하고 카메라 이름으로 자동 라벨링했습니다. 8월엔 v1의 정확도가 데이터 누수(같은 장면이 train/test에 동시 포함·중복 카메라·이름 기반 오라벨)로 부풀려진 것을 스스로 규명하고, 카메라 그룹 단위로 재분할해 재학습하니 0.548로 떨어져 게이트가 등록을 실제로 막았습니다 — 원인 3건을 고쳐 v2로 재등록했습니다. (한계) 전 구간 PoC입니다. 승격 차단만 구현했고 CI 연동은 미완, CCTV는 227장/카메라 80그룹(test는 미학습 카메라 12대 30장)이라 정확도를 성능 주장으로 쓸 표본이 아닙니다.",
                "tags": "`PyTorch` `MLflow` `ONNX` `scikit-learn` `FastAPI` `Qwen2.5-VL`",
            },
            {
                "title": "삼성SDI 폐쇄망 RAG",
                "period": "2025.06 ~ 08 · 인턴",
                "desc": "완전 인터넷 차단 환경에서 특허 검색 RAG 챗봇 개발 — 검색·분기·UI를 담당(LLM 서빙 구성은 멘토 주도). 대화 이력 기반 재검색 로직 설계, 핵심 지표 집계·시각화 기능 포함 → 임원 PoC 호평",
                "tags": "`Ollama` `LangChain` `FAISS` `Docker` `Streamlit`",
            },
            {
                "title": "TEBO 균형 분석 · SCIE 논문",
                "period": "Applied Sciences, 2025.07 게재",
                "desc": "측정 이후 단계를 맡았습니다. 두 코호트(PCD·TCOA) 결과 데이터를 병합할 때 겹치는 피험자 번호를 새 대역으로 재배정해 분리하고, 낙상 두려움(FES-I)·우울(GDS) 설문을 채점해 집단별로 집계하고, 랩이 전달한 대역별 지표로 stabilogram 그림을 EPS 벡터로 출고했습니다. 논문 CRediT 기여는 formal analysis · data curation · visualization입니다 — 신호 필터링과 성분 분해는 연구팀이 수행했고 제 기여가 아닙니다. 게재는 SCIE \'Applied Sciences\' 공저(10인 중 7저자)입니다.",
                "tags": "`Python` `Pandas` `Matplotlib` `설문 집계`",
            },
        ],
        "stack_head": "## 기술 스택",
        "profilegraph_head": "## 프로필 구조 그래프",
        "profilegraph_caption": "선 위 글자가 두 노드의 관계입니다. 노드에 마우스를 올리거나 클릭하면 그 노드에 걸린 관계만 밝게 강조됩니다. 드래그로 이동, 휠로 확대·축소.",
        "stacks": [
            ("**AI / LLM**", "LangChain · RAG · GraphRAG · Agentic RAG · Hybrid(BM25+dense)  \nOllama · Groq · FAISS · PyTorch  \nLLM eval · Guardrails · MCP · Observability · CI"),
            ("**Data Engineering**", "Pandas · NumPy · Matplotlib  \nTableau · Power BI · Streamlit  \nSQL · Docker · Git"),
            ("**MLOps / Infra**", "MLflow · NVIDIA Triton · ONNX  \nGitea Actions · GitHub Actions · Prometheus · Grafana  \nEvidently(PoC) · Docker Compose"),
        ],
        "personal_head": "## 개인 프로젝트",
        "personal_projects": [
            {
                "title": "JisangFolio",
                "desc": "지금 보고 계신 이 포트폴리오입니다. 이력서 전문(약 3K 토큰)을 시스템 프롬프트에 직접 주입해 무거운 문서 RAG 없이 1인칭 챗봇을 만들었고, 프롬프트·모델을 바꿔도 사실이 깨지지 않는지 검증하는 회귀 평가 하니스(규칙 채점 + 별도 모델 LLM-judge)를 직접 붙였습니다. 이 하니스가 낡은 이력서 사본이 새던 문제를 잡았고, 이후 하니스 자체의 결함도 두 번 잡혔습니다 — 앱과 추론 설정이 달랐던 것, 앱이 실제로 조립하는 프롬프트를 태우지 않던 것. 골든셋은 20건이고 가장 최근 완주는 17/20입니다(n=20이라 벤치마크가 아니라 변경 전후 비교용 신호입니다). 여기에 GraphRAG(그래프 탐색 검색)·가드레일·자체호스팅 LLM 옵저버빌리티·하이브리드 RAG·GitHub Actions CI까지 얹었습니다.",
                "tags": "`Groq · Qwen3 27B` `Streamlit` `eval 하니스` `Python`",
                "link": "https://jisangfolio.streamlit.app",
            },
            {
                "title": "MLOps Docs Assistant",
                "desc": "MLOps 파이프라인 문서(Google·AWS·Azure·Vertex 공식 문서 + 온프레 KETI 파이프라인)를 질의하는 Agentic RAG입니다. 검색→관련성 평가→쿼리 재작성·재검색→근거 인용→근거 자기점검의 자기교정 루프로, 코퍼스 밖 질문은 거절하고 검색·근거 충실성을 골든셋으로 회귀 평가합니다(통과율은 `evals/report.md`에 실행마다 기록).",
                "tags": "`Agentic RAG` `FAISS+BM25` `Self-correction` `Groundedness eval`",
                "link": "page:pages/4_MLOps_Docs.py",
            },
            {
                "title": "JisangData",
                "desc": "LLM 라우터가 질문 유형을 판별해 집계·통계 질문은 pandas 코드를 생성해 **축소 권한 네임스페이스**에서 실행하고(모듈 미노출·dunder 정적 거부·writer allowlist — 샌드박스는 아니다), 검색·요약 질문은 FAISS RAG로 처리합니다. 코드 실행 실패 시 RAG 자동 폴백.",
                "tags": "`LangChain` `FAISS` `HuggingFace` `Pandas 코드 생성` `Streamlit`",
                "link": "page:pages/2_Data_Analysis.py",
            },
            {
                "title": "JisangFolio MCP Server",
                "desc": "Claude Desktop에서 제 포트폴리오를 직접 조회하는 MCP 서버입니다. FastMCP로 프로필·경력·프로젝트·기술·논문 조회 툴과 1인칭 Q&A(`ask_jisang`) 툴을 구현했습니다.",
                "tags": "`fastmcp` `MCP` `Claude Desktop` `Groq`",
                "link": "",
            },
        ],
        "cta_btn": "대화 시작하기 →",
        "data_btn": "📂 데이터 분석 해보기",
    },
    "English": {
        "title": "Jisang Park (박지상)",
        "subtitle": "Data Engineer · AI Researcher",
        "location": "📍 Yonhap Infomax · Financial Engineering Research Institute<br>🎓 UIUC Information Science + Data Science",
        "tagline_head": "## A Resume You Talk To",
        "hero_tagline": "Don't read it — ask it. You can ask my AI anything about me, live.",
        "edu_head": "## Education",
        "edu_body": "**University of Illinois Urbana-Champaign (UIUC)** — B.S., Information Science + Data Science · GPA 3.89/4.0 · Dec 2025  \n**University of Washington, Seattle** — Pre-Science · Dean's List\n\n**Selected coursework** (course projects): CS307 Models of Learning · IS327 Machine Learning (RF regression) · IS477 Data Curation (ETL) · IS467 Data Ethics · CSE160 (k-means from scratch) · INFO330 Database (T-SQL) · STAT207 · MATH227",
        "how_head": "## Pipelines",
        "how_intro": "Four separate pipelines — chat, data analysis, an MCP server, and Agentic RAG over MLOps docs — each doing its own thing. The tabs show why I split them up.",
        "graph_head": "## Codebase structure graph",
        "graph_bullets": (
            "- **Single Source of Truth:** prompts & post-processing (`prompts.py`) are shared by the app pages and the eval harness — in the graph, `build_system_prompt` appears as the hub linking multiple pipelines.  \n"
            "- **Regression eval harness:** deterministic checks (fact keywords · banned terms) + an LLM judge verify the chatbot's factual accuracy on every release."
        ),
        "graph_caption": "Click any node to explore its neighbors. (Interactive vis-network · the real call graph of this site's code)",
        "graph_missing": "(place assets/codegraph.html to display the code knowledge graph)",
        "arch_tab1": "Chat Pipeline",
        "arch_tab2": "Data Analysis Pipeline",
        "arch_tab3": "MCP Server Pipeline",
        "arch": [
            "**Guardrail + GraphRAG**\n\nInput guard (injection·scope), then retrieve\n& inject a relevant profile subgraph",
            "**Groq · Qwen3 27B**\n\nResume + subgraph injected\nreasoning off for low latency",
            "**1st-person Streaming + Trace**\n\nReal-time answer + latency/routing\nlogged to observability",
        ],
        "arch_data": [
            "**File Upload**\n\nCSV/Excel → DataFrame\nchunk_size=1000 split + FAISS embedding",
            "**LLM Router**\n\nAuto-classifies question type\n`PANDAS` or `RAG`",
            "**PANDAS Path**\n\nCode gen → reduced-capability exec\nAuto-fallback to RAG on error",
            "**RAG Path**\n\nHybrid: FAISS (dense) + BM25 (sparse)\nfused with Reciprocal Rank Fusion",
        ],
        "arch_mcp": [
            "**MCP Client**\n\nClaude Desktop · Cursor · Cline\nConnects via stdio",
            "**fastmcp Server**\n\nProfile·Experience·Projects·Skills·Publications\n6 tools exposed",
            "**Dynamic Q&A**\n\n`ask_jisang` → Groq · Qwen3 27B\nFirst-person real-time answers",
        ],
        "arch_tab4": "Agentic RAG Pipeline",
        "arch_agentic": [
            "**Hybrid Retrieval**\n\nFAISS (dense) + BM25 (sparse)\nfused with RRF",
            "**Grade + Rewrite**\n\nIf weak, rewrite the query\n& re-retrieve (self-correction)",
            "**Cited Generation**\n\nAnswer only from retrieved chunks\nwith [n] citations; refuse if out-of-corpus",
            "**Groundedness Self-check**\n\nVerify the answer is supported\nby the context (faithfulness)",
        ],
        "rag_note": "",
        "timeline_head": "## Career Timeline",
        "proj_head": "## Key Projects",
        "projects": [
            {
                "title": "KETI AX Research Division — On-prem MLOps Platform",
                "period": "Feb 2026 ~ Sep 2026 · Research Engineer (Contract)",
                "desc": "Led the design and build of a self-hosted on-premise MLOps platform (built to hold up under closed-network constraints). Converted a PKNU-provided PyTorch 3D U-Net to ONNX and served it on Triton GPU, then unified three external PINN models with different I/O onto the same Triton (a 100-point PINN request in 22–32 ms on an L40S). MLflow (experiments·registry·governance), Gitea Actions, and Prometheus+Grafana (7 panels) run as one docker-compose stack; in Aug–Sep I chained weekly training → manifest-driven gate → ONNX export → checksum-verified deploy across eight workflows and confirmed the first unattended end-to-end run on 2026-09-12 (Google MLOps Level 1). The gate actually rejected two under-performing versions; gate calls, serving auto-recovery and declared-vs-actual reconciliation are handled by a 10-menu operations console. After consolidating training data that had arrived in separate splits, I compared versions through the MLflow setup and let that comparison decide promotion (the project's metric values are not disclosed). (Limits) No path yet for refreshing training data, so retraining does not improve the model; no behavioral tests in CI, no rollback, and inference traffic is still smoke-test level. (Separately) Songsan Green City digital twin — integration & validation of 3 parts.",
                "tags": "`Triton` `ONNX` `MLflow` `Gitea Actions` `Prometheus` `Grafana` `Docker` `PyTorch`",
            },
            {
                "title": "Image-Classification MLOps Rail + CCTV PoC",
                "period": "Jul 2026 · self-initiated at KETI",
                "desc": "I had only ever served models handed to me, so this time I wrote the pipeline myself — catalog, training, quality gate, ONNX export. Separating the rail from task config let the same code carry CIFAR-10 → EuroSAT → live traffic CCTV with no code edits, even as the class count went from 10 to 2. The gate skips registry promotion when the test metric falls below a configured threshold, and because metrics are logged *before* the decision, a blocked run still records why. For real data I applied for a public traffic-CCTV OpenAPI key myself and auto-labelled by camera name. In August I established that v1's accuracy was inflated by data leakage (same scene in train and test, duplicate cameras, name-based mislabels), re-split by camera group and retrained — accuracy fell to 0.548 and the gate actually blocked registration; I fixed the three causes and re-registered v2. (Limits) All of it is proof-of-concept: promotion blocking only, not wired into CI, and the CCTV set is 227 images / 80 camera groups (test = 30 images from 12 unseen cameras) — too small to claim accuracy as performance.",
                "tags": "`PyTorch` `MLflow` `ONNX` `scikit-learn` `FastAPI` `Qwen2.5-VL`",
            },
            {
                "title": "Samsung SDI Air-Gapped RAG",
                "period": "Jun ~ Aug 2025 · Intern",
                "desc": "Patent-search RAG chatbot in a fully internet-blocked environment — I owned retrieval, query routing and the UI (LLM serving was set up by my mentor). Designed re-search logic using conversation history and provided key metric aggregation & visualization → executive PoC praised",
                "tags": "`Ollama` `LangChain` `FAISS` `Docker` `Streamlit`",
            },
            {
                "title": "TEBO Balance Analysis · SCIE Paper",
                "period": "Applied Sciences, Jul 2025",
                "desc": "My work began after data collection. Merging the two cohorts (PCD·TCOA) meant overlapping subject IDs, so I reassigned them into a separate range; I scored the fear-of-falling (FES-I) and depression (GDS) surveys and aggregated them by group; and I produced the stabilogram figures as vector EPS from the band-power metrics the lab supplied. My CRediT roles on the paper are formal analysis, data curation and visualization — the signal filtering and component decomposition were done by the research team, not by me. Published as a co-author (7th of 10) in SCIE 'Applied Sciences'.",
                "tags": "`Python` `Pandas` `Matplotlib` `Survey aggregation`",
            },
        ],
        "stack_head": "## Tech Stack",
        "profilegraph_head": "## Profile graph",
        "profilegraph_caption": "The text on each line names the relationship. Hover or click a node to highlight just the relationships attached to it. Drag to pan, scroll to zoom.",
        "stacks": [
            ("**AI / LLM**", "LangChain · RAG · GraphRAG · Agentic RAG · Hybrid(BM25+dense)  \nOllama · Groq · FAISS · PyTorch  \nLLM eval · Guardrails · MCP · Observability · CI"),
            ("**Data Engineering**", "Pandas · NumPy · Matplotlib  \nTableau · Power BI · Streamlit  \nSQL · Docker · Git"),
            ("**MLOps / Infra**", "MLflow · NVIDIA Triton · ONNX  \nGitea Actions · GitHub Actions · Prometheus · Grafana  \nEvidently(PoC) · Docker Compose"),
        ],
        "personal_head": "## Personal Projects",
        "personal_projects": [
            {
                "title": "JisangFolio",
                "desc": "This portfolio itself. The full resume (~3K tokens) is injected into the system prompt — no document RAG needed — and I built a regression eval harness (rule-based scoring + a separate LLM judge) that keeps factual accuracy stable across prompt/model changes. It caught a stale resume copy leaking into the bot — and later caught two defects in the harness itself: it did not share the app's inference settings, and it never exercised the prompt the app actually assembles. The golden set is 20 cases; the most recent complete run is 17/20 (n=20 — a before/after signal, not a benchmark). On top of that: GraphRAG, a guardrails layer, self-hosted LLM observability, hybrid RAG, and GitHub Actions CI.",
                "tags": "`Groq · Qwen3 27B` `Streamlit` `eval harness` `Python`",
                "link": "https://jisangfolio.streamlit.app",
            },
            {
                "title": "MLOps Docs Assistant",
                "desc": "An Agentic RAG over an MLOps pipeline corpus (official Google/AWS/Azure/Vertex docs + an on-prem KETI pipeline reference). A self-correcting loop — retrieve → grade relevance → rewrite & re-retrieve → answer with citations → self-check groundedness — refuses out-of-corpus questions and is regression-tested (retrieval hit + faithfulness) on a golden set — pass rates are recorded per run in `evals/report.md`.",
                "tags": "`Agentic RAG` `FAISS+BM25` `Self-correction` `Groundedness eval`",
                "link": "page:pages/4_MLOps_Docs.py",
            },
            {
                "title": "JisangData",
                "desc": "An LLM router classifies each question: aggregation/stats queries generate pandas code and run it in a **reduced-capability namespace** (no module objects, dunder access statically rejected, writers allowlisted — explicitly not a sandbox); search/summary queries use FAISS RAG. Auto-fallback to RAG on code error.",
                "tags": "`LangChain` `FAISS` `HuggingFace` `Pandas Code Gen` `Streamlit`",
                "link": "page:pages/2_Data_Analysis.py",
            },
            {
                "title": "JisangFolio MCP Server",
                "desc": "An MCP server that lets Claude Desktop query my portfolio directly. Built with FastMCP — tools for profile/experience/projects/skills/publications plus a first-person Q&A tool (`ask_jisang`).",
                "tags": "`fastmcp` `MCP` `Claude Desktop` `Groq`",
                "link": "",
            },
        ],
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
        {"kind": "학력",  "item": "University of Washington",      "start": "2019-09-01", "end": "2020-06-30", "detail": "Pre-Science (INFO · CSE · STAT)"},
        {"kind": "학력",  "item": "University of Washington",      "start": "2022-12-01", "end": "2024-06-30", "detail": "Pre-Science (INFO · CSE · STAT) · 복학"},
        {"kind": "군복무", "item": "어학병 (제3함대 · 한미연합사)", "start": "2021-02-15", "end": "2022-10-14", "detail": "영어 통역 병과"},
        {"kind": "학력",  "item": "UIUC · BSIS+DS",               "start": "2024-06-01", "end": "2025-12-20", "detail": "Information Science + Data Science, GPA 3.89/4.0"},
        {"kind": "경력",  "item": "삼성SDI · 데이터 엔지니어 인턴", "start": "2025-06-01", "end": "2025-08-31", "detail": "폐쇄망 RAG 챗봇 — 검색·분기·UI 담당 → 임원 PoC 호평"},
        {"kind": "논문",  "item": "TEBO · SCIE 논문 게재",          "start": "2025-01-01", "end": "2025-07-31", "detail": "Applied Sciences 공저 · 코호트 정합화 · 설문 집계 · 그림 출고"},
        {"kind": "활동",  "item": "KSA 웹팀 (UIUC)",               "start": "2024-08-01", "end": "2025-06-30", "detail": "한인 학생회 웹사이트 사용성 및 성능 개선"},
        {"kind": "경력",  "item": "KETI · AX 연구본부 위촉연구원",      "start": "2026-02-01", "end": "2026-09-25", "detail": "온프레미스 MLOps 플랫폼 구축·운영 · Triton 모델 서빙 · 학습→배포 자동화(Level 1) · 디지털 트윈 연동"},
        {"kind": "경력",  "item": "연합인포맥스 · 금융공학연구소",        "start": "2026-09-28", "end": "2026-12-31", "detail": "재직 중"},
    ]
    col_구분, col_항목, col_시작, col_종료, col_상세 = "kind", "item", "start", "end", "detail"
else:
    timeline_rows = [
        {"kind": "Education", "item": "University of Washington",        "start": "2019-09-01", "end": "2020-06-30", "detail": "Pre-Science (INFO · CSE · STAT)"},
        {"kind": "Education", "item": "University of Washington",        "start": "2022-12-01", "end": "2024-06-30", "detail": "Pre-Science (INFO · CSE · STAT) · Return"},
        {"kind": "Military",  "item": "Military Service (ROKN)",         "start": "2021-02-15", "end": "2022-10-14", "detail": "English Interpreter · 3rd Fleet & USFK"},
        {"kind": "Education", "item": "UIUC · BSIS+DS",                  "start": "2024-06-01", "end": "2025-12-20", "detail": "Information Science + Data Science, GPA 3.89/4.0"},
        {"kind": "Work",      "item": "Samsung SDI · Data Eng. Intern",  "start": "2025-06-01", "end": "2025-08-31", "detail": "Air-gapped RAG chatbot (retrieval·routing·UI) → praised by executives"},
        {"kind": "Research",  "item": "TEBO · SCIE Publication",         "start": "2025-01-01", "end": "2025-07-31", "detail": "Applied Sciences co-author · cohort curation · survey aggregation · figures"},
        {"kind": "Activity",  "item": "KSA Web Team (UIUC)",              "start": "2024-08-01", "end": "2025-06-30", "detail": "Improved usability and performance of Korean Student Association website"},
        {"kind": "Work",      "item": "KETI · Research Engineer, AX Research Division",      "start": "2026-02-01", "end": "2026-09-25", "detail": "On-prem MLOps platform · Triton model serving · train→deploy automation (Level 1) · digital twin integration"},
        {"kind": "Work",      "item": "Yonhap Infomax · Financial Engineering Research Institute", "start": "2026-09-28", "end": "2026-12-31", "detail": "Current role"},
    ]
    col_구분, col_항목, col_시작, col_종료, col_상세 = "kind", "item", "start", "end", "detail"

df = pd.DataFrame(timeline_rows)
df[col_시작] = pd.to_datetime(df[col_시작])
df[col_종료] = pd.to_datetime(df[col_종료])

# ── 히어로 (사진 + 소개 + CTA) ────────────────────────────────────
_hero_txt, _hero_photo = st.columns([2, 1])
with _hero_txt:
    st.caption(t["subtitle"])
    st.title(t["title"])
    st.markdown(t["location"], unsafe_allow_html=True)
    st.markdown(t["hero_tagline"])
    _hb1, _hb2 = st.columns(2)
    with _hb1:
        if st.button(t["cta_btn"], type="primary", use_container_width=True, key="hero_chat"):
            st.switch_page("pages/1_Chat.py")
    with _hb2:
        if st.button(t["data_btn"], use_container_width=True, key="hero_data"):
            st.switch_page("pages/2_Data_Analysis.py")
with _hero_photo:
    _photo_path = os.path.join(os.path.dirname(__file__), "assets", "profile.jpg")
    if os.path.exists(_photo_path):
        _enc = _b64m.b64encode(open(_photo_path, "rb").read()).decode()
        st.markdown(
            "<div style='text-align:center;padding-top:6px'><img src='data:image/jpeg;base64,"
            + _enc
            + "' style='width:180px;height:180px;object-fit:cover;border-radius:50%;border:1px solid var(--jf-rule)'/></div>",
            unsafe_allow_html=True,
        )

st.divider()

# ── 경력 타임라인 ─────────────────────────────────────────────────
st.markdown(t["timeline_head"])

# y축을 '가장 이른 시작일' 기준 시간순으로 정렬 → 위에서 아래로 읽으면 시간 흐름(계단식)
_y_order = df.sort_values(col_시작)[col_항목].drop_duplicates().tolist()

fig = px.timeline(
    df,
    x_start=col_시작,
    x_end=col_종료,
    y=col_항목,
    color=col_구분,
    color_discrete_map=COLOR_MAP,
    hover_name=col_항목,
    hover_data={col_상세: True, col_시작: "|%Y.%m", col_종료: "|%Y.%m", col_구분: False, col_항목: False},
    # 다섯 키를 전부 매핑한다. 예전엔 두 개만 처리해서, 영어 UI 의 Plotly 호버 툴팁에
    # "상세=Air-gapped RAG chatbot…" 처럼 한글 필드명이 그대로 떴다
    # (영어권 채용담당자가 보는 화면이다). 데이터 키는 내부용 영문으로 두고
    # 보이는 라벨만 여기서 언어별로 붙인다.
    labels={
        col_항목: "", col_구분: "",
        col_상세: "상세" if lang == "한국어" else "Detail",
        col_시작: "시작" if lang == "한국어" else "Start",
        col_종료: "종료" if lang == "한국어" else "End",
    },
)
fig.update_yaxes(categoryorder="array", categoryarray=_y_order, autorange="reversed")
fig.update_layout(
    height=460,
    bargap=0.28,
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

# ── 주요 프로젝트 ─────────────────────────────────────────────────
st.markdown(t["proj_head"])
# Row 1: KETI (full width)
with st.container(border=True):
    st.markdown(f"**{t['projects'][0]['title']}**")
    st.caption(t["projects"][0]["period"])
    _keti_lead, _sep, _keti_rest = t["projects"][0]["desc"].partition(". ")
    st.markdown(f"**{_keti_lead}.**")
    st.markdown(_keti_rest)
    st.caption(t["projects"][0]["tags"])
    grafana_path = os.path.join(os.path.dirname(__file__), "assets", "mlops_grafana.png")
    if os.path.exists(grafana_path):
        st.image(
            grafana_path,
            caption="Prometheus + Grafana 모니터링 대시보드 (Triton 실시간 메트릭)" if lang == "한국어" else "Prometheus + Grafana Monitoring Dashboard (Triton live metrics)",
            use_container_width=True,
        )
# Row 2: Samsung SDI + TEBO (side by side)
# 컬럼 수를 프로젝트 수에 맞춘다. 2로 고정하면 zip 이 짧은 쪽에서 끊겨
# 세 번째 카드부터 화면에서 조용히 사라진다.
row2 = st.columns(len(t["projects"]) - 1)
for col, proj in zip(row2, t["projects"][1:]):
    with col:
        with st.container(border=True):
            st.markdown(f"**{proj['title']}**")
            st.caption(proj["period"])
            st.markdown(proj["desc"])
            st.caption(proj["tags"])

# ── 기술 스택 ─────────────────────────────────────────────────────
st.markdown(t["stack_head"])
cols = st.columns(3)
for col, (header, body) in zip(cols, t["stacks"]):
    with col:
        st.markdown(header)
        st.markdown(body)

st.divider()

# ── 학력 ──────────────────────────────────────────────────────────
st.markdown(t["edu_head"])
st.markdown(t["edu_body"])

st.divider()

# ── 작동 원리 ─────────────────────────────────────────────────────
st.markdown(t["how_head"])
st.caption(t["how_intro"])
tab1, tab2, tab3, tab4 = st.tabs([t["arch_tab1"], t["arch_tab2"], t["arch_tab3"], t["arch_tab4"]])
with tab1:
    col1, col2, col3, col4, col5 = st.columns([3, 1, 3, 1, 3])
    with col1:
        st.info(t["arch"][0])
    with col2:
        st.markdown("<div class='jf-arrow'>→</div>", unsafe_allow_html=True)
    with col3:
        st.info(t["arch"][1])
    with col4:
        st.markdown("<div class='jf-arrow'>→</div>", unsafe_allow_html=True)
    with col5:
        st.info(t["arch"][2])
with tab2:
    d1, d2, d3, d4, d5, d6, d7 = st.columns([3, 1, 3, 1, 3, 1, 3])
    for box, content in zip([d1, d3, d5, d7], t["arch_data"]):
        box.info(content)
    for arrow in [d2, d4, d6]:
        arrow.markdown("<div class='jf-arrow'>→</div>", unsafe_allow_html=True)
with tab3:
    m1, m2, m3, m4, m5 = st.columns([3, 1, 3, 1, 3])
    for box, content in zip([m1, m3, m5], t["arch_mcp"]):
        box.info(content)
    for arrow in [m2, m4]:
        arrow.markdown("<div class='jf-arrow'>→</div>", unsafe_allow_html=True)
with tab4:
    a1, a2, a3, a4, a5, a6, a7 = st.columns([3, 1, 3, 1, 3, 1, 3])
    for box, content in zip([a1, a3, a5, a7], t["arch_agentic"]):
        box.info(content)
    for arrow in [a2, a4, a6]:
        arrow.markdown("<div class='jf-arrow'>→</div>", unsafe_allow_html=True)

# ── 프로필 구조 그래프 (프로필 SSOT — 챗봇과 데이터 공유) ──────────
st.markdown(t["profilegraph_head"])
components.html(profile_graph.to_vis_html(lang),
                height=profile_graph.EMBED_HEIGHT, scrolling=False)
st.caption(t["profilegraph_caption"])

# ── 코드 지식그래프 (자체 AST 파서 gen_codegraph.py 생성 · graphify 아님) ──
st.markdown(t["graph_head"])
st.markdown(t["graph_bullets"])
graph_path = os.path.join(os.path.dirname(__file__), "assets", "codegraph.html")
if os.path.exists(graph_path):
    with open(graph_path, "r", encoding="utf-8") as gf:
        components.html(gf.read(), height=600, scrolling=False)
    st.caption(t["graph_caption"])
else:
    st.caption(t["graph_missing"])

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
                    st.switch_page(proj["link"].split("page:", 1)[1])
