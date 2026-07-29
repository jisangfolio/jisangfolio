"""홈 화면 문구에 폐기된 주장이 되살아나지 않았는지 확인한다.

폐기-주장 검사는 이미 세 표면을 보고 있었다 — resume_text(`test_resume_facts`),
profile_graph.NODES(같은 파일), jisangfolio_mcp.py(`test_mcp_drift`). 그런데
**방문자가 가장 먼저 읽는 표면인 홈(jisangfolio.py)은 아무도 안 봤다.**

그래서 실제로 이런 일이 있었다(2026-07-29 발견): `tests/retired_claims.py` 가
`10/16|15/16` 을 명시적으로 금지하고, profile_graph 는 이미 갱신됐고, README 는
"history rather than a running score" 로 강등해뒀는데, **홈 카드의 한국어·영어 설명은
그 숫자를 여전히 성과로 말하고 있었다.** 채용담당자가 링크를 열면 첫 화면에서 보는
숫자가, 리포가 스스로 금지한 숫자였다.

**주석이 아니라 문자열 리터럴만 본다.** 이유가 있다 — 홈에는
`# ... graphify 아님` 같이 *폐기 사유를 설명하는* 주석이 있고, README 에는 그 숫자가
왜 폐기됐는지 적은 문단이 있다. 소스를 통째로 훑으면 그런 정직한 설명이 위반으로
잡힌다. 검사해야 할 것은 개발자가 서로에게 쓴 말이 아니라 **화면에 나가는 말**이다.
AST 의 문자열 상수만 모으면 주석은 구조적으로 빠진다.
"""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "jisangfolio.py"

from retired_claims import find_retired  # noqa: E402


def _visible_strings(path: Path) -> str:
    """소스에서 화면에 나갈 수 있는 문자열 리터럴만 모은다(주석 제외).

    모듈·함수·클래스 독스트링은 개발자용 설명이므로 함께 제외한다 — 그쪽은 주석과
    같은 성격이고, 폐기 사유를 적어두는 자리이기도 하다.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    return " ".join(
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
    )


def test_home_has_no_retired_claims():
    hits = find_retired(_visible_strings(HOME))
    assert not hits, "홈 화면 문구에 폐기된 주장이 있음:\n" + "\n".join(
        f"  · {m!r} — {why}" for m, why in hits)


def test_scanner_sees_the_home_copy_at_all():
    """스캔이 공허하게 통과하지 않는지 — 문구를 못 읽고 있으면 위 검사는 무의미하다.

    홈의 T 딕셔너리 구조가 바뀌어 문자열을 못 모으게 되면, 위 테스트는 빈 문자열을
    검사하며 영원히 초록으로 남는다. 그 상태가 이 파일이 막으려는 실패다.
    """
    text = _visible_strings(HOME)
    assert len(text) > 5000, f"홈에서 모은 문구가 {len(text)}자뿐 — 추출이 깨졌을 가능성"
    assert "박지상" in text or "Jisang" in text, "홈 문구를 읽고 있지 않다"


@pytest.mark.parametrize("banned", ["10/16", "Kubeflow", "정출연"])
def test_scanner_actually_catches_a_planted_claim(banned):
    """검출기가 살아 있는지 — 심어놓은 위반을 잡는지 직접 확인한다."""
    assert find_retired(f"이 문장은 {banned} 을(를) 포함한다"), f"{banned!r} 을 못 잡는다"
