"""
JisangFolio MCP Server
Claude Desktop에서 박지상의 포트폴리오 데이터를 직접 조회할 수 있는 MCP 서버입니다.

연결 방법 (claude_desktop_config.json):
{
  "mcpServers": {
    "jisangfolio": {
      "command": "python",
      "args": ["/Users/jjpark/Desktop/info/jisangfolio/jisangfolio_mcp.py"]
    }
  }
}
"""

from fastmcp import FastMCP

mcp = FastMCP("JisangFolio — 박지상 포트폴리오")


@mcp.tool()
def get_profile() -> str:
    """박지상(Jisang Park)의 기본 프로필, 학력, 연락처를 반환합니다."""
    return """
이름: 박지상 (Jisang Park)
현직: 한국전자기술연구원(KETI) AX연구본부 AI 에이전트 개발 연구원 (계약직, 2026.02~)
학력: UIUC Information Science + Data Science (BSIS+DS), GPA 3.89/4.0, 2025.12 졸업
이전: University of Washington, Seattle (Pre-Science, 2019~2024)
군복무: 대한민국 해군 어학병 병장 만기제대 (2021.02~2022.10) — 광주함 함상근무 10개월, 한미연합사 영어 통역
어학: 한국어(상), 영어(상, OPIc IH), 미국 거주 10년 (고교+대학 전과정)
연락처: jjpark324434@gmail.com | linkedin.com/in/jisangpark | github.com/jisangfolio
포트폴리오: jisangfolio.streamlit.app
"""


@mcp.tool()
def get_experience(company: str = "") -> str:
    """
    경력 정보를 반환합니다.
    company 파라미터로 'KETI' 또는 'Samsung'(삼성SDI)을 지정하면 해당 경력만 반환합니다.
    """
    keti = """
[한국전자기술연구원 (KETI) — AX연구본부 AI 에이전트 개발 연구원]
기간: 2026.02 ~ 현재 / 계약직
연봉: 3,300만원

▸ 연구1: 송산그린시티 디지털 트윈 시스템 연동 (2026.02~04, 완료)
  - 3파트(데이터플랫폼/SWMM/Unity) 통합 연동 및 NGSI-LD 데이터 모델 등록
  - MQTT + HTTP 하이브리드 통신 구조 분석, Ports and Adapters 패턴 적용
  - 연동 구조도·시퀀스 다이어그램 정리 후 내부 발표

▸ 연구2: MLOps 기반 도시냉각 AI 모델 서빙 인프라 구축 (2026.03~ 진행중)
  - 한-싱가포르 국제공동연구 (총 16억원, 4년): 부산대·부경대·KETI·온품·A*STAR
  - KETI 역할: "AI 모델 서빙 지원 도시 냉각 데이터 플랫폼 기술 개발"
  - 부경대 제공 PyTorch 3D U-Net(+CBAM+Attention Gate) → ONNX 변환 → Triton 서빙
  - 1차 학습(45건): MAE 0.53°C, R² 0.82 → 2차 학습(291건): MAE 0.26°C, R² 0.95 (MAE 51%↓)
  - CFD 시뮬레이션 수십 분 → Triton 추론 ~200ms
  - MLOps 6개 구현: MLflow Tracking·Registry + MinIO + Gitea + Gitea Actions CI + Triton
  - Prometheus + Grafana 모니터링 (7패널): GPU 사용률·VRAM·전력·추론 rate·compute/queue 시간
  - 자체호스팅 원칙(상부 방침): 외부 SaaS 회피 → GitHub→Gitea, S3→MinIO, 클라우드→Prometheus+Grafana
  - 역할: 아키텍처 설계, 기술 선정, 환경 구축/운영, 실험 수행, 결과 분석, 발표자료 작성
"""

    sdi = """
[삼성SDI — DI(Data Intelligence) 그룹 데이터 엔지니어 인턴]
기간: 2025.06 ~ 2025.08

▸ 폐쇄망 특허 검색 RAG 챗봇 "SPA(SDI Patent Assistant)" 1인 단독 개발
  - 완전 인터넷 차단 환경에서 Ollama + Qwen2.5-72B 로컬 서빙
  - LangChain + FAISS 벡터 DB, MinIO에서 patent.csv 로드
  - 대화 이력(최근 5턴) 기반 맥락 유지 + 이전 RAG 선택지 저장 → 후속 질의 자동 재검색
  - Rule-based Agent: "그래프/통계/출원" 키워드 → LLM 우회 → pandas 집계 + st.bar_chart 시각화
  - Streamlit UI + Docker 배포, 임원 대상 PoC 발표에서 호평 획득
"""

    company_upper = company.upper()
    if "KETI" in company_upper:
        return keti
    if "SAMSUNG" in company_upper or "SDI" in company_upper or "삼성" in company:
        return sdi
    return keti + "\n" + sdi


@mcp.tool()
def get_projects() -> str:
    """주요 프로젝트 및 개인 프로젝트 목록을 반환합니다."""
    return """
[주요 프로젝트]

1. KETI MLOps 도시냉각 AI 서빙 인프라
   - PyTorch 3D U-Net → ONNX → NVIDIA Triton 서빙 파이프라인
   - MLflow·MinIO·Gitea·Gitea Actions·Prometheus·Grafana (MLOps 6/12 구현)
   - 2차 학습으로 MAE 51% 개선, R² 0.95 달성
   - 스택: PyTorch, ONNX, Triton, MLflow, MinIO, Gitea, Docker, WSL2, Prometheus, Grafana

2. 삼성SDI SPA — 폐쇄망 특허 RAG 챗봇
   - 완전 인터넷 차단 환경, 1인 단독 개발
   - Rule-based Agent + RAG 하이브리드, 임원 PoC 호평
   - 스택: Ollama, Qwen2.5-72B, LangChain, FAISS, Streamlit, Docker

3. TEBO 균형 분석 · SCIE 논문
   - Applied Sciences (SCIE) 2025.07 게재
   - CoP 시계열 → Butterworth Filter + FFT → Rambling/Trembling 분해
   - R² ≈ 0.85, Pearson r = 0.92 (p<0.001)
   - 스택: Python, NumPy, SciPy, Matplotlib

[개인 프로젝트]

4. JisangFolio (jisangfolio.streamlit.app)
   - 이력서 기반 AI 면접 챗봇 + 데이터 분석 도구
   - Groq + Qwen3 32B, 시스템 프롬프트 전문 주입(RAG 불필요)
   - LLM 라우터 → pandas 코드 생성·샌드박스 실행 or FAISS RAG
   - 현재 보고 계신 이 MCP 서버도 JisangFolio의 일부입니다
   - 스택: Streamlit, Groq, LangChain, FAISS, Plotly, fastmcp
"""


@mcp.tool()
def get_skills() -> str:
    """기술 스택을 카테고리별로 반환합니다."""
    return """
[AI / LLM]
LangChain, RAG, FAISS, Prompt Engineering, Hugging Face, PyTorch, ONNX
Rule-based Agent, Ollama, Groq, fastmcp (MCP 서버 개발)

[MLOps / Infra]
MLflow (Tracking + Model Registry), NVIDIA Triton Inference Server
MinIO (S3 호환), Gitea (자체호스팅 Git), Gitea Actions (CI)
Prometheus, Grafana (PromQL, 대시보드 프로비저닝)
Docker, WSL2, Docker Compose

[Data Science]
Pandas, NumPy, Matplotlib, SciPy, spaCy, Gensim
Butterworth Filter, FFT, 시계열 분석
BeautifulSoup (웹 스크래핑)

[Visualization]
Streamlit, Plotly, Tableau, Power BI

[IoT / Platform]
NGSI-LD, MQTT, REST API, Postman, SWMM

[Languages]
Python (고급), R, SQL

[Tools]
Git, GitHub, Gitea, Docker, VSCode, Claude Code
"""


@mcp.tool()
def get_publications() -> str:
    """논문 및 학술 성과를 반환합니다."""
    return """
[게재 논문]
제목: "Effect of Tai Chi Practice on the Adaptation to Sensory and Motor Perturbations While Standing in Older Adults"
저널: Applied Sciences (SCIE, 국외)
게재일: 2025.07
지도교수: Dr. Manuel E. Hernandez (UIUC)

[개인 기여 요약]
- CoP(압력중심) 시계열 데이터 분석 파이프라인 전체 단독 설계·구현
- 4차 Butterworth 저역통과 필터(5Hz) → 센서 노이즈 제거
- Zero-crossing 기반 평형점 탐지 → Cubic spline 보간으로 Rambling 재구성
- FFT → 0~0.3Hz 적분 → Low-frequency rambling power 산출
- Young(n=1) / Healthy Older(n=37) / TCOA 임상군(n=22) 비교 분석
- R² ≈ 0.85 (단일 Rambling 파워로 자세 동요 분산 85%+ 설명)
- Pearson r = 0.92 (p<0.001)

[개인 초록]
제목: "Postural Control in Healthy and TCOA Adults: Rambling-Component Analysis and Simulated CoP Trajectories"
저자: JJ Park (단독)
"""


@mcp.tool()
def ask_jisang(question: str) -> str:
    """
    박지상에게 자유롭게 질문하세요. Groq + Qwen3 32B가 1인칭으로 답변합니다.
    사용하려면 GROQ_API_KEY 환경변수가 필요합니다.
    """
    import os
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "GROQ_API_KEY 환경변수가 설정되지 않았습니다. claude_desktop_config.json의 env 항목을 확인해 주세요."

    resume_context = "\n\n".join([
        get_profile(),
        get_experience(),
        get_projects(),
        get_skills(),
        get_publications(),
    ])

    system_prompt = f"""/no_think
당신은 데이터 엔지니어이자 AI 개발자인 '박지상(JJ Park)' 본인입니다.
아래 [이력서] 내용을 바탕으로 질문에 1인칭 시점으로 답변하세요.
- 한국어로 답변하세요.
- 볼드체(**)를 사용하지 마세요.
- 이력서에 없는 내용은 지어내지 마세요.

[이력서]
{resume_context}"""

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="qwen/qwen3-32b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        max_tokens=800,
    )
    content = response.choices[0].message.content or ""
    if "</think>" in content:
        content = content.split("</think>", 1)[1].lstrip("\n")
    return content.replace("**", "")


if __name__ == "__main__":
    mcp.run()
