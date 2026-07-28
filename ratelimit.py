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
import re
import time
from collections import deque

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

    def wait_for(self, need: int):
        """다음 호출이 need 토큰을 쓸 예정 — 창이 빌 때까지 잔다."""
        while True:
            now = time.time()
            used = self._used(now)
            if used + need <= self.budget or not self.events:
                return
            # 가장 오래된 기록이 창 밖으로 나갈 때까지
            sleep_for = 60 - (now - self.events[0][0]) + 0.3
            if self.verbose and sleep_for > 1:
                print(f"    · TPM 페이싱 — {sleep_for:.0f}s 대기 (최근 1분 {used:.0f}/{self.budget:.0f} 토큰)")
            time.sleep(max(sleep_for, 0.3))

    def record(self, tokens: int):
        self.events.append((time.time(), max(int(tokens), 0)))


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
