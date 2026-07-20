"""프로필 지식그래프 (단일 소스 SSOT).

박지상의 학력·경력·프로젝트·스킬을 노드/엣지로 한 곳에 정의하고, 여기서
  - to_vis_html(lang): 홈에 임베드할 인터랙티브 vis-network 그래프(HTML)
  - to_prompt_text(lang): 챗봇 시스템 프롬프트에 주입할 구조 요약(텍스트)
을 함께 생성한다. 그래프 그림과 챗봇 컨텍스트가 같은 데이터에서 나오도록 한 SSOT.

⚠️ 노드 설명은 keti_mlops_full_dump / 작업가이드 §2 가드레일 준수:
   KETI="주도적 설계·구축"(단독X)·"전문생산기술연구소"(정출연X)·부경대 제공 모델,
   SDI RAG=1인 단독·임원 PoC 호평, TEBO=공저. Kubeflow/K8s/정출연 등 금지어 없음.
"""
import json

# group: person / edu / work / project / paper / skill
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

    # 프로젝트 / 성과
    {"id": "mlops", "group": "project", "ko": "온프레 MLOps 플랫폼", "en": "On-prem MLOps platform",
     "desc_ko": "폐쇄망 자체호스팅 MLOps 플랫폼을 docker-compose로 주도적으로 설계·구축.",
     "desc_en": "Led design & build of an air-gapped self-hosted MLOps platform (docker-compose)."},
    {"id": "rag", "group": "project", "ko": "폐쇄망 RAG (SPA)", "en": "Air-gapped RAG (SPA)",
     "desc_ko": "완전 차단망 특허검색 RAG 챗봇 1인 단독 개발 → 임원 PoC 호평.",
     "desc_en": "Solo-built patent-search RAG chatbot in a fully air-gapped env → executive PoC praised."},
    {"id": "tebo", "group": "paper", "ko": "TEBO 논문", "en": "TEBO paper",
     "desc_ko": "CoP 신호처리 파이프라인 기여 · SCIE 'Applied Sciences' 공저(2025).",
     "desc_en": "CoP signal-processing pipeline · co-author, SCIE 'Applied Sciences' (2025)."},
    {"id": "jisangfolio", "group": "project", "ko": "JisangFolio", "en": "JisangFolio",
     "desc_ko": "이 포트폴리오 · 회귀 평가 하니스로 사실 정확도 통과율 62%→94%.",
     "desc_en": "This portfolio · a regression eval harness lifted factual accuracy 62%→94%."},

    # 스킬 (프로젝트 하위)
    {"id": "triton", "group": "skill", "ko": "Triton 서빙", "en": "Triton serving",
     "desc_ko": "부경대 제공 3D U-Net을 ONNX로 변환해 GPU 서빙(약 200ms) · 외부 PINN 3종 통합.",
     "desc_en": "PKNU-provided 3D U-Net → ONNX → GPU serving (~200ms) · unified 3 external PINNs."},
    {"id": "mlflow", "group": "skill", "ko": "MLflow 거버넌스", "en": "MLflow governance",
     "desc_ko": "실험·레지스트리·라이프사이클 태그 거버넌스 · v1↔v2 비교(MAE 0.53→0.26°C).",
     "desc_en": "Experiments·registry·lifecycle-tag governance · v1↔v2 compare (MAE 0.53→0.26°C)."},
    {"id": "ci", "group": "skill", "ko": "Gitea Actions CI", "en": "Gitea Actions CI",
     "desc_ko": "ONNX 검증→배포 CI 체인 · 체크아웃 14분→4초 단축.",
     "desc_en": "ONNX validate→deploy CI chain · checkout 14min→4s."},
    {"id": "monitor", "group": "skill", "ko": "Prometheus·Grafana", "en": "Prometheus·Grafana",
     "desc_ko": "서빙 메트릭 7패널 대시보드 · Streamlit 운영 포털 · Evidently 드리프트(PoC).",
     "desc_en": "7-panel serving dashboard · Streamlit ops portal · Evidently drift (PoC)."},
    {"id": "ollama", "group": "skill", "ko": "Ollama·Qwen2.5", "en": "Ollama·Qwen2.5",
     "desc_ko": "온프레미스 sLLM 자체호스팅(Qwen2.5-72B).",
     "desc_en": "On-prem self-hosted sLLM (Qwen2.5-72B)."},
    {"id": "langfaiss", "group": "skill", "ko": "LangChain·FAISS", "en": "LangChain·FAISS",
     "desc_ko": "임베딩(all-MiniLM-L6-v2) · FAISS 검색(k=5) · 최근 5턴 기반 자동 재검색.",
     "desc_en": "Embedding (all-MiniLM-L6-v2) · FAISS retrieval (k=5) · auto re-retrieval over the last 5 turns."},
    {"id": "ruleagent", "group": "skill", "ko": "Rule-based Agent", "en": "Rule-based Agent",
     "desc_ko": "'그래프/통계/출원' 키워드 감지 시 LLM 우회 → pandas 집계·차트로 환각 차단.",
     "desc_en": "Keyword ('graph/stats/filing') detection bypasses the LLM → pandas aggregation·chart to block hallucination."},
    {"id": "eval", "group": "skill", "ko": "LLM eval 하니스", "en": "LLM eval harness",
     "desc_ko": "규칙 채점 + 별도 모델 LLM-judge로 답변 사실성 회귀 검증.",
     "desc_en": "Rule scoring + a separate LLM judge for factual regression."},

    # 학부 코스워크 (강의 프로젝트 수준 — 과대표현 금지, 학부_코스워크_카탈로그.md 근거)
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
     "desc_en": "Data Programming (UW) — k-means, image processing, and a NetworkX social graph built from scratch (coursework)."},
]

EDGES = [
    ("jjpark", "uiuc"), ("jjpark", "uw"), ("jjpark", "keti"), ("jjpark", "sdi"),
    ("jjpark", "jisangfolio"),
    ("uiuc", "tebo"), ("uiuc", "cs307"), ("uiuc", "is327"), ("uiuc", "is477"), ("uiuc", "is467"),
    ("uw", "cse160"),
    ("keti", "mlops"),
    ("sdi", "rag"),
    ("mlops", "triton"), ("mlops", "mlflow"), ("mlops", "ci"), ("mlops", "monitor"),
    ("rag", "ollama"), ("rag", "langfaiss"), ("rag", "ruleagent"),
    ("jisangfolio", "eval"),
]

GROUP_COLOR = {
    "person": "#7AA2F7",   # 브랜드 periwinkle
    "edu": "#4C9BE8",
    "work": "#2ECC71",
    "project": "#F39C12",
    "paper": "#E0B03A",
    "skill": "#9B8CFF",
    "course": "#4FD1C5",
}
GROUP_SIZE = {"person": 30, "work": 22, "edu": 20, "project": 20, "paper": 18, "skill": 14, "course": 13}


def _label(n, ko):
    return n["ko"] if ko else n["en"]


def _desc(n, ko):
    return n["desc_ko"] if ko else n["desc_en"]


_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  html, body { margin:0; padding:0; background:transparent; }
  #net { width:100%; height:560px; }
</style></head>
<body>
<div id="net"></div>
<script>
  const nodes = new vis.DataSet(__NODES__);
  const edges = new vis.DataSet(__EDGES__);
  const options = {
    nodes: { borderWidth: 0, shadow: false, shape: 'dot' },
    edges: { color: { color: 'rgba(180,190,210,0.30)', highlight: '#7AA2F7' },
             smooth: { type: 'continuous' }, width: 1.2 },
    physics: { barnesHut: { gravitationalConstant: -9000, springLength: 135, springConstant: 0.03 },
               stabilization: { iterations: 220 } },
    interaction: { hover: true, tooltipDelay: 80, zoomView: true, dragView: true }
  };
  const network = new vis.Network(document.getElementById('net'), { nodes, edges }, options);
  network.once('stabilizationIterationsDone', function () { network.setOptions({ physics: false }); });
</script>
</body></html>"""


def to_vis_html(lang="한국어"):
    """홈에 임베드할 인터랙티브 프로필 그래프 HTML을 반환한다."""
    ko = (lang == "한국어")
    vis_nodes = [{
        "id": n["id"],
        "label": _label(n, ko),
        "title": _desc(n, ko),          # hover 툴팁 = 설명
        "color": GROUP_COLOR[n["group"]],
        "size": GROUP_SIZE[n["group"]],
        "font": {"color": "#E6E8EE", "size": 16 if n["group"] == "person" else 13},
    } for n in NODES]
    vis_edges = [{"from": a, "to": b} for (a, b) in EDGES]
    html = _HTML_TEMPLATE.replace("__NODES__", json.dumps(vis_nodes, ensure_ascii=False))
    html = html.replace("__EDGES__", json.dumps(vis_edges, ensure_ascii=False))
    return html


def to_prompt_text(lang="한국어"):
    """챗봇 시스템 프롬프트에 주입할 구조 요약(들여쓰기 아웃라인)을 반환한다."""
    ko = (lang == "한국어")
    label = {n["id"]: _label(n, ko) for n in NODES}
    children = {}
    for a, b in EDGES:
        children.setdefault(a, []).append(b)

    lines = []

    def walk(nid, depth):
        for c in children.get(nid, []):
            lines.append("  " * depth + "- " + label[c])
            walk(c, depth + 1)

    lines.append(label["jjpark"])
    walk("jjpark", 1)
    return "\n".join(lines)
