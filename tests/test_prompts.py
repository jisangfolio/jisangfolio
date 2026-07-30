from prompts import clean_response, strip_foreign_cjk, strip_think


def test_strip_think_removes_block():
    assert strip_think("<think>reasoning here</think>answer") == "answer"


def test_strip_think_drops_unterminated_block():
    """닫히지 않은 <think> — 사고가 max_tokens 에 잘린 경우.

    2_Data_Analysis 의 코드 생성 경로가 여기서 죽었다. 그쪽 사본은
    `code.split("</think>")[-1]` 이었는데, 닫는 태그가 없으면 split 이 원문을
    통째로 돌려주고 [-1] 이 사고 텍스트 전체를 '코드'로 흘려보냈다.
    """
    assert strip_think("<think>여기서 잘렸다") == ""
    assert strip_think("result = df.mean()\n<think>사족") == "result = df.mean()"


def _code_only(path):
    """주석만 뺀 코드를 돌려준다. 문자열은 **남긴다**.

    주석까지 훑으면 *옛 버그를 설명하는 주석*이 위반으로 잡힌다 — 실제로 이 테스트를
    처음 넣었을 때 2_Data_Analysis 의 수정 사유 주석이 스스로를 걸었다.
    반대로 문자열까지 버리면 이번엔 아무것도 못 잡는다. 찾으려는 사본이
    `split("</think>")` 처럼 **문자열 인자 안에** 있기 때문이다.
    두 번 다 같은 실수 — 무엇을 검사 대상으로 볼지 안 정하고 필터를 먼저 짰다.
    """
    import io
    import tokenize
    with open(path, "rb") as fh:
        toks = list(tokenize.tokenize(io.BytesIO(fh.read()).readline))
    return " ".join(t.string for t in toks if t.type != tokenize.COMMENT)


def test_pages_do_not_reimplement_think_stripping():
    """페이지가 사고 제거를 자기 손으로 다시 짜면 같은 드리프트가 재발한다."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name in ("pages/1_Chat.py", "pages/2_Data_Analysis.py", "pages/4_MLOps_Docs.py"):
        code = _code_only(root / name)
        assert "</think>" not in code, f"{name} 에 사고 제거 사본이 되살아났다"


def test_the_scanner_would_actually_catch_a_copy():
    """검사가 공허하게 통과하지 않는지 — 심어놓은 위반을 잡는지 확인한다."""
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "planted.py"
        f.write_text('x = code.split("</think>")[-1]\n', encoding="utf-8")
        assert "</think>" in _code_only(f), "심어놓은 사본을 못 잡는다"
        g = Path(d) / "comment_only.py"
        g.write_text('# 옛날엔 split("</think>") 였다\nx = 1\n', encoding="utf-8")
        assert "</think>" not in _code_only(g), "주석을 위반으로 잡는다"


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
