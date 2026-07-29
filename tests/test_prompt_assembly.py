"""앱과 평가 하니스가 **같은 프롬프트를 조립하는지** 고정한다.

모듈을 공유하는 것만으로는 부족하다. 예전엔 양쪽이 build_system_prompt 를 공유했지만
질문별 GraphRAG 서브그래프 주입은 pages/1_Chat.py 안에만 있었다 — evals/ 전체에
graph_retrieve 호출이 0건이었으니, 하니스는 앱이 실제로 모델에 보내는 프롬프트를
평가한 적이 한 번도 없다. README 의

    "Those same modules feed the app pages, the eval harness and the tests,
     so the graph and the bot share one source."

가 조립 경로에서는 참이 아니었고, 하필 이 리포가 가장 앞세우는 기능이 회귀 게이트
밖에 있었다. 그래서 조립 자체를 prompts.py 로 올리고, 여기서 그걸 못박는다.

run_evals 는 groq SDK 가 있어야 import 되므로(CI 엔 없다) 하니스 쪽은 test_mcp_drift
와 같은 방식으로 소스 텍스트를 본다.
"""
from pathlib import Path

import pytest

from prompts import build_chat_system_prompt, build_system_prompt, get_df_info

ROOT = Path(__file__).resolve().parents[1]
RESUME = "Jisang Park — built an air-gapped RAG chatbot at Samsung SDI."


def test_question_adds_a_graphrag_block():
    base = build_system_prompt("English", RESUME)
    prompt, gr = build_chat_system_prompt("English", RESUME, "Tell me about your RAG experience")
    assert gr["seeds"], "간판 주제인데 seed 가 없다"
    assert "[GraphRAG" in prompt
    assert len(prompt) > len(base)


def test_no_question_means_no_graph_block():
    prompt, gr = build_chat_system_prompt("English", RESUME)
    assert prompt == build_system_prompt("English", RESUME)
    assert gr["seeds"] == []


def test_graph_block_language_follows_lang():
    ko, _ = build_chat_system_prompt("한국어", RESUME, "삼성SDI에서 어떤 프로젝트를 했나요?")
    en, _ = build_chat_system_prompt("English", RESUME, "What did you work on at Samsung SDI?")
    assert "이 질문에 관련된 프로필 서브그래프" in ko
    assert "Profile subgraph relevant to this question" in en


def test_lang_token_variants_are_accepted():
    """골든셋은 'ko'/'en' 을 쓴다 — 조용히 영어 헤더로 떨어진 전례가 있다."""
    a, _ = build_chat_system_prompt("ko", RESUME, "논문 주제가 뭔가요?")
    b, _ = build_chat_system_prompt("한국어", RESUME, "논문 주제가 뭔가요?")
    assert a == b


@pytest.mark.parametrize("path,needle", [
    ("pages/1_Chat.py", "build_chat_system_prompt("),
    ("evals/run_evals.py", "build_chat_system_prompt("),
])
def test_both_sides_use_the_shared_assembly(path, needle):
    assert needle in (ROOT / path).read_text(encoding="utf-8"), f"{path} 가 공유 조립을 안 쓴다"


def test_no_local_graphrag_assembly_survives():
    """페이지가 다시 자기 손으로 조립하기 시작하면 같은 드리프트가 재발한다."""
    src = (ROOT / "pages/1_Chat.py").read_text(encoding="utf-8")
    assert "graph_retrieve(" not in src, "페이지가 직접 GraphRAG 를 조립하고 있다"


# ── 라우터 입력(df 요약) 사본 제거 ──────────────────────────────────
def test_df_info_has_one_owner():
    for path in ("pages/2_Data_Analysis.py", "evals/run_evals.py"):
        src = (ROOT / path).read_text(encoding="utf-8")
        assert "def get_df_info(" not in src, f"{path} 에 df 요약 사본이 남아 있다"
        assert "get_df_info" in src, f"{path} 가 공유 df 요약을 안 쓴다"


def test_df_info_format():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    out = get_df_info(df)
    for label in ("컬럼:", "행 수:", "데이터 타입:", "처음 3행:"):
        assert label in out
    assert "행 수: 3" in out


def test_df_info_is_in_the_cache_fingerprint():
    """포맷을 바꿔도 --resume 가 옛 라우팅 PASS 를 재활용하면 안 된다."""
    src = (ROOT / "evals/run_evals.py").read_text(encoding="utf-8")
    assert "inspect.getsource(get_df_info)" in src
    assert "_graph_fingerprint()" in src, "그래프를 고쳐도 캐시가 안 무효화된다"
