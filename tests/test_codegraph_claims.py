"""README 가 코드그래프에 대해 말하는 수치가 실제 파일과 맞는지 확인한다.

CI 에는 이미 코드그래프 staleness 게이트가 있다(gen_codegraph.py 를 다시 돌려
assets/codegraph.html 과 diff). 그런데 그 게이트가 보는 것은 **파일**이고,
README 가 그 파일에 대해 **주장하는 숫자**는 아무도 안 봤다.

그래서 실제로 이런 일이 있었다(2026-07-29 발견): 그래프가 커져 302 노드가 됐는데
README 는 "vis-network, 226 nodes" 를 그대로 들고 있었다. 파일은 최신인데 파일에
대한 설명만 낡은 상태 — tests/retired_claims.py 가 적어둔 그 패턴
("코드 드리프트는 CI 가 잡는데 주장 드리프트는 사본마다 따로 논다")이 감시 장치
자신에게서 한 번 더 난 것이다.

노드 수는 코드가 늘면 자연히 변한다. 즉 이 숫자는 **가만히 둬도 언젠가 반드시 틀리는
종류의 주장**이고, 그런 주장은 사람이 기억해서 고치는 대신 테스트가 잡아야 한다.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "assets" / "codegraph.html"
README = ROOT / "README.md"


def _actual_node_count() -> int:
    """codegraph.html 에 실제로 들어 있는 노드 수.

    범례 문구("302 nodes · 646 edges")가 아니라 vis.DataSet 의 노드 배열을 센다 —
    범례는 사람이 읽는 표시이고, 이 테스트가 확인해야 할 진실은 데이터 쪽이다.
    """
    html = GRAPH.read_text(encoding="utf-8")
    m = re.search(r"var nodes = new vis\.DataSet\((\[.*?\])\);", html, re.S)
    assert m, "codegraph.html 에서 노드 DataSet 을 찾지 못했다"
    return len(json.loads(m.group(1)))


def test_readme_node_count_matches_graph():
    claimed = re.search(r"vis-network,\s*([\d,]+)\s*nodes", README.read_text(encoding="utf-8"))
    assert claimed, "README 에서 코드그래프 노드 수 주장을 찾지 못했다 — 문구가 바뀌었다면 이 정규식도 같이 고쳐야 한다"
    claimed_n = int(claimed.group(1).replace(",", ""))
    actual_n = _actual_node_count()
    assert claimed_n == actual_n, (
        f"README 는 {claimed_n} 노드라고 하는데 assets/codegraph.html 에는 {actual_n} 개가 있다. "
        f"`python gen_codegraph.py` 로 그래프를 갱신했다면 README 문구도 같이 고쳐라."
    )


def test_graph_legend_matches_its_own_data():
    """범례에 박힌 숫자와 실제 데이터가 어긋나지 않는지 — 생성기 자체의 회귀 검사."""
    html = GRAPH.read_text(encoding="utf-8")
    legend = re.search(r"([\d,]+)\s*nodes\s*·\s*([\d,]+)\s*edges", html)
    assert legend, "codegraph.html 범례에서 노드/엣지 수를 찾지 못했다"
    assert int(legend.group(1).replace(",", "")) == _actual_node_count(), (
        "범례의 노드 수가 실제 노드 배열과 다르다 — gen_codegraph.py 의 범례 조립이 깨졌다"
    )
