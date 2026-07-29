"""분당 토큰(TPM) 페이싱 · 대기시간 파싱 — 무료 티어에서 429를 '맞고 복구'하지 않고 '안 맞게' 한다.

Groq 무료 티어는 모델별로 분당 토큰 상한이 걸린다(예: qwen3.6-27b = 8,000 TPM).
Agentic RAG는 질문 하나당 판정→(재작성)→생성→근거점검으로 3~4콜을 연달아 쏘기 때문에,
상한을 넘기는 건 예외 상황이 아니라 정상 부하다. 그래서 두 겹을 둔다.

  ① TokenPacer — 최근 60초 사용량을 추적해, 다음 호출이 상한을 넘길 것 같으면 미리 잔다.
     성공한 호출의 **실제 usage**를 되먹여 추정 오차가 누적되지 않게 한다.
  ② parse_wait_seconds — 그래도 429가 나면 서버가 알려준 대기시간을 그대로 존중한다.
     "9.8s"·"1m20s"·"1h2m3s"·"90ms" 형식을 모두 처리한다 — 초 단위만 파싱하던 구현은
     분 단위 응답에서 조용히 폴백으로 떨어져(1·2·4·8초) 사실상 재시도를 포기했다.

모델별로 버킷이 따로이므로 페이서도 모델별로 둔다(pacer_for).
"""
import json
import os
import re
import threading
import time
from collections import deque
from datetime import datetime

# 무료 티어 기본값. 실제 값은 응답 헤더 x-ratelimit-limit-tokens 로 갱신된다.
DEFAULT_TPM = 8000
# 상한의 몇 %까지만 쓸지 — 프롬프트 토큰 추정 오차와 동시성 여지를 남긴다.
SAFETY = 0.85

_DURATION_PARTS = re.compile(r"([\d.]+)\s*(ms|h|m|s)")
_TRY_AGAIN = re.compile(r"try again in\s*([0-9hms.\s]+)", re.IGNORECASE)


def parse_duration(text):
    """'1m20s' → 80.0, '9.8s' → 9.8, '90ms' → 0.09. 못 읽으면 None."""
    if not text:
        return None
    factor = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}
    parts = _DURATION_PARTS.findall(str(text))
    if not parts:
        return None
    return sum(float(n) * factor[u] for n, u in parts)


def parse_wait_seconds(err):
    """예외/메시지에서 대기시간을 뽑는다. 헤더(retry-after)가 있으면 우선."""
    headers = getattr(getattr(err, "response", None), "headers", None) or {}
    for key in ("retry-after", "x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        raw = headers.get(key)
        if raw:
            secs = parse_duration(raw) if not str(raw).isdigit() else float(raw)
            if secs:
                return secs
    m = _TRY_AGAIN.search(str(err))
    return parse_duration(m.group(1)) if m else None


def is_daily_limit(err) -> bool:
    """일일 한도(TPD/RPD)면 기다려도 안 풀린다 — 재시도 대신 즉시 중단해야 한다."""
    msg = str(err).lower()
    return "per day" in msg or "tpd" in msg or "rpd" in msg


class TokenPacer:
    """최근 60초 토큰 사용량을 보고 선제적으로 재우는 슬라이딩 윈도우 페이서."""

    def __init__(self, tpm_limit: int = DEFAULT_TPM, safety: float = SAFETY, verbose: bool = True):
        self.limit = tpm_limit
        self.safety = safety
        self.verbose = verbose
        self.events = deque()  # (timestamp, tokens)

    @property
    def budget(self) -> float:
        return self.limit * self.safety

    def update_limit(self, headers):
        """응답 헤더의 실제 상한으로 갱신 — 티어를 올려도 코드를 안 고쳐도 된다."""
        try:
            limit = int((headers or {}).get("x-ratelimit-limit-tokens", 0))
            if limit > 0:
                self.limit = limit
        except (TypeError, ValueError):
            pass

    def _used(self, now: float) -> float:
        while self.events and now - self.events[0][0] > 60:
            self.events.popleft()
        return sum(t for _, t in self.events)

    def wait_for(self, need: int, deadline: float = None):
        """다음 호출이 need 토큰을 쓸 예정 — 창이 빌 때까지 잔다.

        deadline(time.monotonic 절대시각)을 주면 그 안에 못 끝날 대기는 자지 않고
        TimeoutError 로 즉시 포기한다. 무인 실행(평가 하니스)에서는 끈기 있게 기다리는
        게 옳지만, 사람이 화면을 보고 있는 앱에서는 몇 분짜리 sleep 이 곧 '멈춘 사이트'다.
        """
        while True:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("pacing budget exhausted for this turn")
            now = time.time()
            used = self._used(now)
            if used + need <= self.budget or not self.events:
                return
            # 가장 오래된 기록이 창 밖으로 나갈 때까지
            sleep_for = 60 - (now - self.events[0][0]) + 0.3
            if deadline is not None and time.monotonic() + sleep_for > deadline:
                raise TimeoutError("pacing wait would exceed this turn's deadline")
            if self.verbose and sleep_for > 1:
                print(f"    · TPM 페이싱 — {sleep_for:.0f}s 대기 (최근 1분 {used:.0f}/{self.budget:.0f} 토큰)")
            time.sleep(max(sleep_for, 0.3))

    def record(self, tokens: int):
        self.events.append((time.time(), max(int(tokens), 0)))
        # TPM 창(분 단위)과 별개로 일일 원장에도 누적한다 — TPD 는 헤더로 안 오므로
        # 우리가 세지 않으면 아무도 모른다.
        record_usage(max(int(tokens), 0))


_PACERS = {}


def pacer_for(model: str) -> TokenPacer:
    """모델별 페이서 — Groq 한도는 모델 단위로 따로 걸린다."""
    return _PACERS.setdefault(model, TokenPacer())


def estimate_tokens(text: str) -> int:
    """프롬프트 토큰 대략 추정. 한국어는 문자당 토큰이 많아 보수적으로 잡는다."""
    if not text:
        return 0
    hangul = sum(1 for c in text if "가" <= c <= "힣")
    return int(hangul * 0.9 + (len(text) - hangul) / 3.5) + 8


# ── 일일 사용량 원장 ────────────────────────────────────────────────
# Groq 은 TPM 은 헤더로 알려주는데(`x-ratelimit-limit-tokens: 8000`) **TPD 는 안 알려준다**.
# 그래서 하니스는 "오늘 이미 얼마 썼는지"를 모른 채 매 실행을 0부터 시작했고, 이미 비어
# 있는 예산에 뛰어들어 몇 케이스 만에 'per day' 에러로 죽었다(실제로 그렇게 한 번 죽었다).
# 남은 예산을 알아야 실행 여부를 판단할 수 있으므로 직접 적어 둔다.
#
# ⚠️ 한계: 이 원장은 **로컬 실행분만** 본다. 배포된 앱이 같은 키로 쓰는 토큰은 안 보이므로
#    실제 사용량의 하한이다. 그래서 SAFE_SHARE 로 여유를 남기는 게 여전히 필요하다.
DAILY_TOKEN_BUDGET = 200_000
_LEDGER_PATH = os.path.join(os.path.dirname(__file__), "evals", ".daily_usage.json")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


# 원장 갱신은 read-modify-write 라서 동시 기록이 서로를 덮어쓴다(40스레드 × 100토큰을
# 넣었더니 4,000 이 아니라 200 만 남았다). 읽는 쪽(하니스)은 순차라 지금 당장 오답을
# 보지는 않지만, 배포 앱은 세션마다 스레드로 기록하므로 원인은 실재한다.
_LEDGER_LOCK = threading.Lock()


def _load_ledger():
    try:
        with open(_LEDGER_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        # 깨진 원장을 조용히 {} 로 돌리면 **오늘 쓴 양이 0으로 리셋**되어, 예산을 다
        # 쓴 날에도 하니스가 새 20만 토큰을 승인한다 — 이 모듈이 막으려던 바로 그 사고다.
        # 그래서 깨진 파일은 치워두고 티가 나게 남긴다.
        try:
            os.replace(_LEDGER_PATH, _LEDGER_PATH + ".corrupt")
            print(f"⚠️  사용량 원장이 손상돼 {_LEDGER_PATH}.corrupt 로 옮겼습니다 "
                  "— 오늘 집계가 0부터 다시 시작합니다.")
        except OSError:
            pass
        return {}


def record_usage(tokens: int):
    """이번 호출에 쓴(=예약한) 토큰을 오늘자에 누적한다."""
    with _LEDGER_LOCK:
        led = _load_ledger()
        led[_today()] = int(led.get(_today(), 0)) + int(tokens)
        for k in sorted(led)[:-7]:      # 날짜 키가 무한히 쌓이지 않게 최근 7일만
            led.pop(k, None)
        try:
            os.makedirs(os.path.dirname(_LEDGER_PATH), exist_ok=True)
            # 임시 파일 → os.replace 로 원자적 교체. 곧바로 open(..,"w") 하면
            # 쓰다가 죽었을 때 잘린 JSON 이 남고, 그게 위 손상 경로로 이어진다.
            tmp = f"{_LEDGER_PATH}.{os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(led, f, indent=2, sort_keys=True)
            os.replace(tmp, _LEDGER_PATH)
        except OSError:
            pass          # 원장을 못 써도 실행 자체를 막지는 않는다


def used_today() -> int:
    return int(_load_ledger().get(_today(), 0))


def remaining_today() -> int:
    return max(0, DAILY_TOKEN_BUDGET - used_today())


# ── 세션 단위 요청 상한 ─────────────────────────────────────────────
# 위 페이서는 **재우기만** 한다 — 거절하지 않는다. 그래서 요청 수 자체에는 상한이
# 없었고, 익명 방문자 한 명이 무료 티어 하루치를 혼자 태울 수 있었다.
# 그러면 그날 다른 방문자는 전부 429를 본다.
#
# 숫자 근거(2026-07-29 실측, 한국어 기준):
#   시스템 프롬프트(이력서+관계도+질문별 GraphRAG) ≈ 4.4k  ← 매 턴 상수
#   재전송 히스토리(ui.REPLAY_MAX_MESSAGES=12 로 상한)  ≲ 2.6k
#   답변 예산                                            = 0.6k
#   → 턴당 최악 ≈ 7.6k
# 예전 상한 25는 한 세션에 최대 ~182k, 즉 하루 예산(200k)의 **91%** 를 한 사람에게
# 내주는 값이었다. 그건 "한 사람이 우연히 예산을 다 쓰는 걸 막는다"는 이 상한의
# 목적을 사실상 달성하지 못한다(구 주석의 '33턴'은 GraphRAG 주입 이전 추정치다).
# 12로 낮추면 세션당 ≈91k ≈ 46% 라, 최소 두 명은 온전한 세션을 쓸 수 있다.
#
# 로그인이 없으므로 세션 단위가 실효 경계다(쿠키를 지우면 리셋된다 = 우회 가능).
# 목적이 악의적 공격 차단이 아니라 우발적 소진 방지라 이 정도가 비용 대비 맞는 선이다.
# 대부분의 방문자는 3~5턴에서 끝나고, 상한에 닿으면 이력서 PDF·메일로 안내한다.
SESSION_TURN_LIMIT = 12

# 턴당 토큰 추정치(위 근거). 상한을 만질 때 비용 계산이 같이 따라오게 코드에 둔다.
EST_TOKENS_PER_CHAT_TURN = 7_600


def session_quota_exceeded(turns: int, limit: int = SESSION_TURN_LIMIT) -> bool:
    return turns >= limit


def quota_message(lang: str = "English") -> str:
    return ("한 세션에서 물어볼 수 있는 횟수를 다 쓰셨어요. 이 데모는 무료 티어라 "
            "하루 예산이 정해져 있어서, 다른 방문자 몫을 남기려고 세션당 상한을 뒀습니다. "
            "더 궁금한 점은 이력서 PDF나 메일로 편하게 물어봐 주세요."
            if lang == "한국어" else
            "You've reached this session's question limit. The demo runs on a free tier "
            "with a fixed daily budget, so there's a per-session cap to leave room for "
            "other visitors. Happy to answer more over email — or see the résumé PDF.")
