"""README 의 Python 배지가 실제 최소 요구 버전과 맞는지 확인한다.

배지는 3.10+ 라고 적혀 있었지만 `tomllib` 은 3.11 표준 라이브러리다. 3.10 에서는
pytest 가 collection 단계에서 죽어 테스트가 **한 개도** 안 돌았다. CI 가 3.12 로
고정돼 있어서 안 보였을 뿐이다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 표준 라이브러리 모듈 → 도입된 최소 (major, minor)
_STDLIB_MIN = {
    "tomllib": (3, 11),
    "graphlib": (3, 9),
    "zoneinfo": (3, 9),
}


def _sources():
    for path in ROOT.rglob("*.py"):
        if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
            continue
        yield path


def _required_version():
    """코드가 실제로 요구하는 최소 파이썬 버전을 import 로 역산한다."""
    required = (3, 9)
    for path in _sources():
        text = path.read_text(encoding="utf-8")
        for mod, ver in _STDLIB_MIN.items():
            if re.search(rf"^\s*import {mod}\b|^\s*from {mod}\b", text, re.M):
                required = max(required, ver)
    return required


def test_readme_badge_matches_actual_requirement():
    major, minor = _required_version()
    badge = re.search(r"Python-(\d)\.(\d+)%2B", (ROOT / "README.md").read_text(encoding="utf-8"))
    assert badge, "README 에서 Python 배지를 찾지 못했다"
    claimed = (int(badge.group(1)), int(badge.group(2)))
    assert claimed == (major, minor), (
        f"배지는 {claimed[0]}.{claimed[1]}+ 인데 코드는 {major}.{minor}+ 를 요구한다 "
        f"(stdlib import 기준)"
    )


def _ci_versions(text):
    """워크플로에서 실제로 돌리는 파이썬 버전 전부.

    스칼라(`python-version: "3.12"`)와 매트릭스 리스트(`["3.11", "3.12"]`)를 모두 읽는다.
    스칼라만 보던 시절, 매트릭스로 바꾸면 이 검사가 **0건 매치로 조용히 통과**했다 —
    버전 게이트가 사라진 걸 아무도 모르는 상태가 정확히 이 파일이 막으려는 실패다.
    (`${{ matrix.python-version }}` 참조는 값이 아니므로 버전 추출 대상이 아니다.)
    """
    versions = []
    for m in re.finditer(r'python-version:\s*(\[[^\]]*\]|"?\d+\.\d+"?)', text):
        versions += [(int(a), int(b)) for a, b in re.findall(r"(\d+)\.(\d+)", m.group(1))]
    return versions


def test_ci_python_is_not_below_requirement():
    major, minor = _required_version()
    found = []
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        versions = _ci_versions(wf.read_text(encoding="utf-8"))
        found += versions
        for ci in versions:
            assert ci >= (major, minor), f"{wf.name}: CI {ci} < 요구 {(major, minor)}"
    assert found, "워크플로에서 파이썬 버전을 하나도 못 찾았다 — 검사가 공허하게 통과 중"


def test_ci_actually_runs_the_claimed_minimum():
    """README 가 3.11+ 라고 주장하면 CI 가 3.11 을 **실제로** 돌려야 한다.

    문서·CI·코드의 주장끼리 대조하는 것만으로는 '3.11 에서 돈다'가 증명되지 않는다.
    """
    required = _required_version()
    found = []
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        found += _ci_versions(wf.read_text(encoding="utf-8"))
    assert required in found, f"CI 가 최소 버전 {required[0]}.{required[1]} 을 안 돌린다 (돌리는 버전: {sorted(set(found))})"
