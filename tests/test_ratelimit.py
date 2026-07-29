"""ratelimit 의 순수 로직 회귀.

이 모듈의 핵심 함수들은 stdlib 만 쓰는데 테스트가 하나도 없었다 — 그런데 독스트링은
여기서 **실제로 버그가 났었다**고 적고 있다:

    "초 단위만 파싱하던 구현은 분 단위 응답에서 조용히 폴백으로 떨어져(1·2·4·8초)
     사실상 재시도를 포기했다."

조용히 틀리는 파서가 정확히 테스트가 필요한 종류다. 원장(ledger)도 같이 고정한다 —
집계가 조용히 0으로 리셋되면 하루 예산을 다 쓴 날에도 새 실행이 승인된다.
"""
import json

import pytest

import ratelimit
from ratelimit import (DAILY_TOKEN_BUDGET, TokenPacer, estimate_tokens,
                       is_daily_limit, parse_duration, parse_wait_seconds,
                       session_quota_exceeded)


@pytest.mark.parametrize("text,expected", [
    ("9.8s", 9.8),
    ("1m20s", 80.0),          # 초 단위만 보던 구현이 놓치던 형식
    ("1h2m3s", 3723.0),
    ("90ms", 0.09),
    ("2m", 120.0),
])
def test_parse_duration(text, expected):
    assert parse_duration(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["", None, "soon", "잠시 후"])
def test_parse_duration_returns_none_when_unreadable(text):
    assert parse_duration(text) is None


class _Resp:
    def __init__(self, headers):
        self.headers = headers


class _Err(Exception):
    def __init__(self, msg="", headers=None):
        super().__init__(msg)
        self.response = _Resp(headers) if headers is not None else None


def test_header_wins_over_message():
    err = _Err("Rate limit reached, try again in 1m20s", headers={"retry-after": "7"})
    assert parse_wait_seconds(err) == 7.0


def test_falls_back_to_the_message_when_no_header():
    assert parse_wait_seconds(_Err("Please try again in 1m20s.")) == pytest.approx(80.0)


def test_returns_none_when_nothing_is_parseable():
    assert parse_wait_seconds(_Err("boom")) is None


@pytest.mark.parametrize("msg,expected", [
    ("Rate limit reached for tokens per day (TPD)", True),
    ("limit reached, try again in 9.8s", False),
])
def test_is_daily_limit(msg, expected):
    assert is_daily_limit(_Err(msg)) is expected


def test_pacer_does_not_sleep_below_budget():
    """예산 안이면 wait_for 는 즉시 돌아와야 한다(테스트가 멈추면 안 되는 이유)."""
    p = TokenPacer(tpm_limit=1000, safety=1.0, verbose=False)
    p.events.append((__import__("time").time(), 100))
    p.wait_for(100)     # 100 + 100 <= 1000


def test_pacer_forgets_events_older_than_the_window():
    p = TokenPacer(tpm_limit=1000, safety=1.0, verbose=False)
    now = 10_000.0
    p.events.append((now - 120, 900))     # 창 밖
    p.events.append((now - 5, 50))        # 창 안
    assert p._used(now) == 50


def test_pacer_reads_the_real_limit_from_headers():
    p = TokenPacer(tpm_limit=8000, verbose=False)
    p.update_limit({"x-ratelimit-limit-tokens": "30000"})
    assert p.limit == 30000
    p.update_limit({"x-ratelimit-limit-tokens": "nonsense"})
    assert p.limit == 30000, "파싱 실패가 기존 상한을 망가뜨리면 안 된다"


def test_estimate_tokens_is_more_conservative_for_korean():
    ko = estimate_tokens("가" * 100)
    en = estimate_tokens("a" * 100)
    assert ko > en, "한국어는 문자당 토큰이 많아 보수적이어야 한다"


def test_session_quota_boundary():
    from ratelimit import SESSION_TURN_LIMIT
    assert not session_quota_exceeded(SESSION_TURN_LIMIT - 1)
    assert session_quota_exceeded(SESSION_TURN_LIMIT)


def test_one_session_cannot_take_most_of_the_day():
    """상한의 목적은 '한 사람이 우연히 하루치를 태우는 것' 방지다.

    상한 25 시절엔 한 세션이 하루 예산의 91% 까지 갈 수 있어서 목적을 달성하지
    못했다. 상한을 다시 올릴 때 이 계산이 같이 따라오게 못박는다.
    """
    from ratelimit import EST_TOKENS_PER_CHAT_TURN, SESSION_TURN_LIMIT
    share = (SESSION_TURN_LIMIT - 1) * EST_TOKENS_PER_CHAT_TURN / DAILY_TOKEN_BUDGET
    assert share <= 0.5, (
        f"한 세션이 하루 예산의 {share*100:.0f}% 를 쓸 수 있다 — "
        f"상한({SESSION_TURN_LIMIT})을 올렸다면 EST_TOKENS_PER_CHAT_TURN 근거도 다시 재라")


# ── 일일 원장 ────────────────────────────────────────────────────────
@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "daily_usage.json"
    monkeypatch.setattr(ratelimit, "_LEDGER_PATH", str(path))
    return path


def test_record_usage_accumulates(ledger):
    ratelimit.record_usage(100)
    ratelimit.record_usage(250)
    assert ratelimit.used_today() == 350
    assert ratelimit.remaining_today() == DAILY_TOKEN_BUDGET - 350


def test_ledger_write_is_atomic_and_leaves_no_temp_file(ledger):
    ratelimit.record_usage(10)
    leftovers = list(ledger.parent.glob("*.tmp"))
    assert not leftovers, f"임시 파일이 남았다: {leftovers}"
    assert json.loads(ledger.read_text())          # 유효한 JSON


def test_concurrent_writes_do_not_lose_usage(ledger):
    """스레드 40개 × 100토큰. 락이 없던 시절 4,000 대신 200 이 남았다."""
    import threading
    threads = [threading.Thread(target=ratelimit.record_usage, args=(100,)) for _ in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert ratelimit.used_today() == 4000


def test_corrupt_ledger_is_quarantined_not_silently_zeroed(ledger, capsys):
    """깨진 원장을 조용히 {} 로 돌리면 예산을 다 쓴 날에도 새 실행이 승인된다."""
    ledger.write_text('{"2026-07-29": 1234')      # 잘린 JSON
    assert ratelimit.used_today() == 0            # 값 자체는 복구 불가
    assert ledger.with_suffix(".json.corrupt").exists(), "손상 파일을 흔적 없이 지우면 안 된다"
    assert "손상" in capsys.readouterr().out


def test_ledger_keeps_only_recent_days(ledger):
    ledger.write_text(json.dumps({f"2026-01-{d:02d}": 1 for d in range(1, 21)}))
    ratelimit.record_usage(5)
    assert len(json.loads(ledger.read_text())) <= 7
