"""문서에 적힌 골든셋 크기와 실제 파일을 대조한다.

README 는 "45 cases" 라고 썼는데 실제로는 19+20+9=48 이었고, evals/README 의 표는
챗봇을 16건으로 적어둔 채 19건이 돼 있었다. 이 리포가 파는 것이 '정직한 측정'인데
분모가 틀리면 그 위에 얹은 McNemar p값·Wilson 구간까지 같이 신뢰를 잃는다.

케이스를 추가할 때 문서를 같이 안 고치면 여기서 실패한다.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"

GOLDEN = {
    "chat": EVALS / "golden_chat.jsonl",
    "router": EVALS / "golden_router.jsonl",
    "rag": EVALS / "golden_rag.jsonl",
}


def _count(path):
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_golden_file_is_non_empty(name):
    assert _count(GOLDEN[name]) > 0


def test_evals_readme_table_matches_files():
    """evals/README.md 표의 `golden_*.jsonl (N)` 이 실제 줄 수와 같아야 한다."""
    text = (EVALS / "README.md").read_text(encoding="utf-8")
    found = dict(re.findall(r"`(golden_\w+\.jsonl)`\s*\((\d+)\)", text))
    assert found, "evals/README.md 표에서 골든셋 개수를 찾지 못했다"
    for name, path in GOLDEN.items():
        claimed = found.get(path.name)
        assert claimed is not None, f"{path.name} 이 표에 없다"
        assert int(claimed) == _count(path), \
            f"{path.name}: 표는 {claimed}건, 실제 {_count(path)}건"


def test_total_case_count_is_stated_correctly_everywhere():
    """총합이 README 와 evals/README 양쪽에 같은 숫자로 적혀 있어야 한다."""
    total = sum(_count(p) for p in GOLDEN.values())
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    evals_readme = (EVALS / "README.md").read_text(encoding="utf-8")

    assert f"{total} cases" in root_readme, \
        f"README.md 에 '{total} cases' 가 없다 (실제 골든셋 {total}건)"
    assert f"{total}건" in evals_readme, \
        f"evals/README.md 에 '{total}건' 이 없다 (실제 골든셋 {total}건)"


def test_chat_cases_declare_a_language():
    """lang 이 빠지면 normalize_lang 이 영어로 떨어뜨린다 — 조용히 새는 자리다."""
    import json
    for line in GOLDEN["chat"].read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        assert case.get("lang") in ("ko", "en", "한국어", "English"), \
            f"lang 누락/오타: {case.get('id', line[:40])}"
