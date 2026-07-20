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
