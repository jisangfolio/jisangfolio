"""GraphRAG 검색 회귀 테스트.

주의: 이 파일은 한 번 한국어를 놓쳤다. `test_bilingual` 이 "삼성SDI RAG 챗봇" —
**조사가 없는** 질문 — 을 써서, 토크나이저가 조사를 어간에 붙여버리는 동안에도
계속 통과했다. 실제 사용자 질문("삼성SDI**에서** 어떤 프로젝트를 했나요?")은
seed 0개였고, 홈에 걸린 한국어 샘플 5개 중 4개가 그랬다.

그래서 아래 한국어 케이스는 **홈 화면의 실제 샘플 질문 문자열을 그대로** 쓴다.
"""
import pytest

from profile_graph import _tokens, graph_retrieve, to_vis_html


def test_tokenizer_splits_hangul_from_alnum():
    """근본 원인을 직접 고정한다.

    구 정규식 `[a-z0-9가-힣]+` 는 한글과 영숫자를 한 문자클래스로 묶어서
    "KETI에서" 를 통째로 한 토큰으로 만들었다 — 'keti' 와 영원히 안 맞는다.
    """
    assert _tokens("KETI에서") == {"keti", "에서"}
    assert _tokens("삼성SDI에서") == {"삼성", "sdi", "에서"}
    assert _tokens("MLOps 플랫폼을") == {"mlops", "플랫폼을"}


def test_retrieves_relevant_seeds():
    r = graph_retrieve("How did you build the MLOps platform at KETI?")
    assert r["seeds"]
    assert any("MLOps" in s for s in r["seeds"])


def test_excludes_person_seed():
    r = graph_retrieve("on-prem MLOps serving")
    assert "Jisang Park" not in r["seeds"]
    assert "박지상" not in r["seeds"]


def test_empty_query_returns_nothing():
    assert graph_retrieve("")["seeds"] == []
    assert graph_retrieve("   ")["nodes"] == []


def test_context_present_when_seeds_found():
    r = graph_retrieve("RAG chatbot Samsung SDI")
    assert r["seeds"]
    assert r["context"]
    assert len(r["nodes"]) >= len(r["seeds"])


def test_bilingual():
    ko = graph_retrieve("삼성SDI RAG 챗봇", lang="한국어")
    assert ko["seeds"]


# ── 조사가 붙은 실제 한국어 질문 ────────────────────────────────────
# (query, seed 1위에 반드시 들어가야 하는 문자열)
KO_SAMPLES = [
    ("삼성SDI에서 어떤 프로젝트를 했나요?", "삼성SDI"),
    ("KETI에서 어떤 연구를 하고 있나요?", "KETI"),
    ("논문 주제가 뭔가요?", "논문"),
]


@pytest.mark.parametrize("query,expected", KO_SAMPLES, ids=[q for q, _ in KO_SAMPLES])
def test_korean_particles_do_not_kill_retrieval(query, expected):
    """조사가 붙어도 seed 를 찾고, 가장 관련 있는 노드가 1위여야 한다."""
    r = graph_retrieve(query, lang="한국어")
    assert r["seeds"], f"seed 0개 — 조사가 어간에 붙었다: {query}"
    assert expected in r["seeds"][0], f"1위 seed 가 {r['seeds'][0]!r} (기대: {expected})"


def test_korean_and_english_agree_on_the_same_question():
    """같은 질문의 한/영 표현이 같은 노드를 찾아야 한다 — 한쪽만 도는 걸 막는다."""
    ko = graph_retrieve("KETI에서 MLOps 플랫폼을 어떻게 구축했나요?", lang="한국어")
    en = graph_retrieve("How did you build the MLOps platform at KETI?")
    assert ko["seeds"] and en["seeds"]
    assert any("MLOps" in s for s in ko["seeds"]), ko["seeds"]


def test_single_char_tokens_do_not_seed():
    """'5년 후' 의 '5' 가 'Qwen2.5' 의 '5' 와 붙어 엉뚱한 노드를 seed 로 올렸다."""
    r = graph_retrieve("5년 후 목표는 무엇인가요?", lang="한국어")
    assert "Ollama" not in " ".join(r["seeds"])
    assert "FAISS" not in r["seeds"]


# ── 간판 주제가 df 컷에 먹히던 회귀 (2026-07-29) ──────────────────
# 문서빈도 컷은 조사를 걸러주지만, **중심 주제일수록 df 가 높아진다**는 역설이 있다.
# `rag` 의 df 는 정확히 cap(=노드수 38 × 0.25 = 9)이라 탈락했고, 이 리포의 간판인
# RAG 질문들이 seed 0개거나(한/영 모두) 남은 조사성 토큰 때문에 엉뚱한 노드를 물었다.
#   "RAG 파이프라인은?" → seeds ['TEBO 논문', 'IS477 · ETL']  ← 틀린 근거를 주입
# 기존 테스트가 초록이었던 이유: 'RAG chatbot Samsung SDI' 처럼 다른 토큰으로 통과.
RAG_QUERIES_KO = [
    "RAG 경험을 말해주세요",
    "당신의 RAG 시스템을 설명해주세요",
    "RAG 파이프라인은 어떻게 만들었나요?",
]
RAG_QUERIES_EN = [
    "Tell me about your RAG experience",
    "What is your RAG work?",
]


@pytest.mark.parametrize("q", RAG_QUERIES_KO)
def test_rag_questions_retrieve_rag_nodes_ko(q):
    r = graph_retrieve(q, lang="한국어")
    assert r["seeds"], f"seed 0개 — 간판 주제가 df 컷에 먹혔다: {q}"
    assert any("RAG" in s for s in r["seeds"]), f"RAG 노드가 아닌 seed: {r['seeds']}"


@pytest.mark.parametrize("q", RAG_QUERIES_EN)
def test_rag_questions_retrieve_rag_nodes_en(q):
    r = graph_retrieve(q)
    assert r["seeds"], q
    assert any("RAG" in s for s in r["seeds"]), f"RAG 노드가 아닌 seed: {r['seeds']}"


def test_filler_only_query_returns_no_subgraph():
    """변별 토큰이 하나도 없으면 **틀린 근거보다 근거 없음**이 낫다.

    설명에 한 번 스친 1점짜리 매치는 seed 가 되면 안 된다 — 그게 '파이프라인은' →
    TEBO 논문 같은 오답 서브그래프를 '집중 근거' 라벨로 주입하던 경로였다.
    """
    r = graph_retrieve("그건 어떻게 되나요?", lang="한국어")
    assert r["seeds"] == [], r["seeds"]


def test_to_vis_html_accepts_the_same_lang_tokens_as_retrieval():
    """graph_retrieve 는 'ko' 를 받는데 to_vis_html 은 KeyError 로 죽었다."""
    for lang in ("ko", "한국어", "en", "English"):
        assert "__LEGEND__" not in to_vis_html(lang)


def test_lang_token_variants_are_accepted():
    """골든셋은 'ko'/'en' 을 쓰고 앱은 '한국어'/'English' 를 쓴다 — 둘 다 받아야 한다."""
    assert graph_retrieve("논문 주제가 뭔가요?", lang="ko")["seeds"] == \
        graph_retrieve("논문 주제가 뭔가요?", lang="한국어")["seeds"]
