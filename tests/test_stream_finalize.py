"""스트림 마감 회귀 테스트.

스트림 루프는 <think> 블록 판정을 위해 앞 50자를 buffer 에 모으고, 50자를 넘겨야
buffer 를 full_response 로 승격한다. 그래서 50자 미만 응답은 buffer 에만 남은 채
스트림이 끝나 **빈 말풍선**이 되고 히스토리에 content="" 로 저장됐다.

하필 프롬프트가 지시하는 거절 문구가 전부 짧다:
  "I can't find that in the data."      → 30자
즉 "데이터에 없다"고 정직하게 답해야 하는 순간마다 화면이 비었다.

1_Chat.py 에서 한 번 고쳤지만 인라인 수정이라 2_Data_Analysis.py 로 넘어가지
않았다. ui.finalize_stream 으로 합치고 여기서 고정한다.
"""
import pytest

from ui import finalize_stream, friendly_llm_error, stream_answer


class _GroqChunk:
    """Groq SDK 모양: chunk.choices[0].delta.content"""
    def __init__(self, text):
        self.choices = [type("C", (), {"delta": type("D", (), {"content": text})()})()]


class _LangChainChunk:
    """LangChain 모양: chunk.content"""
    def __init__(self, text):
        self.content = text


def _chunks(text, shape=_GroqChunk, size=7):
    return [shape(text[i:i + size]) for i in range(0, len(text), size)]


def _run_stream(text, chunk_size=7, shape=_GroqChunk, lang="English"):
    """**실물** 스트림 루프(ui.stream_answer)를 돌린다.

    예전엔 이 헬퍼가 페이지의 루프를 재구현한 사본이었다. 그래서 테스트는 사본을
    검증했고, 실물 세 벌 중 하나만 고쳐도 초록일 수 있었다 — 이 파일 최상단 독스트링이
    말하는 바로 그 실패(1_Chat 만 고치고 2_Data_Analysis 는 못 고침)를 못 잡는 구조였다.
    """
    return stream_answer(_chunks(text, shape=shape, size=chunk_size), lang=lang)


SHORT_ANSWERS = [
    "I can't find that in the data.",                 # 프롬프트가 지시하는 거절 문구
    "데이터에서 찾을 수 없습니다.",
    "42",
    "Yes.",
]


@pytest.mark.parametrize("answer", SHORT_ANSWERS, ids=SHORT_ANSWERS)
def test_short_answers_survive(answer):
    """50자 미만 응답이 사라지면 안 된다 — 이게 원래 버그다."""
    assert len(answer) < 50, "이 케이스는 50자 미만이어야 의미가 있다"
    out = _run_stream(answer)
    assert answer.strip() in out, f"짧은 응답이 사라졌다: {answer!r} -> {out!r}"


def test_long_answer_unchanged():
    answer = "This is a long analytical answer about the uploaded dataset. " * 3
    out = _run_stream(answer)
    assert "long analytical answer" in out


def test_think_block_is_stripped():
    out = _run_stream("<think>reasoning goes here</think>\nThe mean is 3.5.")
    assert "The mean is 3.5." in out
    assert "reasoning goes here" not in out


def test_empty_stream_gets_placeholder_not_blank():
    """완전히 빈 응답이라도 빈 말풍선 대신 안내 문구가 나와야 한다."""
    assert finalize_stream("", "", None).strip()
    assert "다시" in finalize_stream("", "", None, lang="한국어")


def test_error_message_never_leaks_exception_text():
    """Groq 429 본문에는 조직 ID·쿼터가 실려 나온다. 화면에 나가면 안 된다."""
    err = Exception(
        "Error code: 429 - Rate limit reached for model `qwen/qwen3.6-27b` in "
        "organization `org_01abcdef0123456789` on tokens per minute (TPM): "
        "Limit 6000, Used 5983"
    )
    msg = friendly_llm_error(err)
    assert "org_01abcdef0123456789" not in msg
    assert "6000" not in msg
    assert "rate-limited" in msg.lower()


def test_generic_error_reports_type_only():
    msg = friendly_llm_error(ValueError("secret detail /Users/jjpark/.streamlit/secrets.toml"))
    assert "secrets.toml" not in msg
    assert "ValueError" in msg


# ── 루프를 세 벌로 복사해 두던 시절의 회귀 (2026-07-29) ─────────────
# 같은 상태기계가 1_Chat 1개 · 2_Data_Analysis 2개로 복사돼 있었고, 두 벌은 Groq 청크
# (choices[0].delta.content), 한 벌은 LangChain 청크(content) 를 읽었다. 그 모양 차이가
# 통합을 미루게 한 이유였는데, 실제로는 헬퍼 하나가 둘 다 흡수하면 끝이었다.
@pytest.mark.parametrize("shape", [_GroqChunk, _LangChainChunk],
                         ids=["groq", "langchain"])
def test_both_chunk_shapes_are_handled(shape):
    assert "The mean is 3.5." in _run_stream("The mean is 3.5.", shape=shape)


@pytest.mark.parametrize("shape", [_GroqChunk, _LangChainChunk],
                         ids=["groq", "langchain"])
def test_short_answer_survives_in_both_shapes(shape):
    """짧은 응답 버그가 한쪽 청크 모양에서만 고쳐지는 일이 없어야 한다."""
    assert "I can't find that in the data." in _run_stream(
        "I can't find that in the data.", shape=shape)


def test_none_content_chunks_are_tolerated():
    """스트림 마지막 청크는 content=None 으로 오는 경우가 있다."""
    assert "hi" in stream_answer([_GroqChunk("hi"), _GroqChunk(None), _LangChainChunk(None)])


def test_render_callback_sees_progressive_text():
    seen = []
    out = stream_answer(_chunks("x" * 120), render=seen.append)
    assert seen, "부분 응답이 한 번도 렌더되지 않았다"
    assert seen[-1] == out
    assert len(seen[0]) <= len(seen[-1])


def test_stream_answer_does_not_swallow_exceptions():
    """호출부의 except 가 friendly_llm_error 를 띄워야 한다 — 여기서 삼키면 안 된다."""
    def boom():
        yield _GroqChunk("partial")
        raise RuntimeError("stream died")

    with pytest.raises(RuntimeError):
        stream_answer(boom())


def test_pages_do_not_reimplement_the_loop():
    """세 페이지가 다시 자기 손으로 루프를 굴리기 시작하면 같은 드리프트가 재발한다."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name in ("pages/1_Chat.py", "pages/2_Data_Analysis.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert "stream_answer(" in src, f"{name} 가 공용 스트림 헬퍼를 안 쓴다"
        assert 'if "<think>" in buffer' not in src, f"{name} 에 루프 사본이 되살아났다"
