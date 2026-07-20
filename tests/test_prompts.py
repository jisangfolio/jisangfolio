from prompts import clean_response, strip_foreign_cjk, strip_think


def test_strip_think_removes_block():
    assert strip_think("<think>reasoning here</think>answer") == "answer"


def test_clean_removes_think_and_bold():
    out = clean_response("<think>x</think>**bold** and text")
    assert "**" not in out
    assert "<think>" not in out
    assert "bold and text" in out


def test_cjk_removes_hanja_keeps_hangul():
    assert strip_foreign_cjk("CSV等非경험") == "CSV경험"
    assert "現象" not in strip_foreign_cjk("현상(現象)을 검출(検出)")


def test_cjk_preserves_jamo_latin_numbers():
    assert strip_foreign_cjk("ㅎㅇ ㅋㅋ Python RAG 200ms") == "ㅎㅇ ㅋㅋ Python RAG 200ms"


def test_cjk_removes_fullwidth_and_chinese():
    out = strip_foreign_cjk("평가받았어요.，那时候의 경험")
    assert "，" not in out
    assert "那时候" not in out
    assert "경험" in out
