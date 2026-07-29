"""주입 이력서가 골든셋의 사실 주장을 지탱하는지 — LLM 호출 없이 검증한다.

챗봇은 이력서를 시스템 프롬프트로 받아 답한다. 그래서 골든셋이 "이 답변에 X가
있어야 한다"고 요구하는데 이력서 원문에 X가 없으면, 그 케이스는 **모델 품질과 무관하게
구조적으로 통과 불가**다(반대로 금지어가 원문에 있으면 봇이 그대로 인용해 떨어진다).

무료 티어에서 평가 1회가 하루 예산의 상당분을 먹기 때문에, 이 종류의 실패는 API를
쓰기 전에 문자열 매칭으로 잡아야 한다. 이력서를 압축·수정할 때의 안전벨트이기도 하다.

이력서는 gitignore 대상(`.streamlit/`)이라 CI에서는 자동 skip된다 — 로컬 게이트다.
"""
import json
import pathlib

import pytest

# tomllib 은 3.11+ 다. 최상단에서 그냥 import 하면 3.10 에서 ModuleNotFoundError 가
# collection 단계에 터져 **이 파일 하나 때문에 전체 스위트가 중단**된다(실제로 그랬다).
# importorskip 은 진짜 skip 을 만든다 — 함수 안으로 내리기만 하면 red 로 바뀔 뿐이다.
tomllib = pytest.importorskip("tomllib")

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "evals" / "golden_chat.jsonl"


def _resume() -> str:
    """실제로 주입되는 텍스트(secrets의 resume_text)를 본다. 없으면 skip."""
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if not secrets.exists():
        pytest.skip("secrets.toml 없음 (CI 환경) — 로컬에서만 검사")
    text = tomllib.load(secrets.open("rb")).get("resume_text", "")
    if not text.strip():
        pytest.skip("resume_text 비어 있음")
    return text


def _cases():
    return [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_every_factual_case_is_answerable():
    """각 케이스의 must_include_any 중 **최소 하나**는 이력서에 있어야 한다.

    must_include_any는 OR 조건이므로("200ms" 또는 "200 ms" 또는 "밀리초") 전부를
    요구하지 않는다. 다만 하나도 없으면 그 케이스는 절대 통과할 수 없다.
    """
    resume = _resume().lower()
    unanswerable = []
    for c in _cases():
        need = c.get("must_include_any") or []
        if need and not any(k.lower() in resume for k in need):
            unanswerable.append((c["id"], need))
    assert not unanswerable, (
        "이력서에 근거가 없어 구조적으로 통과 불가한 케이스: "
        + "; ".join(f"{cid} (기대 중 하나: {need})" for cid, need in unanswerable)
    )


def test_banned_terms_absent_from_resume():
    """금지어가 이력서 원문에 있으면 봇이 인용해 떨어진다 — 원문에서 먼저 없애야 한다.

    페르소나 누설 방어용 토큰(`/no_think`·`PERSONA INSTRUCTIONS` 등)은 프롬프트
    구조에 대한 것이지 이력서 내용이 아니므로 검사 대상에서 제외한다.
    """
    resume = _resume().lower()
    prompt_artifacts = {"/no_think", "persona instructions", "top priority rules",
                        "페르소나 지시사항", "최우선 언어 규칙"}
    found = set()
    for c in _cases():
        for k in c.get("must_not_include") or []:
            if k.lower() in prompt_artifacts:
                continue
            if k.lower() in resume:
                found.add(k)
    assert not found, f"이력서 원문에 금지어가 있음: {sorted(found)}"


# ── 폐기된 주장이 라이브 봇 입으로 되살아나는 것 방지 (2026-07-29) ──
# 이 검사는 원래 jisangfolio_mcp.py(2차 사본)에만 걸려 있었다. 정작 챗봇이 1인칭으로
# 말하는 원본 두 개 — resume_text 와 profile_graph 노드 설명 — 은 아무도 안 봤고,
# 그래서 "(Graphify)" 와 "10/16→15/16" 이 리포가 그것들을 폐기한 뒤에도 살아남았다.
from retired_claims import find_retired  # noqa: E402


def test_resume_text_has_no_retired_claims():
    hits = find_retired(_resume())
    assert not hits, "이력서 원문에 폐기된 주장이 있음:\n" + "\n".join(
        f"  · {m!r} — {why}" for m, why in hits)


def test_profile_graph_has_no_retired_claims():
    """그래프 설명도 챗봇 프롬프트에 함께 주입된다 — resume_text 만 고치면 반쪽이다."""
    import profile_graph

    blob = " ".join(f"{n['ko']} {n['en']} {n['desc_ko']} {n['desc_en']}"
                    for n in profile_graph.NODES)
    hits = find_retired(blob)
    assert not hits, "프로필 그래프에 폐기된 주장이 있음:\n" + "\n".join(
        f"  · {m!r} — {why}" for m, why in hits)
