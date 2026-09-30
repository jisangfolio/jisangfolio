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
