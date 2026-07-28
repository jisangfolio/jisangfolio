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


def test_ci_python_is_not_below_requirement():
    major, minor = _required_version()
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        for m in re.finditer(r'python-version:\s*"?(\d)\.(\d+)"?', wf.read_text(encoding="utf-8")):
            ci = (int(m.group(1)), int(m.group(2)))
            assert ci >= (major, minor), f"{wf.name}: CI {ci} < 요구 {(major, minor)}"
