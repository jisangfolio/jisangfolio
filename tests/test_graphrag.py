from profile_graph import graph_retrieve


def test_retrieves_relevant_seeds():
    r = graph_retrieve("How did you build the MLOps platform at KETI?")
    assert r["seeds"]
    assert any("MLOps" in s for s in r["seeds"])


def test_excludes_person_seed():
    r = graph_retrieve("on-prem MLOps serving")
    assert "Jisang Park" not in r["seeds"]
    assert "박지상" not in r["seeds"]


def test_empty_query_returns_nothing():
    assert graph_retrieve("")["seeds"] == []
    assert graph_retrieve("   ")["nodes"] == []


def test_context_present_when_seeds_found():
    r = graph_retrieve("RAG chatbot Samsung SDI")
    assert r["seeds"]
    assert r["context"]
    assert len(r["nodes"]) >= len(r["seeds"])


def test_bilingual():
    ko = graph_retrieve("삼성SDI RAG 챗봇", lang="한국어")
    assert ko["seeds"]
