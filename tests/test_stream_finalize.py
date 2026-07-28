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

from ui import finalize_stream, friendly_llm_error


def _run_stream(text, chunk_size=7):
    """페이지의 스트림 루프를 그대로 흉내내 (full_response, buffer, in_think) 를 만든다."""
    full_response, buffer, in_think = "", "", None
    for i in range(0, len(text), chunk_size):
        delta = text[i:i + chunk_size]
        if in_think is None:
            buffer += delta
            if "<think>" in buffer:
                in_think = True
            elif len(buffer) >= 50:
                in_think = False
                full_response = buffer
        elif in_think:
            buffer += delta
            if "</think>" in buffer:
                full_response = buffer.split("</think>", 1)[1].lstrip("\n")
                in_think = False
        else:
            full_response += delta
    return full_response, buffer, in_think


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
    out = finalize_stream(*_run_stream(answer))
    assert answer.strip() in out, f"짧은 응답이 사라졌다: {answer!r} -> {out!r}"


def test_long_answer_unchanged():
    answer = "This is a long analytical answer about the uploaded dataset. " * 3
    out = finalize_stream(*_run_stream(answer))
    assert "long analytical answer" in out


def test_think_block_is_stripped():
    out = finalize_stream(*_run_stream("<think>reasoning goes here</think>\nThe mean is 3.5."))
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
