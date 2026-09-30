"""프로필 지식그래프 (단일 소스 SSOT).

박지상의 학력·경력·프로젝트·스킬·코스워크를 노드/엣지로 한 곳에 정의하고, 여기서
  - to_vis_html(lang): 홈에 임베드할 인터랙티브 vis-network 그래프(HTML)
  - to_prompt_text(lang): 챗봇 시스템 프롬프트에 주입할 구조 요약(텍스트)
을 함께 생성한다. 그래프 그림과 챗봇 컨텍스트가 같은 데이터에서 나오도록 한 SSOT.

트리가 아니라 '망'이 되도록 공유 기술 노드(Docker·Streamlit·LangChain·FAISS·Groq·
PyTorch)를 여러 프로젝트가 함께 가리키게 해 교차연결을 만든다.

⚠️ 노드 설명은 keti_mlops_full_dump / 학부_코스워크_카탈로그 / SDI 실코드 / 작업가이드 §2
   가드레일 준수: KETI="온프레미스 자체호스팅(폐쇄망 대응 설계)"·"주도적 설계·구축"(단독X)
   ·"전문생산기술연구소"(정출연X)·모델은 협업 대학 제공. SDI SPA=본인 몫은 검색·분기·UI(LLM
   서빙은 멘토 주도), 임원 PoC 호평. TEBO=공저 + formal analysis·data curation·
   visualization(신호처리·분해는 연구팀 몫). 코스워크=강의 프로젝트 수준(IS327·IS477 R²
   성과화 금지). FAISS/LangChain은 SDI·JisangData만(KETI 아님).
   전 직장 성능 지표(MAE·R²)와 사내 CI 실측치는 공개 산출물에 수치로 쓰지 않는다.
   금지 표현 목록은 tests/retired_claims.py 가 소유하고 CI 가 이 파일을 대조한다.
"""
import json
import re

# group: person / edu / work / project / paper / course / skill
NODES = [
    {"id": "jjpark", "group": "person", "ko": "박지상", "en": "Jisang Park",
     "desc_ko": "온프레미스 자체호스팅 환경의 MLOps와 RAG·LLM 서빙을 맡아 온 AI 엔지니어.",
     "desc_en": "AI engineer who owns MLOps and RAG·LLM serving in self-hosted, on-prem environments."},

    # 학력
    {"id": "uiuc", "group": "edu", "ko": "UIUC", "en": "UIUC",
     "desc_ko": "Information Science + Data Science 학사 · GPA 3.89/4.0 (2025.12 졸업).",
     "desc_en": "B.S. Information Science + Data Science · GPA 3.89/4.0 (Dec 2025)."},
    {"id": "uw", "group": "edu", "ko": "UW", "en": "UW",
     "desc_ko": "University of Washington · Pre-Science · Dean's List.",
     "desc_en": "University of Washington · Pre-Science · Dean's List."},

    # 경력
    {"id": "infomax", "group": "work", "ko": "연합인포맥스", "en": "Yonhap Infomax",
     "desc_ko": "금융공학연구소 재직 중(2026.09~).",
     "desc_en": "Financial Engineering Research Institute (since Sep 2026)."},
    {"id": "keti", "group": "work", "ko": "KETI", "en": "KETI",
     "desc_ko": "AX 연구본부 위촉연구원(2026.02~2026.09) · 산업부 소관 전문생산기술연구소.",
     "desc_en": "Research engineer, AX Research Division (Feb–Sep 2026) · industrial R&D institute."},
    {"id": "sdi", "group": "work", "ko": "삼성SDI", "en": "Samsung SDI",
     "desc_ko": "DI(Data Intelligence)그룹 데이터 엔지니어 인턴(2025.06~08).",
     "desc_en": "Data Engineer Intern, DI (Data Intelligence) Group (Jun~Aug 2025)."},

    # 프로젝트
    {"id": "mlops", "group": "project", "ko": "온프레 MLOps 플랫폼", "en": "On-prem MLOps platform",
     "desc_ko": "온프레미스 자체호스팅(폐쇄망 대응 설계) MLOps 플랫폼을 docker-compose로 주도적으로 설계·구축.",
     "desc_en": "Led design & build of a self-hosted on-prem MLOps platform on docker-compose, built to hold up under closed-network constraints."},
    {"id": "imgclf", "group": "project", "ko": "이미지 분류 레일 + CCTV", "en": "Image-clf rail + CCTV",
     "desc_ko": "받은 모델을 서빙하던 것과 달리 파이프라인을 처음부터 설계. 품질 게이트가 임계치 미달 시 레지스트리 승격을 건너뛰고, 지표를 판정보다 먼저 기록해 차단 사유가 런에 남는다. 같은 코드로 CIFAR-10→EuroSAT→실 CCTV 3종 통과. 직접 등록해 서빙하던 모델의 정확도가 데이터 누수로 부풀려진 것을 스스로 규명하고 카메라 그룹 단위로 재분할하니 게이트가 승격을 실제로 차단했다(PoC · CI 연동 미완).",
     "desc_en": "Unlike serving models handed to me, this pipeline was designed from scratch. A quality gate skips registry promotion below threshold, and metrics are logged before the decision so blocked runs still record why. Same code carried CIFAR-10→EuroSAT→live CCTV. I established that a model I had registered and served myself scored high only through data leakage; re-splitting by camera group made the gate actually block promotion (PoC · not wired to CI)."},
    {"id": "rag", "group": "project", "ko": "폐쇄망 RAG (SPA)", "en": "Air-gapped RAG (SPA)",
     "desc_ko": "완전 차단망 특허검색 RAG 챗봇 — 검색·분기·UI를 맡았고 LLM 서빙 구성은 멘토 주도 → 임원 PoC 호평.",
     "desc_en": "Patent-search RAG chatbot in a fully internet-blocked env — I owned retrieval, routing and UI; LLM serving was set up by my mentor → executive PoC praised."},
    {"id": "jf", "group": "project", "ko": "JisangFolio", "en": "JisangFolio",
     "desc_ko": "이 포트폴리오 · GraphRAG·가드레일·LLM 옵저버빌리티·하이브리드 RAG·Agentic RAG·CI 실장. 회귀 평가 하니스 최근 실행 17/20 (n=20, 벤치마크가 아니라 변경 전후 게이트).",
     "desc_en": "This portfolio · GraphRAG, guardrails, LLM observability, hybrid & agentic RAG, CI. Latest regression eval run 17/20 (n=20 — a before/after gate, not a benchmark)."},
    {"id": "jd", "group": "project", "ko": "JisangData", "en": "JisangData",
     "desc_ko": "LLM 라우터가 집계 질문은 pandas 코드 생성·실행, 검색 질문은 FAISS RAG로 처리(실패 시 RAG 폴백).",
     "desc_en": "An LLM router runs pandas codegen for aggregates and FAISS RAG for search (RAG fallback on failure)."},
    {"id": "mcp", "group": "project", "ko": "MCP 서버", "en": "MCP server",
     "desc_ko": "FastMCP 서버 — 프로필·경력·프로젝트·기술·논문 조회 + ask_jisang(1인칭 Q&A) 6개 툴 노출.",
     "desc_en": "FastMCP server — 6 tools: profile/experience/projects/skills/publications + ask_jisang."},

    # 논문
    {"id": "tebo", "group": "paper", "ko": "TEBO 논문", "en": "TEBO paper",
     "desc_ko": "측정 이후 단계 기여 — 두 코호트 ID 정합화 · FES-I 집단 집계 · 시뮬레이션 stabilogram 시각화. SCIE 'Applied Sciences' 공저(2025, 10인 중 7저자). 신호 필터링·성분 분해는 연구팀 수행.",
     "desc_en": "Contributed after data collection — reconciled two cohorts' subject IDs, scored and aggregated the FES-I survey, produced simulated stabilogram visualisations. Co-author, SCIE 'Applied Sciences' (2025, 7th author). Signal filtering and decomposition were done by the research team."},

    # 학부 코스워크 (강의 프로젝트 수준 — 과대표현 금지)
    {"id": "cs307", "group": "course", "ko": "CS307 · ML", "en": "CS307 · ML",
     "desc_ko": "Models of Learning — 6개 lab로 KNN·RandomForest·GBM·캘리브레이션에서 PyTorch CNN까지(강의 프로젝트).",
     "desc_en": "Models of Learning — 6 labs from KNN·RandomForest·GBM·calibration to a PyTorch CNN (coursework)."},
    {"id": "is327", "group": "course", "ko": "IS327 · 회귀", "en": "IS327 · Regression",
     "desc_ko": "Machine Learning — 게임 판매 예측 회귀(Random Forest, 강의 프로젝트). 좋은 R²가 나왔지만 피처에 판매 구간 지표가 남아 정답이 새고 있었고, 걷어내니 0.22로 떨어졌다 — 수치가 아니라 이 규명을 근거로 쓴다.",
     "desc_en": "Machine Learning — game-sales regression with Random Forest (coursework). The R² looked strong until I found a sales-bracket feature leaking the target; with the leak removed it fell to 0.22. I cite the audit, not the number."},
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
     "desc_ko": "협업 대학이 제공한 3D U-Net을 GPU 서빙 · voxel I/O와 point I/O가 다른 외부 PINN 3종까지 같은 Triton에 통합(PINN 100점 단일 요청 22–32ms, L40S).",
     "desc_en": "Serves a partner university's 3D U-Net on GPU and unifies 3 external PINNs with different I/O on the same Triton (a 100-point PINN request in 22–32 ms on an L40S)."},
    {"id": "onnx", "group": "skill", "ko": "ONNX", "en": "ONNX",
     "desc_ko": "PyTorch 모델을 ONNX(opset 17)로 변환·검증해 Triton 서빙 포맷 확보.",
     "desc_en": "Convert/validate PyTorch models to ONNX (opset 17) for Triton serving."},
    {"id": "mlflow", "group": "skill", "ko": "MLflow 거버넌스", "en": "MLflow governance",
     "desc_ko": "실험·레지스트리·라이프사이클 태그 거버넌스 · 버전 간 지표 비교로 승격/기각 판단(과제 지표 수치는 비공개).",
     "desc_en": "Experiments, registry and lifecycle-tag governance · version-to-version metric comparison drives promote/reject (project metrics not disclosed)."},
    {"id": "ci", "group": "skill", "ko": "Gitea Actions CI", "en": "Gitea Actions CI",
     "desc_ko": "주간 학습 → 매니페스트 기준 판정 → ONNX 변환 → 체크섬 대조 배포를 워크플로 8개로 이은 CI 체인. 표준 checkout 액션이 인증에서 매달리는 문제를 raw git clone으로 대체해 해소.",
     "desc_en": "Eight workflows chaining weekly training → manifest-driven gate → ONNX export → checksum-verified deploy. Replaced the stock checkout action, which hung on auth, with a raw git clone."},
    {"id": "monitor", "group": "skill", "ko": "Prometheus·Grafana", "en": "Prometheus·Grafana",
     "desc_ko": "서빙 메트릭 7패널 대시보드 · Streamlit 운영 포털 · Evidently 드리프트(PoC).",
     "desc_en": "7-panel serving dashboard · Streamlit ops portal · Evidently drift (PoC)."},
    {"id": "docker", "group": "skill", "ko": "Docker·Compose", "en": "Docker·Compose",
     "desc_ko": "다중 컨테이너 운영 — KETI 자체호스팅 스택과 SDI 폐쇄망 환경 양쪽에서 사용.",
     "desc_en": "Multi-container ops — used across KETI's self-hosted stack and SDI's air-gapped env."},
    {"id": "pytorch", "group": "skill", "ko": "PyTorch", "en": "PyTorch",
     "desc_ko": "협업 대학이 제공한 서빙 모델(→ONNX 변환)과 CS307 CNN 실습의 프레임워크.",
     "desc_en": "Framework for the partner university's serving model (→ONNX) and the CS307 CNN lab."},
    {"id": "ollama", "group": "skill", "ko": "Ollama·Qwen2.5", "en": "Ollama·Qwen2.5",
     "desc_ko": "SPA가 올라간 온프레미스 LLM 런타임(Qwen2.5-72B) — SDI 폐쇄망. 서빙 구성은 멘토 주도이고 본인은 그 위의 검색·분기·UI를 맡았다.",
     "desc_en": "The on-prem LLM runtime SPA ran on (Qwen2.5-72B) in SDI's air-gapped env. My mentor set the serving up; I built retrieval, routing and the UI on top."},
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
     "desc_ko": "'그래프/통계/출원' 키워드를 감지하면 차트를 원본 DataFrame 집계로 직접 만들고, LLM에는 그 질의에 답하지 말라고 지시한다(SDI). 침묵이 프롬프트 지시라 구조적 보장은 아니었다 — 코드는 모든 질의에 LLM을 호출한다.",
     "desc_en": "On 'chart/stats/filing' keywords the chart is computed straight from the DataFrame and the LLM is told not to answer that query (SDI). The silence is a prompt instruction, not a structural guarantee — the code calls the LLM on every query."},
    {"id": "eval", "group": "skill", "ko": "LLM eval 하니스", "en": "LLM eval harness",
     "desc_ko": "규칙 채점 + 별도 모델 LLM-judge로 답변 사실성 회귀 검증.",
     "desc_en": "Rule scoring + a separate LLM judge for factual regression."},
    {"id": "mpl", "group": "skill", "ko": "Matplotlib 도식화", "en": "Matplotlib figures",
     "desc_ko": "TEBO에서 랩이 전달한 대역별 파워로 스케일한 시뮬레이션 stabilogram을 EPS 벡터로 그림 · 설문 집단 집계 도식화. 실측 궤적이 아니고, 게재 논문에도 stabilogram은 없다.",
     "desc_en": "Rendered TEBO stabilograms as vector EPS — simulated trajectories scaled to the lab's band-power metrics, not measured sway — and visualised the survey group aggregates. The published paper contains no stabilogram."},
    {"id": "sql", "group": "skill", "ko": "SQL", "en": "SQL",
     "desc_ko": "T-SQL 복합 JOIN·CTE·저장 프로시저·스키마 정규화(INFO330).",
     "desc_en": "T-SQL complex JOINs·CTEs·stored procedures·normalization (INFO330)."},

    # JisangFolio LLMOps 스택 (본 사이트 실장)
    {"id": "graphrag", "group": "skill", "ko": "GraphRAG", "en": "GraphRAG",
     "desc_ko": "질문마다 이 프로필 그래프에서 관련 서브그래프(시드+이웃)를 탐색해 챗봇 근거로 주입.",
     "desc_en": "Each question retrieves a relevant subgraph (seeds + neighbors) from this profile graph as chatbot grounding."},
    {"id": "guardrails", "group": "skill", "ko": "Guardrails", "en": "Guardrails",
     "desc_ko": "프롬프트 인젝션·과길이·빈 입력을 LLM 앞단에서 정규식으로 차단(카테고리 3종). 주제 이탈은 코드가 아니라 페르소나 프롬프트가 맡는다.",
     "desc_en": "A regex pre-filter blocks prompt injection, over-length and empty input before the LLM (three categories). Off-topic scope is handled by the persona prompt, not by code."},
    {"id": "observability", "group": "skill", "ko": "LLM Observability", "en": "LLM Observability",
     "desc_ko": "챗·데이터 매 턴을 트레이싱(지연·모델·라우팅·가드결과) — Langfuse/Phoenix 개념 인하우스 대시보드.",
     "desc_en": "Every chat/data turn is traced (latency·model·routing·guard verdict) — a Langfuse/Phoenix-style in-house dashboard."},
    {"id": "hybrid", "group": "skill", "ko": "Hybrid RAG", "en": "Hybrid RAG",
     "desc_ko": "FAISS(dense) + BM25(sparse)를 Reciprocal Rank Fusion으로 융합 — JisangData·MLOps Docs 검색 경로.",
     "desc_en": "FAISS (dense) + BM25 (sparse) fused with Reciprocal Rank Fusion — JisangData & MLOps Docs search path."},
    {"id": "agenticrag", "group": "skill", "ko": "Agentic RAG", "en": "Agentic RAG",
     "desc_ko": "MLOps 문서 코퍼스(클라우드 4사+온프레 KETI)에 대한 자기교정 루프 — 검색→관련성 평가→쿼리 재작성·재검색→근거 인용→근거 자기점검. 코퍼스 밖 질문 거절, 골든셋 회귀 평가(통과율은 evals/report.md에 실행마다 기록).",
     "desc_en": "A self-correcting loop over an MLOps docs corpus (4 clouds + on-prem KETI) — retrieve→grade→rewrite & re-retrieve→cite→self-check groundedness. Refuses out-of-corpus questions; golden-set regression (pass rates recorded per run in evals/report.md)."},
    {"id": "codeguard", "group": "skill", "ko": "코드 실행 가드", "en": "Code execution guard",
     "desc_ko": "LLM이 생성한 pandas 코드를 축소 권한 네임스페이스에서 실행 — pandas 모듈 대신 facade(모듈 객체는 allowlist 우회 통로), AST로 import·dunder·속성쓰기·상한없는 range 차단, 쓰기계열은 denylist가 아니라 allowlist. 뚫렸던 우회 3건은 회귀 테스트로 고정. 샌드박스가 아님을 문서에 명시.",
     "desc_en": "Runs LLM-generated pandas in a reduced-capability namespace — a facade instead of the pandas module (a module object is a way out of any allowlist), an AST pass rejecting imports, dunders, attribute writes and unbounded range(), and an allowlist (not a denylist) for writers. Three escapes that once worked are pinned as regression tests. Documented as not a sandbox."},
    {"id": "ghci", "group": "skill", "ko": "CI 회귀 게이트", "en": "CI regression gates",
     "desc_ko": "GitHub Actions + pytest 스위트를 Python 3.11·3.12 매트릭스로 실행. 코드뿐 아니라 문서의 진실성까지 게이트 — 코드그래프 스테일 검사, 골든셋 개수 대 문서 대조, MCP 사본 드리프트, README 배지 대 실제 요구 버전. CI는 키 없이 도는 LLM-free 레이어만 검증한다는 범위도 명시.",
     "desc_en": "GitHub Actions + a pytest suite on a Python 3.11/3.12 matrix. The gates cover documentation truthfulness, not just code — code-graph staleness, golden-set count vs docs, MCP copy drift, README badge vs the version the code actually needs. Scope is stated honestly: CI exercises the LLM-free layers only, so it runs fast and key-free."},
    {"id": "probe", "group": "skill", "ko": "검색 자기진단", "en": "Retrieval self-diagnosis",
     "desc_ko": "검색 품질을 주장하는 대신 결함을 측정. 인코더(all-MiniLM-L6-v2, 256 word-piece)가 긴 청크를 잘라내는 문제를 계량 — 한국어 절단률 65.6%, 영어 0%. 코퍼스 편중(한 문서 89%)을 바로잡자 교차언어 검색 점수가 4/5→2/5로 내려갔고, 그 2/5가 정직한 값이며 해법은 튜닝이 아니라 다국어 인코더라는 결론까지 기록.",
     "desc_en": "Measures the retrieval layer's own defects instead of asserting quality. It quantified the encoder (all-MiniLM-L6-v2, 256 word-pieces) silently truncating long chunks — 65.6% of Korean chunks, 0% of English. After rebalancing a corpus one document had dominated (~89%), the cross-lingual score fell 4/5 → 2/5; 2/5 is the honest read, and the recorded conclusion is that a multilingual encoder is the fix, not more tuning."},
]

EDGES = [
    # 뿌리
    ("jjpark", "uiuc"), ("jjpark", "uw"), ("jjpark", "infomax"), ("jjpark", "keti"), ("jjpark", "sdi"),
    ("jjpark", "jf"), ("jjpark", "jd"), ("jjpark", "mcp"),
    # 학력 → 코스워크·논문
    ("uiuc", "cs307"), ("uiuc", "is327"), ("uiuc", "is477"), ("uiuc", "is467"),
    ("uiuc", "tebo"),
    ("uw", "cse160"), ("uw", "info330"),
    # 경력 → 프로젝트
    ("keti", "mlops"), ("sdi", "rag"),
    ("keti", "imgclf"),         # 도시냉각 과제와 별개인 자발 트랙
    ("imgclf", "mlflow"),       # 게이트 통과분만 레지스트리로 승격
    ("imgclf", "onnx"),         # 학습 끝 → ONNX 내보내기 + Triton config 스텁
    ("imgclf", "pytorch"),      # resnet18 파인튜닝
    ("imgclf", "eval"),         # "지표로 승격을 막는다" — 평가가 게이트라는 같은 발상
    # MLOps 플랫폼 → 기술
    ("mlops", "triton"), ("mlops", "onnx"), ("mlops", "mlflow"), ("mlops", "ci"),
    ("mlops", "monitor"), ("mlops", "docker"), ("mlops", "pytorch"),
    # RAG → 기술
    ("rag", "ollama"), ("rag", "langchain"), ("rag", "faiss"), ("rag", "ruleagent"),
    ("rag", "docker"), ("rag", "streamlit"),
    # 개인 프로젝트 → 기술 (공유 노드로 교차연결)
    ("jf", "eval"), ("jf", "groq"), ("jf", "streamlit"),
    ("jf", "graphrag"), ("jf", "guardrails"), ("jf", "observability"),
    ("jf", "agenticrag"), ("jf", "codeguard"), ("jf", "ghci"), ("jf", "probe"),
    # 자기진단은 검색 스택을 겨눈다 — 결함을 잰 대상이 곧 하이브리드 검색이다
    ("probe", "hybrid"), ("probe", "faiss"), ("probe", "agenticrag"),
    # 실행 가드는 데이터분석 경로(JisangData)의 코드 생성에 걸린다
    ("codeguard", "jd"),
    # CI 게이트는 평가 하니스와 짝을 이룬다(빠른 결정적 검증 ↔ 느린 LLM 평가)
    ("ghci", "eval"),
    # Agentic RAG → 기술 (교차연결: 코퍼스에 온프레 MLOps 파이프라인 포함)
    ("agenticrag", "hybrid"), ("agenticrag", "faiss"), ("agenticrag", "langchain"),
    ("agenticrag", "groq"), ("agenticrag", "eval"), ("agenticrag", "mlops"),
    ("jd", "langchain"), ("jd", "faiss"), ("jd", "groq"), ("jd", "streamlit"),
    ("jd", "hybrid"), ("jd", "observability"),
    ("mcp", "groq"),
    # LLMOps 스택 내부 교차연결 (망 형성)
    ("hybrid", "faiss"), ("observability", "streamlit"),
    # 논문·코스워크 → 기술 (교차연결)
    ("tebo", "mpl"), ("cs307", "pytorch"), ("info330", "sql"),

    # ── 망 형성 (2026-07-29) ─────────────────────────────────────────
    # 여기까지의 그래프는 사실상 **스타/트리**였다: 기술 노드 15개가 차수 1이라
    # 프로젝트 하나에만 매달려 있었고, person 노드를 빼면 UW 코스워크 덩어리가
    # 통째로 떨어져 나갔다. GraphRAG 가 seed 에서 1-hop 을 도는 구조라 이건 보기
    # 문제가 아니라 **검색 품질 문제**다 — 이웃이 부모 하나뿐이면 '집중 근거'가
    # 사실상 부모 노드 하나로 수렴한다.
    # 아래 엣지는 전부 이력서·리포에 근거가 있는 실제 관계만 넣는다(장식용 금지).

    # MLOps 파이프라인 내부 — 도구들이 실제로 물려 있는 순서
    ("pytorch", "onnx"),        # 협업 대학이 제공한 PyTorch → ONNX 변환 경로 확보
    ("onnx", "triton"),         # 변환·검증된 ONNX를 Triton으로 서빙
    ("mlflow", "triton"),       # Registry 모델을 Triton에 로드(운영 포털 워크플로우)
    ("monitor", "triton"),      # Prometheus가 Triton 메트릭 수집 → Grafana 7패널
    ("ci", "onnx"),             # 푸시·PR 시 ONNX 검증 → 배포 자동화
    ("ci", "mlflow"),           # 배포 시 MLflow 거버넌스 태그 자동 갱신
    ("docker", "monitor"),      # docker-compose로 모니터링 스택까지 단일 서버 통합
    ("mlops", "streamlit"),     # Streamlit MLOps 운영 포털 6페이지

    # 폐쇄망 RAG 내부, 그리고 그 아이디어의 다음 세대
    ("ollama", "langchain"),    # LangChain + 온프레 sLLM(Qwen2.5-72B)
    ("ruleagent", "jd"),        # "수치는 누가 만드나" — SPA의 키워드 분기가
                                # JisangData의 LLM 라우터로 이어지는 계보

    # LLMOps 스택 내부 — 오늘 실제로 생긴 연결 포함
    ("graphrag", "eval"),       # 하니스가 GraphRAG 주입 프롬프트까지 평가(조립 공유)
    ("guardrails", "eval"),     # 골든셋에 인젝션 케이스가 들어 있다
    ("guardrails", "codeguard"),# 입력 가드 + 실행 가드 = 2층 방어
    ("guardrails", "observability"),  # 트레이스에 guard 판정을 남긴다
    ("ghci", "codeguard"),      # 뚫렸던 우회 3건을 CI가 매 푸시 재현
    ("ghci", "graphrag"),       # 검색 회귀 테스트도 CI 게이트
    ("probe", "eval"),          # 둘 다 '주장 대신 측정' 계층
    ("mcp", "jf"),              # MCP 서버가 같은 이력서를 도구로 노출

    # UW 코스워크를 본체에 잇는다 — person 허브 없이도 연결되게
    ("cse160", "cs307"),        # 라이브러리 없이 직접 구현(UW) → 프레임워크로 확장(UIUC)
    ("cse160", "graphrag"),     # NetworkX 없이 짠 그래프 탐색 → 프로필 서브그래프 탐색
    ("is477", "sql"),           # ETL 과제의 관계형 모델링 ↔ INFO330 DB
    ("is327", "cs307"),         # 회귀(RF) ↔ 분류·CNN, 같은 ML 코스워크 계보
    ("tebo", "is327"),          # 설문·집단 집계 ↔ 회귀 모델링 코스워크 — 같은 시기의
                                # 같은 종류(표 만들고 모델 돌리는) 데이터 분석 계보
    ("is467", "guardrails"),    # 채용 AI 편향·EU AI Act 연구 → 책임 있는 AI 가드레일
]


# ── 엣지 이름 (2026-09-30) ────────────────────────────────────────
# 엣지가 92개인데 전부 무명이라, 그래프는 "무엇이 무엇과 이어졌나"는 보여주고
# **"어떤 관계인가"는 못 보여줬다.** 관계 근거는 위 EDGES 의 주석에만 있었고 그건
# 화면에 안 나간다. 아래 라벨이 그 주석을 화면으로 끌어올린다.
#
# 라벨을 EDGES 3-튜플로 합치지 않은 이유: `for a, b in EDGES` 로 EDGES 를 도는
# 코드가 to_prompt_text·graph_retrieve·테스트까지 네 군데다. 튜플 폭을 늘리면
# 그 전부가 조용히 깨진다(언패킹 에러는 조용하지 않지만, 라벨을 노드 id 로 착각해
# 도는 쪽은 조용하다). 별 dict 로 두고 아래 test 가 누락을 잡게 한다.
EDGE_LABEL = {
    # 뿌리
    ("jjpark", "uiuc"): ("학사 졸업", "B.S."),
    ("jjpark", "uw"): ("편입 전", "before transfer"),
    ("jjpark", "infomax"): ("현 재직", "current role"),
    ("jjpark", "keti"): ("전 재직", "former role"),
    ("jjpark", "sdi"): ("인턴", "internship"),
    ("jjpark", "jf"): ("직접 제작", "built it"),
    ("jjpark", "jd"): ("직접 제작", "built it"),
    ("jjpark", "mcp"): ("직접 제작", "built it"),
    # 학력 → 코스워크·논문
    ("uiuc", "cs307"): ("이수", "took"),
    ("uiuc", "is327"): ("이수", "took"),
    ("uiuc", "is477"): ("이수", "took"),
    ("uiuc", "is467"): ("이수", "took"),
    ("uiuc", "tebo"): ("학부 연구생", "undergrad researcher"),
    ("uw", "cse160"): ("이수", "took"),
    ("uw", "info330"): ("이수", "took"),
    # 경력 → 프로젝트
    ("keti", "mlops"): ("배정 과제", "assigned project"),
    ("keti", "imgclf"): ("자발 과제", "self-initiated"),
    ("sdi", "rag"): ("배정 과제", "assigned project"),
    # 이미지 레일
    ("imgclf", "mlflow"): ("게이트 통과분만 등록", "register only if gated"),
    ("imgclf", "onnx"): ("학습 후 내보내기", "export after training"),
    ("imgclf", "pytorch"): ("resnet18 파인튜닝", "resnet18 fine-tune"),
    ("imgclf", "eval"): ("지표가 곧 게이트", "metric as the gate"),
    # MLOps 플랫폼 → 기술
    ("mlops", "triton"): ("모델 서빙", "serves models"),
    ("mlops", "onnx"): ("서빙 포맷", "serving format"),
    ("mlops", "mlflow"): ("실험·레지스트리", "experiments & registry"),
    ("mlops", "ci"): ("배포 자동화", "deploy automation"),
    ("mlops", "monitor"): ("운영 관측", "observability"),
    ("mlops", "docker"): ("단일 서버 통합", "one-server stack"),
    ("mlops", "pytorch"): ("수령 모델", "model received"),
    ("mlops", "streamlit"): ("운영 포털", "ops portal"),
    # RAG → 기술
    ("rag", "ollama"): ("LLM 런타임", "LLM runtime"),
    ("rag", "langchain"): ("오케스트레이션", "orchestration"),
    ("rag", "faiss"): ("벡터 검색", "vector search"),
    ("rag", "ruleagent"): ("키워드 분기", "keyword branch"),
    ("rag", "docker"): ("컨테이너 배포", "containerised"),
    ("rag", "streamlit"): ("UI", "UI"),
    # JisangFolio → LLMOps 스택
    ("jf", "eval"): ("회귀 게이트", "regression gate"),
    ("jf", "groq"): ("추론", "inference"),
    ("jf", "streamlit"): ("UI", "UI"),
    ("jf", "graphrag"): ("근거 검색", "grounding retrieval"),
    ("jf", "guardrails"): ("입력 가드", "input guard"),
    ("jf", "observability"): ("턴 트레이싱", "per-turn tracing"),
    ("jf", "agenticrag"): ("문서 Q&A", "docs Q&A"),
    ("jf", "codeguard"): ("실행 가드", "execution guard"),
    ("jf", "ghci"): ("CI 게이트", "CI gates"),
    ("jf", "probe"): ("검색 자기진단", "retrieval self-diagnosis"),
    ("probe", "hybrid"): ("측정 대상", "what it measured"),
    ("probe", "faiss"): ("절단률 계량", "quantified truncation"),
    ("probe", "agenticrag"): ("코퍼스 편중 규명", "found corpus skew"),
    ("codeguard", "jd"): ("생성 코드 실행", "runs generated code"),
    ("ghci", "eval"): ("빠른 결정적 층", "fast deterministic layer"),
    ("agenticrag", "hybrid"): ("검색 융합", "fused retrieval"),
    ("agenticrag", "faiss"): ("dense 절반", "the dense half"),
    ("agenticrag", "langchain"): ("루프 배선", "loop wiring"),
    ("agenticrag", "groq"): ("생성·평가", "generate & grade"),
    ("agenticrag", "eval"): ("근거 충실성 평가", "groundedness eval"),
    ("agenticrag", "mlops"): ("코퍼스에 포함", "part of the corpus"),
    ("jd", "langchain"): ("오케스트레이션", "orchestration"),
    ("jd", "faiss"): ("벡터 검색", "vector search"),
    ("jd", "groq"): ("라우팅·생성", "routing & generation"),
    ("jd", "streamlit"): ("UI", "UI"),
    ("jd", "hybrid"): ("BM25+dense", "BM25+dense"),
    ("jd", "observability"): ("턴 트레이싱", "per-turn tracing"),
    ("mcp", "groq"): ("ask_jisang", "ask_jisang"),
    ("hybrid", "faiss"): ("dense 절반", "the dense half"),
    ("observability", "streamlit"): ("대시보드", "dashboard"),
    # 논문·코스워크 → 기술
    ("tebo", "mpl"): ("시뮬레이션 stabilogram", "simulated stabilograms"),
    ("cs307", "pytorch"): ("CNN lab", "CNN lab"),
    ("info330", "sql"): ("T-SQL", "T-SQL"),
    # MLOps 파이프라인 내부 순서
    ("pytorch", "onnx"): ("변환 경로", "conversion path"),
    ("onnx", "triton"): ("검증 후 로드", "validated, then loaded"),
    ("mlflow", "triton"): ("레지스트리 → 서빙", "registry → serving"),
    ("monitor", "triton"): ("메트릭 수집", "scrapes metrics"),
    ("ci", "onnx"): ("변환·검증", "convert & validate"),
    ("ci", "mlflow"): ("거버넌스 갱신", "updates governance"),
    ("docker", "monitor"): ("같은 compose", "same compose stack"),
    # SPA 내부와 그 계보
    ("ollama", "langchain"): ("체인 백엔드", "chain backend"),
    ("ruleagent", "jd"): ("라우터의 계보", "the router's lineage"),
    # LLMOps 스택 내부
    ("graphrag", "eval"): ("주입 프롬프트까지 평가", "evaluates the injected prompt"),
    ("guardrails", "eval"): ("인젝션 케이스", "injection cases"),
    ("guardrails", "codeguard"): ("2층 방어", "two-layer defence"),
    ("guardrails", "observability"): ("판정 기록", "verdict logged"),
    ("ghci", "codeguard"): ("우회 3건 재현", "replays 3 escapes"),
    ("ghci", "graphrag"): ("검색 회귀", "retrieval regression"),
    ("probe", "eval"): ("주장 대신 측정", "measure, don't claim"),
    ("mcp", "jf"): ("같은 이력서 노출", "exposes the same resume"),
    # 코스워크를 본체에 잇는 엣지
    ("cse160", "cs307"): ("직접구현 → 프레임워크", "scratch → framework"),
    ("cse160", "graphrag"): ("그래프 탐색 계보", "graph-traversal lineage"),
    ("is477", "sql"): ("관계형 모델링", "relational modelling"),
    ("is327", "cs307"): ("회귀 ↔ 분류", "regression ↔ classification"),
    ("tebo", "is327"): ("데이터 분석 계보", "data-analysis lineage"),
    ("is467", "guardrails"): ("편향 연구 → 가드레일", "bias study → guardrails"),
}

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


# 캔버스 높이는 여기 하나로 둔다. jisangfolio.py 의 components.html(height=...) 이
# 이 값보다 작으면 **그래프 아래쪽이 잘린다** — 실제로 680 캔버스를 580 iframe 에
# 넣어 100px 이 잘려 있었다. tests/test_profile_graph.py 가 둘을 대조한다.
NET_HEIGHT = 780
LEGEND_HEIGHT = 34
EMBED_HEIGHT = NET_HEIGHT + LEGEND_HEIGHT

_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  html, body { margin:0; padding:0; background:transparent; overflow:hidden; }
  #net { width:100%; height:__NET_HEIGHT__px; }
</style></head>
<body>
__LEGEND__
<div id="net"></div>
<script>
  const nodes = new vis.DataSet(__NODES__);
  const edges = new vis.DataSet(__EDGES__);
  // 엣지 이름은 **항상** 띄운다. 다만 92개가 같은 밝기로 떠 있으면 글자 죽이
  // 되므로 기본은 흐리게 두고, 노드에 마우스를 올리거나 클릭하면 그 노드에 걸린
  // 관계만 밝고 크게 끌어올린다(나머지는 그대로 흐리게 남는다).
  const LABELS = __EDGE_LABELS__;
  const ALL_IDS = Object.keys(LABELS);
  const DIM   = { size: 9,  color: '#79818F', strokeWidth: 4, strokeColor: '#0E1117' };
  const FOCUS = { size: 11, color: '#E8EBF0', strokeWidth: 6, strokeColor: '#0E1117' };

  const options = {
    // drawThreshold: vis 는 fontSize * 배율이 이 값보다 작으면 라벨을 **통째로 안 그린다**
    // (기본 5). fit() 으로 축소되면 노드 이름이 전부 사라지는 원인이었다.
    nodes: { borderWidth: 0, shadow: false, font: { face: 'Pretendard, sans-serif' },
             scaling: { label: { drawThreshold: 1 } } },
    edges: { color: { color: 'rgba(180,190,210,0.22)', highlight: '#7AA2F7', hover: '#7AA2F7' },
             smooth: { type: 'continuous' }, width: 1.1, hoverWidth: 0.8,
             // strokeWidth 로 배경을 깔지 않으면 선 위에서 글자가 안 읽힌다.
             font: { size: 9, color: '#79818F', strokeWidth: 4, strokeColor: '#0E1117',
                     face: 'Pretendard, sans-serif', align: 'horizontal' },
             // drawThreshold 를 안 내리면 축소 배율에서 선 이름이 통째로 사라진다.
             scaling: { label: { drawThreshold: 1 } } },
    physics: { barnesHut: { gravitationalConstant: -13000, centralGravity: 0.33,
                            springLength: 145, springConstant: 0.045, avoidOverlap: 0.32 },
               stabilization: { iterations: 400 } },
    interaction: { hover: true, tooltipDelay: 80, zoomView: true, dragView: true,
                   hoverConnectedEdges: true, navigationButtons: false }
  };
  const network = new vis.Network(document.getElementById('net'), { nodes, edges }, options);

  function focusOn(nodeId) {
    const on = new Set(network.getConnectedEdges(nodeId));
    edges.update(ALL_IDS.map(id => ({ id: id, font: on.has(id) ? FOCUS : DIM })));
  }
  function resetFocus() {
    edges.update(ALL_IDS.map(id => ({ id: id, font: DIM })));
  }
  network.on('hoverNode', p => focusOn(p.node));
  network.on('blurNode', () => { if (network.getSelectedNodes().length === 0) resetFocus(); });
  network.on('selectNode', p => focusOn(p.nodes[0]));
  network.on('deselectNode', resetFocus);

  network.once('stabilizationIterationsDone', function () {
    network.setOptions({ physics: false });
    fitInView();
  });
  // fit() 이 없으면 바깥쪽 노드가 캔버스 밖으로 나가 라벨이 잘린다. 다만 너무 크게
  // 확대되면 그래프가 화면을 뚫으므로 배율 상한을 둔다.
  function fitInView() {
    network.fit({ animation: false });
    const s = network.getScale();
    if (s > 1.15) network.moveTo({ scale: 1.15 });
  }
  window.addEventListener('resize', fitInView);
</script>
</body></html>"""


def normalize_lang(lang):
    """언어 토큰을 앱 내부 표기('한국어'/'English')로 통일한다.

    앱은 '한국어'/'English' 를 쓰는데 evals/golden_*.jsonl 은 'ko'/'en' 을 쓴다.
    두 표기가 `lang == "한국어"` 비교 하나로 만나면서, 평가 하니스가 한국어 케이스
    15건을 **영어 프롬프트로 돌린 뒤 한국어 키워드로 채점**하고 있었다. 조용히
    영어로 새는 종류의 버그라 호출자마다 고치는 대신 공유 모듈 입구에서 흡수한다.
    """
    return "한국어" if str(lang).strip().lower() in ("한국어", "ko", "kor", "korean") else "English"


def to_vis_html(lang="한국어"):
    """홈에 임베드할 인터랙티브 프로필 그래프 HTML을 반환한다."""
    ko = (normalize_lang(lang) == "한국어")
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
    vis_edges, edge_labels = [], {}
    for i, (a, b) in enumerate(EDGES):
        eid = f"e{i}"
        lab = EDGE_LABEL.get((a, b))
        text = (lab[0] if ko else lab[1]) if lab else ""
        # label(선 위 글자)과 title(툴팁) 둘 다 단다. 상시 노출이 기본이고,
        # 겹침은 밝기 차이(DIM/FOCUS)와 캔버스 높이로 푼다.
        vis_edges.append({"id": eid, "from": a, "to": b, "label": text, "title": text})
        edge_labels[eid] = text
    # 정규화한 값을 넘긴다. 노드 쪽만 normalize_lang 을 거치고 범례에 raw 를 넘기던 탓에
    # to_vis_html("ko") 가 LEGEND_LABELS 조회에서 KeyError 로 죽었다 — 형제 함수
    # graph_retrieve 는 'ko' 를 받도록 테스트까지 있는데 이쪽만 안 받았다.
    html = _HTML_TEMPLATE.replace("__LEGEND__", _legend_html("한국어" if ko else "English"))
    html = html.replace("__NODES__", json.dumps(vis_nodes, ensure_ascii=False))
    html = html.replace("__EDGES__", json.dumps(vis_edges, ensure_ascii=False))
    html = html.replace("__EDGE_LABELS__", json.dumps(edge_labels, ensure_ascii=False))
    html = html.replace("__NET_HEIGHT__", str(NET_HEIGHT))
    return html


def to_prompt_text(lang="한국어"):
    """챗봇 시스템 프롬프트에 주입할 구조 요약(들여쓰기 아웃라인)을 반환한다.

    공유 노드(여러 부모)가 있어 DAG이므로, 이미 펼친 노드는 다시 펼치지 않도록
    seen 으로 스패닝 트리를 만든다(중복·순환 방지).
    """
    ko = (normalize_lang(lang) == "한국어")
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


# ── GraphRAG: 프로필 그래프 위의 검색·탐색 ──────────────────────────
# 한글과 영숫자를 **따로** 끊는다. 하나의 문자클래스로 묶으면 "KETI에서" 가 통째로
# 한 토큰이 되어 "keti" 와 안 맞는다 — 조사가 어간에 붙어버려서, 홈에 걸린 한국어
# 샘플 질문 5개 중 4개가 seed 0개였다(영어는 멀쩡해서 안 보였다).
_TOKEN = re.compile(r"[a-z0-9]+|[가-힣]+")

# 노드 1/4 이상에 나오는 토큰은 seed 를 가르지 못한다. 조사를 손으로 열거하는 대신
# 그래프 자체에서 문서빈도를 뽑아 거른다 — 노드가 늘어도 따라 움직인다.
# ("삼성SDI에서" 는 위 정규식에서 ['삼성','sdi','에서'] 로 끊기므로 '에서' 는 실제로
#  많은 노드 설명에 등장한다. 그래서 df 만으로 걸러진다.)
_STOP_DF_RATIO = 0.25
_DF = None
_ADJ = None
_LABEL_TOKENS = None

# seed 로 인정할 최소 점수. 1점은 **설명에 한 번 스친** 것뿐이라 변별력이 없다.
# 이게 없으면 "RAG 파이프라인은?" 처럼 변별 토큰이 df 컷에 걸린 질문에서 남은
# 조사성 토큰('파이프라인은')이 엉뚱한 노드를 seed 로 올려, 틀린 서브그래프가
# '집중 근거'라는 라벨을 달고 시스템 프롬프트에 들어갔다. 근거 없음(무해) 쪽이 낫다.
_MIN_SEED_SCORE = 2


def _tokens(s):
    return set(_TOKEN.findall(s.lower()))


def _node_text(n, labels_only=False):
    if labels_only:
        return " ".join([n["ko"], n["en"]])
    return " ".join([n["ko"], n["en"], n["desc_ko"], n["desc_en"]])


def _doc_freq():
    global _DF
    if _DF is None:
        df = {}
        for n in NODES:
            for t in _tokens(_node_text(n)):
                df[t] = df.get(t, 0) + 1
        _DF = df
    return _DF


def _label_tokens():
    """어느 노드든 **라벨**에 등장하는 토큰의 합집합.

    df 컷의 사각지대를 메운다. 포트폴리오의 중심 주제일수록 여러 노드 설명에
    등장해 df 가 높아지고, 그래서 '가장 중요한 단어가 먼저 버려지는' 역설이 생긴다.
    실제로 `rag` 는 df 가 정확히 cap(9)이라 탈락했고, "RAG 경험을 말해주세요" 가
    seed 0개였다 — 이 리포의 간판 주제인데. 라벨에 있는 토큰은 조사·불용어가 아니라
    고유명사·기술명이므로, df 가 높아도 변별 토큰으로 살려둔다.
    """
    global _LABEL_TOKENS
    if _LABEL_TOKENS is None:
        toks = set()
        for n in NODES:
            toks |= _tokens(_node_text(n, labels_only=True))
        _LABEL_TOKENS = toks
    return _LABEL_TOKENS


def _query_tokens(query):
    """질문에서 변별력 있는 토큰만 남긴다.

    - 1글자 제거: '5' 가 'Qwen2.5' 의 '5' 와 붙고 '후' 가 아무 데나 붙었다.
    - 흔한 토큰 제거: 위 df 컷. 단 **노드 라벨에 있는 토큰은 예외**(_label_tokens 참고).
    """
    df = _doc_freq()
    labels = _label_tokens()
    cap = max(2, int(len(NODES) * _STOP_DF_RATIO))
    return {t for t in _tokens(query or "")
            if len(t) >= 2 and (df.get(t, 0) < cap or t in labels)}


def _is_hangul(t):
    return "가" <= t[0] <= "힣"


def _overlap(q_tokens, node_tokens):
    """질문 토큰 ∩ 노드 토큰. 한글만 접두 일치까지 인정한다(조사가 붙으므로).

    영숫자는 정규식이 이미 깔끔하게 끊으므로 정확일치로 충분하다. 한글은
    '연구를' ↔ '연구' 처럼 조사가 붙은 형태를 어간과 이어줘야 한다.
    """
    hits = 0
    for q in q_tokens:
        if q in node_tokens:
            hits += 1
        elif _is_hangul(q) and any(
                _is_hangul(n) and len(n) >= 2 and (n.startswith(q) or q.startswith(n))
                for n in node_tokens):
            hits += 1
    return hits


def _adjacency():
    global _ADJ
    if _ADJ is None:
        adj = {}
        for a, b in EDGES:
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
        _ADJ = adj
    return _ADJ


def graph_retrieve(query, lang="English", max_seeds=3, hops=1):
    """GraphRAG: 질문과 어휘가 겹치는 노드를 seed로 뽑고 이웃(hops)까지 탐색해 서브그래프를 만든다.

    반환: {"seeds": [labels], "nodes": [labels], "context": str}
    전체 이력서가 이미 프롬프트에 있어도, 관련 서브그래프를 '집중 근거'로 함께 주입한다.
    """
    ko = (normalize_lang(lang) == "한국어")
    q = _query_tokens(query)
    if not q:
        return {"seeds": [], "nodes": [], "context": ""}

    def score(n):
        # 라벨 일치는 설명 일치보다 훨씬 강한 신호다. 가중치가 없으면 전부 1점이라
        # 'KETI' 질문에서 KETI 노드와, 설명에 KETI 를 스치기만 한 노드가 동점이 됐다.
        return (3 * _overlap(q, _tokens(_node_text(n, labels_only=True)))
                + _overlap(q, _tokens(_node_text(n))))

    ranked = sorted(NODES, key=score, reverse=True)
    # person 노드(중심 허브)는 seed에서 제외 — 검색을 구체적 경험/기술에 집중
    seeds = [n for n in ranked
             if score(n) >= _MIN_SEED_SCORE and n["group"] != "person"][:max_seeds]
    if not seeds:
        return {"seeds": [], "nodes": [], "context": ""}

    adj = _adjacency()
    selected = {n["id"] for n in seeds}
    frontier = set(selected)
    for _ in range(hops):
        nxt = set()
        for nid in frontier:
            nxt |= adj.get(nid, set())
        selected |= nxt
        frontier = nxt

    by_id = {n["id"]: n for n in NODES}
    def lab(nid):
        return by_id[nid]["ko"] if ko else by_id[nid]["en"]
    def desc(nid):
        return by_id[nid]["desc_ko"] if ko else by_id[nid]["desc_en"]

    node_lines = [f"- {lab(nid)}: {desc(nid)}" for nid in selected]
    # 관계 **이름**까지 넣는다. 예전엔 "A → B" 만 줘서, 챗봇은 둘이 이어져 있다는 건
    # 알아도 *어떤 관계인지*는 몰랐다(그래프 그림에는 그 이름이 떠 있는데 프롬프트에만
    # 없어서, 화면과 답변이 다른 것을 아는 상태였다).
    def rel(a, b):
        arrow = f"{lab(a)} → {lab(b)}"
        name = EDGE_LABEL.get((a, b))
        return f"{arrow} ({name[0] if ko else name[1]})" if name else arrow
    rels = [rel(a, b) for a, b in EDGES if a in selected and b in selected]
    head_n = "관련 노드" if ko else "Relevant nodes"
    head_r = "관계" if ko else "Relationships"
    context = f"[{head_n}]\n" + "\n".join(node_lines) + f"\n[{head_r}]\n" + " · ".join(rels)
    return {
        "seeds": [lab(n["id"]) for n in seeds],
        "nodes": [lab(nid) for nid in selected],
        "context": context,
    }
