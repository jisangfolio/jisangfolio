"""평가 하니스의 예산 가드 테스트.

배경: 배포된 Streamlit 앱과 평가 하니스가 **같은 Groq 키·같은 일일 예산**을 쓴다.
전체 골든셋 1회 실행이 무료 일일한도를 넘기 때문에, 인자 없이 실행하는 것만으로
그날 방문자(=채용담당자)가 429를 보게 된다. 실제로 한 번 그렇게 됐다.

그래서 (1) 기본값은 예산 안에 드는 core 집합이고, (2) 한도를 넘는 실행은 프리플라이트가
막는다. 이 둘이 되돌려지면 여기서 실패한다.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evals"))

pytest.importorskip("groq", reason="groq SDK 없으면 하니스를 import 할 수 없다")

from run_evals import (  # noqa: E402
    DAILY_TOKEN_BUDGET,
    SAFE_SHARE,
    estimate_run_cost,
)

EVAL_DIR = ROOT / "evals"


def _load(name):
    return [json.loads(l) for l in (EVAL_DIR / name).read_text(encoding="utf-8").splitlines() if l.strip()]


def _resume():
    import tomllib
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if not secrets.exists():
        pytest.skip("secrets.toml 없음 (CI 는 키 없이 돈다)")
    return tomllib.load(secrets.open("rb"))["resume_text"]


def _core(cases):
    return [c for c in cases if c.get("core")]


def test_core_run_fits_the_safety_share():
    """기본 실행이 하루 예산의 SAFE_SHARE 안에 들어야 한다."""
    resume = _resume()
    est = estimate_run_cost(_core(_load("golden_chat.jsonl")),
                            _core(_load("golden_router.jsonl")),
                            _core(_load("golden_rag.jsonl")), resume)
    share = est["합계"] / DAILY_TOKEN_BUDGET
    assert share <= SAFE_SHARE, (
        f"기본 실행이 하루 예산의 {share*100:.0f}% 를 쓴다 (상한 {SAFE_SHARE*100:.0f}%). "
        f"core 태그를 늘렸다면 되돌리거나 SAFE_SHARE 를 의식적으로 올려야 한다."
    )


def test_core_run_leaves_room_for_visitors():
    """평가 후에도 방문자가 최소 15턴은 쓸 수 있어야 한다 (챗 1턴 ≈ 6k)."""
    resume = _resume()
    est = estimate_run_cost(_core(_load("golden_chat.jsonl")),
                            _core(_load("golden_router.jsonl")),
                            _core(_load("golden_rag.jsonl")), resume)
    remaining = DAILY_TOKEN_BUDGET - est["합계"]
    assert remaining // 6000 >= 15, f"방문자 몫이 {remaining // 6000}턴밖에 안 남는다"


def test_full_run_would_exceed_budget():
    """전체 실행이 예산을 넘는다는 사실 자체를 고정한다.

    이게 통과하지 않게 되면(=전체가 예산에 들어오면) 기본값을 core 로 둘 이유가
    사라진 것이므로, 그때는 이 테스트와 함께 기본값도 다시 판단해야 한다.
    """
    resume = _resume()
    est = estimate_run_cost(_load("golden_chat.jsonl"), _load("golden_router.jsonl"),
                            _load("golden_rag.jsonl"), resume)
    assert est["합계"] > DAILY_TOKEN_BUDGET * SAFE_SHARE


def test_behavioural_cases_are_all_core():
    """문자열 검사로 대체 불가능한 케이스는 전부 기본 실행에 있어야 한다.

    인젝션에 페르소나가 버티는지, 주제이탈을 거절하는지는 모델을 불러봐야만 안다.
    반면 factual 은 tests/test_resume_facts.py 가 토큰 0으로 드리프트를 잡으므로
    표본만 남겨도 된다 — 그게 core 선정 기준이다.
    """
    behavioural = {"factual-guard", "offtopic", "injection"}
    missing = [c["id"] for c in _load("golden_chat.jsonl")
               if c.get("category") in behavioural and not c.get("core")]
    assert not missing, f"모델 호출로만 검증되는 케이스가 기본 실행에서 빠졌다: {missing}"


def test_router_core_covers_both_classes():
    core = _core(_load("golden_router.jsonl"))
    labels = {c["expected"] for c in core}
    assert labels == {"PANDAS", "RAG"}, f"라우터 core 가 한쪽 클래스만 본다: {labels}"
