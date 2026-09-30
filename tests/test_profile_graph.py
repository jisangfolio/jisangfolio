import profile_graph as pg


def test_no_duplicate_node_ids():
    ids = [n["id"] for n in pg.NODES]
    assert len(ids) == len(set(ids))


def test_no_dangling_edges():
    ids = {n["id"] for n in pg.NODES}
    for a, b in pg.EDGES:
        assert a in ids, a
        assert b in ids, b


def test_no_orphan_nodes():
    ids = {n["id"] for n in pg.NODES}
    linked = {x for e in pg.EDGES for x in e}
    assert ids - linked == set()


def test_every_group_has_color_and_size():
    for n in pg.NODES:
        assert n["group"] in pg.GROUP_COLOR, n["group"]
        assert n["group"] in pg.GROUP_SIZE, n["group"]


def test_nodes_are_bilingual():
    for n in pg.NODES:
        for key in ("ko", "en", "desc_ko", "desc_en"):
            assert n.get(key), (n["id"], key)


def test_prompt_text_reaches_every_node():
    txt = pg.to_prompt_text("English")
    for n in pg.NODES:
        assert n["en"] in txt, n["en"]


def test_vis_html_renders():
    html = pg.to_vis_html("English")
    assert "vis-network" in html
    assert "__NODES__" not in html  # placeholder fully substituted


def test_every_edge_has_a_bilingual_label():
    """엣지 이름은 EDGES 와 별 dict 라 추가할 때 조용히 빠질 수 있다 — 여기서 잡는다."""
    missing = [e for e in pg.EDGES if e not in pg.EDGE_LABEL]
    assert not missing, f"EDGE_LABEL 누락: {missing}"
    for e, lab in pg.EDGE_LABEL.items():
        assert len(lab) == 2 and all(lab), (e, lab)


def test_no_stale_edge_labels():
    """엣지를 지웠는데 라벨이 남아 있으면 다음 사람이 없는 관계를 믿게 된다."""
    stale = [e for e in pg.EDGE_LABEL if e not in set(pg.EDGES)]
    assert not stale, f"EDGES 에 없는 라벨: {stale}"


def test_edge_labels_render_into_the_html():
    for lang, idx in (("한국어", 0), ("English", 1)):
        html = pg.to_vis_html(lang)
        assert pg.EDGE_LABEL[("jjpark", "infomax")][idx] in html, lang


def test_embed_height_covers_the_canvas():
    """iframe 높이가 캔버스보다 작으면 그래프 아래가 잘린다 — 실제로 100px 잘려 있었다.

    홈이 하드코딩 숫자로 되돌아가는 것도 함께 막는다.
    """
    from pathlib import Path
    home = (Path(__file__).resolve().parents[1] / "jisangfolio.py").read_text(encoding="utf-8")
    assert pg.EMBED_HEIGHT >= pg.NET_HEIGHT + pg.LEGEND_HEIGHT
    assert f"height={pg.NET_HEIGHT}" not in home, "캔버스 높이를 홈에 하드코딩하고 있다"
    assert "height=profile_graph.EMBED_HEIGHT" in home, \
        "홈이 그래프 모듈의 EMBED_HEIGHT 를 쓰지 않는다 — 다시 어긋난다"
    assert f"height:{pg.NET_HEIGHT}px" in pg.to_vis_html("English")


def test_edge_labels_are_always_on_with_hover_emphasis():
    """선 이름은 상시 노출이 기본이다 — hover 전용으로 바꿨더니 '사라졌다'가 됐다.

    hover 는 지우고 드러내는 장치가 아니라 **밝기를 올리는** 장치여야 한다.
    """
    html = pg.to_vis_html("한국어")
    assert "hoverNode" in html and "selectNode" in html, "강조 훅이 없다"
    assert "network.fit(" in html, "fit() 이 없으면 바깥 노드가 캔버스 밖으로 잘린다"
    assert "drawThreshold" in html, "축소 배율에서 vis 가 라벨을 통째로 안 그린다"

    import json, re
    raw = re.search(r"new vis\.DataSet\((\[\{\"id\": \"e0\".*?\}\])\);", html, re.S).group(1)
    labelled = [e for e in json.loads(raw) if e.get("label")]
    assert len(labelled) == len(pg.EDGES), \
        f"선 이름이 {len(labelled)}/{len(pg.EDGES)} 개만 박혀 있다 — 상시 노출이 깨졌다"
