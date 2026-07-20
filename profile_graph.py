"""프로필 지식그래프 (단일 소스 SSOT).

박지상의 학력·경력·프로젝트·스킬·코스워크를 노드/엣지로 한 곳에 정의하고, 여기서
  - to_vis_html(lang): 홈에 임베드할 인터랙티브 vis-network 그래프(HTML)
  - to_prompt_text(lang): 챗봇 시스템 프롬프트에 주입할 구조 요약(텍스트)
을 함께 생성한다. 그래프 그림과 챗봇 컨텍스트가 같은 데이터에서 나오도록 한 SSOT.

트리가 아니라 '망'이 되도록 공유 기술 노드(Docker·Streamlit·LangChain·FAISS·Groq·
PyTorch)를 여러 프로젝트가 함께 가리키게 해 교차연결을 만든다.

⚠️ 노드 설명은 keti_mlops_full_dump / 학부_코스워크_카탈로그 / SDI 실코드 / 작업가이드 §2
   가드레일 준수: KETI="주도적 설계·구축"(단독X)·"전문생산기술연구소"(정출연X)·부경대 제공
   모델, SDI RAG=1인 단독·임원 PoC 호평·Rule-based Agent, TEBO=공저·노이즈 필터링, 코스워크
   =강의 프로젝트 수준(IS477 R² 성과화 금지). FAISS/LangChain은 SDI·JisangData만(KETI 아님).
   Kubeflow/K8s/정출연 등 금지어 없음.
"""
import json

# group: person / edu / work / project / paper / course / skill
NODES = [
    {"id": "jjpark", "group": "person", "ko": "박지상", "en": "Jisang Park",
     "desc_ko": "온프레미스·폐쇄망 MLOps와 RAG·LLM 서빙을 소유하는 AI 엔지니어.",
     "desc_en": "AI engineer who owns on-prem / air-gapped MLOps and RAG·LLM serving."},

    # 학력
    {"id": "uiuc", "group": "edu", "ko": "UIUC", "en": "UIUC",
     "desc_ko": "Information Science + Data Science 학사 · GPA 3.89/4.0 (2025.12 졸업).",
     "desc_en": "B.S. Information Science + Data Science · GPA 3.89/4.0 (Dec 2025)."},
    {"id": "uw", "group": "edu", "ko": "UW", "en": "UW",
     "desc_ko": "University of Washington · Pre-Science · Dean's List.",
     "desc_en": "University of Washington · Pre-Science · Dean's List."},

    # 경력
    {"id": "keti", "group": "work", "ko": "KETI", "en": "KETI",
     "desc_ko": "AX 연구본부 연구원(2026.02~현재) · 산업부 소관 전문생산기술연구소.",
     "desc_en": "Researcher, AX Research Division (Feb 2026~) · industrial R&D institute."},
    {"id": "sdi", "group": "work", "ko": "삼성SDI", "en": "Samsung SDI",
     "desc_ko": "DI(Data Intelligence)그룹 데이터 엔지니어 인턴(2025.06~08).",
     "desc_en": "Data Engineer Intern, DI (Data Intelligence) Group (Jun~Aug 2025)."},

    # 프로젝트
    {"id": "mlops", "group": "project", "ko": "온프레 MLOps 플랫폼", "en": "On-prem MLOps platform",
     "desc_ko": "폐쇄망 자체호스팅 MLOps 플랫폼을 docker-compose로 주도적으로 설계·구축.",
     "desc_en": "Led design & build of an air-gapped self-hosted MLOps platform (docker-compose)."},
    {"id": "rag", "group": "project", "ko": "폐쇄망 RAG (SPA)", "en": "Air-gapped RAG (SPA)",
     "desc_ko": "완전 차단망 특허검색 RAG 챗봇 1인 단독 개발 → 임원 PoC 호평.",
     "desc_en": "Solo-built patent-search RAG chatbot in a fully air-gapped env → executive PoC praised."},
    {"id": "jf", "group": "project", "ko": "JisangFolio", "en": "JisangFolio",
     "desc_ko": "이 포트폴리오 · 회귀 평가 하니스로 사실 정확도 통과율 62%→94%.",
     "desc_en": "This portfolio · a regression eval harness lifted factual accuracy 62%→94%."},
    {"id": "jd", "group": "project", "ko": "JisangData", "en": "JisangData",
     "desc_ko": "LLM 라우터가 집계 질문은 pandas 코드 생성·실행, 검색 질문은 FAISS RAG로 처리(실패 시 RAG 폴백).",
     "desc_en": "An LLM router runs pandas codegen for aggregates and FAISS RAG for search (RAG fallback on failure)."},
    {"id": "mcp", "group": "project", "ko": "MCP 서버", "en": "MCP server",
     "desc_ko": "FastMCP 서버 — 프로필·경력·프로젝트·기술·논문 조회 + ask_jisang(1인칭 Q&A) 6개 툴 노출.",
     "desc_en": "FastMCP server — 6 tools: profile/experience/projects/skills/publications + ask_jisang."},

    # 논문
    {"id": "tebo", "group": "paper", "ko": "TEBO 논문", "en": "TEBO paper",
     "desc_ko": "CoP 신호처리 파이프라인 기여 · SCIE 'Applied Sciences' 공저(2025).",
     "desc_en": "CoP signal-processing pipeline · co-author, SCIE 'Applied Sciences' (2025)."},

    # 학부 코스워크 (강의 프로젝트 수준 — 과대표현 금지)
    {"id": "cs307", "group": "course", "ko": "CS307 · ML", "en": "CS307 · ML",
     "desc_ko": "Models of Learning — 6개 lab로 KNN·RandomForest·GBM·캘리브레이션에서 PyTorch CNN까지(강의 프로젝트).",
     "desc_en": "Models of Learning — 6 labs from KNN·RandomForest·GBM·calibration to a PyTorch CNN (coursework)."},
    {"id": "is327", "group": "course", "ko": "IS327 · 회귀", "en": "IS327 · Regression",
     "desc_ko": "Machine Learning — 게임 판매 예측 회귀 플래그십(Random Forest R²≈0.85, 강의 프로젝트).",
     "desc_en": "Machine Learning — flagship game-sales regression (Random Forest R²≈0.85, coursework)."},
    {"id": "is477", "group": "course", "ko": "IS477 · ETL", "en": "IS477 · ETL",
     "desc_ko": "Data Management & Curation — 시카고 Airbnb ETL 파이프라인(통합·정제·모델링, 강의 프로젝트).",
     "desc_en": "Data Management & Curation — Chicago Airbnb ETL pipeline (integrate·clean·model, coursework)."},
    {"id": "is467", "group": "course", "ko": "IS467 · AI 윤리", "en": "IS467 · AI Ethics",
     "desc_ko": "Data Ethics & Policy — 채용 AI 편향 6단계 연구(EU AI Act·공정성 감사, 강의 프로젝트).",
     "desc_en": "Data Ethics & Policy — 6-stage hiring-AI bias study (EU AI Act·fairness audit, coursework)."},
    {"id": "cse160", "group": "course", "ko": "CSE160 · 직접구현", "en": "CSE160 · From scratch",
     "desc_ko": "Data Programming(UW) — k-means·이미지 처리·NetworkX 소셜그래프를 라이브러리 없이 직접 구현(강의 프로젝트).",
     "desc_en": "Data Programming (UW) — k-means, image processing, and a NetworkX social graph from scratch (coursework)."},
    {"id": "info330", "group": "course", "ko": "INFO330 · DB", "en": "INFO330 · DB",
     "desc_ko": "Database Management — T-SQL JOIN·CTE·저장 프로시저·스키마 정규화(강의 프로젝트).",
     "desc_en": "Database Management — T-SQL JOINs·CTEs·stored procedures·normalization (coursework)."},

    # 기술·도구 (공유 노드 — 여러 프로젝트가 함께 가리켜 교차연결)
    {"id": "triton", "group": "skill", "ko": "Triton 서빙", "en": "Triton serving",
     "desc_ko": "부경대 제공 3D U-Net을 GPU 서빙(약 200ms) · 외부 PINN 3종을 같은 Triton에 통합.",
     "desc_en": "Serves a PKNU-provided 3D U-Net on GPU (~200ms) · unified 3 external PINNs on one Triton."},
    {"id": "onnx", "group": "skill", "ko": "ONNX", "en": "ONNX",
     "desc_ko": "PyTorch 모델을 ONNX(opset 17)로 변환·검증해 Triton 서빙 포맷 확보.",
     "desc_en": "Convert/validate PyTorch models to ONNX (opset 17) for Triton serving."},
    {"id": "mlflow", "group": "skill", "ko": "MLflow 거버넌스", "en": "MLflow governance",
     "desc_ko": "실험·레지스트리·라이프사이클 태그 거버넌스 · v1↔v2 비교(MAE 0.53→0.26°C).",
     "desc_en": "Experiments·registry·lifecycle-tag governance · v1↔v2 compare (MAE 0.53→0.26°C)."},
    {"id": "ci", "group": "skill", "ko": "Gitea Actions CI", "en": "Gitea Actions CI",
     "desc_ko": "ONNX 검증→배포 CI 체인 · 체크아웃 14분→4초 단축.",
     "desc_en": "ONNX validate→deploy CI chain · checkout 14min→4s."},
    {"id": "monitor", "group": "skill", "ko": "Prometheus·Grafana", "en": "Prometheus·Grafana",
     "desc_ko": "서빙 메트릭 7패널 대시보드 · Streamlit 운영 포털 · Evidently 드리프트(PoC).",
     "desc_en": "7-panel serving dashboard · Streamlit ops portal · Evidently drift (PoC)."},
    {"id": "docker", "group": "skill", "ko": "Docker·Compose", "en": "Docker·Compose",
     "desc_ko": "다중 컨테이너 운영 — KETI 자체호스팅 스택과 SDI 폐쇄망 환경 양쪽에서 사용.",
     "desc_en": "Multi-container ops — used across KETI's self-hosted stack and SDI's air-gapped env."},
    {"id": "pytorch", "group": "skill", "ko": "PyTorch", "en": "PyTorch",
     "desc_ko": "부경대 제공 서빙 모델(→ONNX 변환)과 CS307 CNN 실습의 프레임워크.",
     "desc_en": "Framework for the PKNU-provided serving model (→ONNX) and the CS307 CNN lab."},
    {"id": "ollama", "group": "skill", "ko": "Ollama·Qwen2.5", "en": "Ollama·Qwen2.5",
     "desc_ko": "온프레미스 sLLM 자체호스팅(Qwen2.5-72B) — SDI 폐쇄망.",
     "desc_en": "On-prem self-hosted sLLM (Qwen2.5-72B) — SDI air-gapped."},
    {"id": "langchain", "group": "skill", "ko": "LangChain", "en": "LangChain",
     "desc_ko": "검색·생성·라우팅 오케스트레이션 — SDI RAG와 JisangData에서 사용.",
     "desc_en": "Retrieval/generation/routing orchestration — used in SDI RAG and JisangData."},
    {"id": "faiss", "group": "skill", "ko": "FAISS", "en": "FAISS",
     "desc_ko": "벡터 검색 — SDI RAG(k=5, all-MiniLM-L6-v2)와 JisangData에서 사용.",
     "desc_en": "Vector search — SDI RAG (k=5, all-MiniLM-L6-v2) and JisangData."},
    {"id": "streamlit", "group": "skill", "ko": "Streamlit", "en": "Streamlit",
     "desc_ko": "SDI RAG UI · KETI 운영 포털 · JisangFolio · JisangData · 본 사이트 전반.",
     "desc_en": "SDI RAG UI · KETI ops portal · JisangFolio · JisangData · this whole site."},
    {"id": "groq", "group": "skill", "ko": "Groq·Qwen3", "en": "Groq·Qwen3",
     "desc_ko": "Groq(Qwen3 27B) 저지연 추론 — JisangFolio·JisangData·MCP.",
     "desc_en": "Groq (Qwen3 27B) low-latency inference — JisangFolio·JisangData·MCP."},
    {"id": "ruleagent", "group": "skill", "ko": "Rule-based Agent", "en": "Rule-based Agent",
     "desc_ko": "'그래프/통계/출원' 키워드 감지 시 LLM 우회 → pandas 집계·차트로 환각 차단(SDI).",
     "desc_en": "Keyword ('graph/stats/filing') detection bypasses the LLM → pandas aggregation·chart (SDI)."},
    {"id": "eval", "group": "skill", "ko": "LLM eval 하니스", "en": "LLM eval harness",
     "desc_ko": "규칙 채점 + 별도 모델 LLM-judge로 답변 사실성 회귀 검증.",
     "desc_en": "Rule scoring + a separate LLM judge for factual regression."},
    {"id": "scipy", "group": "skill", "ko": "SciPy·FFT", "en": "SciPy·FFT",
     "desc_ko": "TEBO CoP 신호처리 — 4차 Butterworth 노이즈 필터·FFT 주파수 분해.",
     "desc_en": "TEBO CoP signal processing — 4th-order Butterworth denoise·FFT decomposition."},
    {"id": "sql", "group": "skill", "ko": "SQL", "en": "SQL",
     "desc_ko": "T-SQL 복합 JOIN·CTE·저장 프로시저·스키마 정규화(INFO330).",
     "desc_en": "T-SQL complex JOINs·CTEs·stored procedures·normalization (INFO330)."},
]

EDGES = [
    # 뿌리
    ("jjpark", "uiuc"), ("jjpark", "uw"), ("jjpark", "keti"), ("jjpark", "sdi"),
    ("jjpark", "jf"), ("jjpark", "jd"), ("jjpark", "mcp"),
    # 학력 → 코스워크·논문
    ("uiuc", "cs307"), ("uiuc", "is327"), ("uiuc", "is477"), ("uiuc", "is467"),
    ("uiuc", "tebo"),
    ("uw", "cse160"), ("uw", "info330"),
    # 경력 → 프로젝트
    ("keti", "mlops"), ("sdi", "rag"),
    # MLOps 플랫폼 → 기술
    ("mlops", "triton"), ("mlops", "onnx"), ("mlops", "mlflow"), ("mlops", "ci"),
    ("mlops", "monitor"), ("mlops", "docker"), ("mlops", "pytorch"),
    # RAG → 기술
    ("rag", "ollama"), ("rag", "langchain"), ("rag", "faiss"), ("rag", "ruleagent"),
    ("rag", "docker"), ("rag", "streamlit"),
    # 개인 프로젝트 → 기술 (공유 노드로 교차연결)
    ("jf", "eval"), ("jf", "groq"), ("jf", "streamlit"),
    ("jd", "langchain"), ("jd", "faiss"), ("jd", "groq"), ("jd", "streamlit"),
    ("mcp", "groq"),
    # 논문·코스워크 → 기술 (교차연결)
    ("tebo", "scipy"), ("cs307", "pytorch"), ("info330", "sql"),
]

GROUP_COLOR = {
    "person": "#7AA2F7",   # 브랜드 periwinkle
    "edu": "#4C9BE8",
    "work": "#2ECC71",
    "project": "#F39C12",
    "paper": "#E0B03A",
    "course": "#4FD1C5",
    "skill": "#9B8CFF",
}
GROUP_SIZE = {"person": 34, "work": 24, "edu": 22, "project": 22, "paper": 18, "course": 14, "skill": 14}
GROUP_SHAPE = {"course": "square"}  # 코스워크만 사각형으로 구분, 나머지는 dot

LEGEND_LABELS = {
    "한국어": [("person", "인물"), ("edu", "학력"), ("work", "경력"), ("project", "프로젝트"),
             ("paper", "논문"), ("course", "코스워크"), ("skill", "기술·도구")],
    "English": [("person", "Person"), ("edu", "Education"), ("work", "Work"), ("project", "Project"),
                ("paper", "Paper"), ("course", "Coursework"), ("skill", "Skills·Tools")],
}


def _label(n, ko):
    return n["ko"] if ko else n["en"]


def _desc(n, ko):
    return n["desc_ko"] if ko else n["desc_en"]


def _legend_html(lang):
    items = LEGEND_LABELS[lang]
    spans = "".join(
        '<span style="display:inline-flex;align-items:center;margin:0 14px 6px 0;white-space:nowrap;">'
        '<span style="width:10px;height:10px;border-radius:50%;background:{c};display:inline-block;margin-right:5px;"></span>{lab}</span>'.format(
            c=GROUP_COLOR[g], lab=lab)
        for g, lab in items)
    return ('<div style="font:12px Pretendard,-apple-system,sans-serif;color:#AAB2C0;'
            'padding:2px 2px 10px;display:flex;flex-wrap:wrap;">' + spans + '</div>')


_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  html, body { margin:0; padding:0; background:transparent; }
  #net { width:100%; height:600px; }
</style></head>
<body>
__LEGEND__
<div id="net"></div>
<script>
  const nodes = new vis.DataSet(__NODES__);
  const edges = new vis.DataSet(__EDGES__);
  const options = {
    nodes: { borderWidth: 0, shadow: false, font: { face: 'Pretendard, sans-serif' } },
    edges: { color: { color: 'rgba(180,190,210,0.28)', highlight: '#7AA2F7', hover: '#7AA2F7' },
             smooth: { type: 'continuous' }, width: 1.1, hoverWidth: 0.6 },
    physics: { barnesHut: { gravitationalConstant: -14000, centralGravity: 0.25,
                            springLength: 150, springConstant: 0.035, avoidOverlap: 0.3 },
               stabilization: { iterations: 320 } },
    interaction: { hover: true, tooltipDelay: 80, zoomView: true, dragView: true, navigationButtons: false }
  };
  const network = new vis.Network(document.getElementById('net'), { nodes, edges }, options);
  network.once('stabilizationIterationsDone', function () { network.setOptions({ physics: false }); });
</script>
</body></html>"""


def to_vis_html(lang="한국어"):
    """홈에 임베드할 인터랙티브 프로필 그래프 HTML을 반환한다."""
    ko = (lang == "한국어")
    vis_nodes = []
    for n in NODES:
        node = {
            "id": n["id"],
            "label": _label(n, ko),
            "title": _desc(n, ko),          # hover 툴팁 = 설명
            "color": GROUP_COLOR[n["group"]],
            "size": GROUP_SIZE[n["group"]],
            "shape": GROUP_SHAPE.get(n["group"], "dot"),
            "font": {"color": "#E6E8EE", "size": 16 if n["group"] == "person" else 13},
        }
        vis_nodes.append(node)
    vis_edges = [{"from": a, "to": b} for (a, b) in EDGES]
    html = _HTML_TEMPLATE.replace("__LEGEND__", _legend_html(lang))
    html = html.replace("__NODES__", json.dumps(vis_nodes, ensure_ascii=False))
    html = html.replace("__EDGES__", json.dumps(vis_edges, ensure_ascii=False))
    return html


def to_prompt_text(lang="한국어"):
    """챗봇 시스템 프롬프트에 주입할 구조 요약(들여쓰기 아웃라인)을 반환한다.

    공유 노드(여러 부모)가 있어 DAG이므로, 이미 펼친 노드는 다시 펼치지 않도록
    seen 으로 스패닝 트리를 만든다(중복·순환 방지).
    """
    ko = (lang == "한국어")
    label = {n["id"]: _label(n, ko) for n in NODES}
    children = {}
    for a, b in EDGES:
        children.setdefault(a, []).append(b)

    lines = []
    seen = {"jjpark"}

    def walk(nid, depth):
        for c in children.get(nid, []):
            if c in seen:
                continue
            seen.add(c)
            lines.append("  " * depth + "- " + label[c])
            walk(c, depth + 1)

    lines.append(label["jjpark"])
    walk("jjpark", 1)
    return "\n".join(lines)
