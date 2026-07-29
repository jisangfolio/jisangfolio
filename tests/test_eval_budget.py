"""평가 하니스의 예산 가드 테스트.

배경: 배포된 Streamlit 앱과 평가 하니스가 **같은 Groq 키·같은 일일 예산**을 쓴다.
전체 골든셋 1회가 169k(84%)여서, 인자 없이 실행하는 것만으로 그날 방문자
(=채용담당자)가 429를 보게 됐다. 실제로 한 번 그렇게 됐다.

처음엔 기본값을 작은 티어로 바꿔서 피했는데, 그러면 **나머지 케이스는 영원히 안 도는
장식**이 된다. 그래서 골든셋 자체를 48 → 20건으로 줄였다(지운 건 `evals/archive/`).
지금은 전체 실행이 약 77k(39%)라 기본값이 곧 전체 실행이다. (추정은 보수적이라
실사용은 그보다 낮다 — 2026-07-29 실측 62k.)

여기서 고정하는 것: 전체 실행이 예산 안에 들 것, 방문자 몫이 남을 것, 카테고리·언어
커버리지가 유지될 것.
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
    # 함수 안 import 는 skip 이 아니라 red 를 만든다 — 3.10 에서는 아래 secrets 스킵보다
    # 먼저 터진다. 진짜로 건너뛰려면 importorskip 이어야 한다.
    tomllib = pytest.importorskip("tomllib")
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if not secrets.exists():
        pytest.skip("secrets.toml 없음 (CI 는 키 없이 돈다)")
    return tomllib.load(secrets.open("rb"))["resume_text"]


def _full():
    return (_load("golden_chat.jsonl"), _load("golden_router.jsonl"),
            _load("golden_rag.jsonl"))


def test_full_run_fits_the_safety_share():
    """전체 실행이 하루 예산의 SAFE_SHARE 안에 들어야 한다.

    케이스를 추가하다 이 선을 넘으면, 늘린 그 순간에 알아야 한다 — 나중에 실행이
    중간에 죽고 나서가 아니라.
    """
    est = estimate_run_cost(*_full(), _resume())
    share = est["합계"] / DAILY_TOKEN_BUDGET
    assert share <= SAFE_SHARE, (
        f"전체 실행이 하루 예산의 {share*100:.0f}% 를 쓴다 (상한 {SAFE_SHARE*100:.0f}%). "
        f"케이스를 늘렸다면 줄이거나, 예산 배분을 의식적으로 다시 정해야 한다."
    )


def test_full_run_leaves_room_for_visitors():
    """평가 후에도 방문자가 최소 15턴은 쓸 수 있어야 한다 (챗 1턴 ≈ 6k).

    배포된 앱이 같은 키를 쓰므로, 평가가 다 먹으면 그날 사이트가 죽은 것과 같다.
    """
    est = estimate_run_cost(*_full(), _resume())
    remaining = DAILY_TOKEN_BUDGET - est["합계"]
    assert remaining // 6000 >= 15, f"방문자 몫이 {remaining // 6000}턴밖에 안 남는다"


def test_every_behavioural_category_survives_in_both_languages():
    """줄이면서 커버리지가 조용히 빠지는 걸 막는다.

    인젝션에 페르소나가 버티는지, 주제이탈을 거절하는지는 모델을 불러봐야만 안다
    (문자열 검사로 대체 불가). 한국어만 남기면 영어 경로가 검증에서 사라진다.
    """
    chat = _load("golden_chat.jsonl")
    for cat in ("offtopic", "injection"):
        langs = {c.get("lang") for c in chat if c.get("category") == cat}
        assert {"ko", "en"} <= langs, f"{cat} 가 {langs} 만 검증한다"
    assert any(c.get("category") == "factual-guard" for c in chat), \
        "사실 가드(안 쓴 도구를 썼다고 하지 않는가) 케이스가 사라졌다"


def test_router_covers_both_classes():
    labels = {c["expected"] for c in _load("golden_router.jsonl")}
    assert labels == {"PANDAS", "RAG"}, f"라우터가 한쪽 클래스만 본다: {labels}"


def test_rag_covers_retrieval_and_refusal():
    cats = {c["category"] for c in _load("golden_rag.jsonl")}
    assert {"factual", "refuse"} <= cats, f"RAG 커버리지 부족: {cats}"


def test_dropped_cases_are_archived_not_deleted():
    """줄인 케이스는 사라진 게 아니라 archive 로 옮긴 것이어야 한다."""
    archive = EVAL_DIR / "archive"
    assert archive.is_dir(), "evals/archive/ 가 없다"
    kept = {c["id"] for group in _full() for c in group}
    for f in archive.glob("*.dropped.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                case = json.loads(line)
                assert case["id"] not in kept, \
                    f"{case['id']} 이 골든셋과 archive 양쪽에 있다"
