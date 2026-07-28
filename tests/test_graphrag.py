"""GraphRAG 검색 회귀 테스트.

주의: 이 파일은 한 번 한국어를 놓쳤다. `test_bilingual` 이 "삼성SDI RAG 챗봇" —
**조사가 없는** 질문 — 을 써서, 토크나이저가 조사를 어간에 붙여버리는 동안에도
계속 통과했다. 실제 사용자 질문("삼성SDI**에서** 어떤 프로젝트를 했나요?")은
seed 0개였고, 홈에 걸린 한국어 샘플 5개 중 4개가 그랬다.

그래서 아래 한국어 케이스는 **홈 화면의 실제 샘플 질문 문자열을 그대로** 쓴다.
"""
import pytest

from profile_graph import _tokens, graph_retrieve


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


def test_lang_token_variants_are_accepted():
    """골든셋은 'ko'/'en' 을 쓰고 앱은 '한국어'/'English' 를 쓴다 — 둘 다 받아야 한다."""
    assert graph_retrieve("논문 주제가 뭔가요?", lang="ko")["seeds"] == \
        graph_retrieve("논문 주제가 뭔가요?", lang="한국어")["seeds"]
