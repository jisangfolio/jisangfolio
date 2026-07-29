"""경량 LLM 옵저버빌리티 (자체호스팅 스타일).

모든 챗봇·데이터 분석 턴을 트레이싱한다: 지연(latency)·모델·라우트·가드 판정·GraphRAG 노드.
토큰/비용 회계는 의도적으로 범위 밖 — 정확한 토크나이저 없이 추정치를 적으면 대시보드가
틀린 숫자를 사실처럼 보여준다. 필요해지면 Groq 응답의 usage를 받아 기록할 것.
외부 SaaS(Langfuse·Arize Phoenix) 대신, 온프레미스/무외부의존 철학에 맞춰 인앱으로 구현.
컨테이너 수명 동안 공유되는 스토어(@st.cache_resource)에 쌓고 Observability 페이지에서 시각화한다.
"""
import time


def _new_store():
    # 컨테이너 수명 동안 세션·리런을 넘어 공유되는 트레이스 저장소
    return {"traces": []}


_STORE = None


def _store():
    """트레이스 저장소를 지연 생성한다.

    streamlit import 가 함수 안에 있는 이유: 이 모듈의 집계 규칙(summarize_guard)은
    streamlit 이 없는 CI 에서 테스트돼야 한다. 최상단 import 하나가 테스트 수집을
    통째로 죽여 CI 를 4런 동안 빨갛게 만든 전례가 있다(ui.apply_style 주석 참고).
    """
    global _STORE
    if _STORE is None:
        import streamlit as st
        _STORE = st.cache_resource(_new_store)()
    return _STORE


# 차단 턴이 남기는 route 값. 대시보드는 **이 값**으로 차단을 센다 — 차단 카테고리
# 목록을 화면 쪽에 복사해두면 guardrails 에 카테고리가 추가될 때 조용히 누락된다.
BLOCK_ROUTE = "blocked"


def summarize_guard(traces):
    """(차단 건수, 미측정 건수) 를 센다.

    guard 는 None 이 **"측정 안 함"** 이다(log_trace 독스트링 참고). 예전 대시보드는
    `guard != "ok"` 로 세서 미측정과 쿼터 거절까지 '가드레일 차단'에 합산했다 —
    이 모듈이 세운 원칙을 화면이 정반대로 어긴 셈이라, 규칙을 여기로 가져왔다.
    """
    blocked = sum(1 for t in traces if t.get("route") == BLOCK_ROUTE)
    unmeasured = sum(1 for t in traces if not t.get("guard"))
    return blocked, unmeasured


def log_trace(page: str, model: str, route: str, latency_ms: int,
              guard: str = None, nodes=None, ok: bool = True, ts: float = None):
    """한 턴을 트레이스로 기록한다.

    guard 기본값은 None이다 — "ok"를 기본으로 두면 **가드레일을 아예 돌지 않은 경로**까지
    대시보드에 '통과'로 찍힌다. 측정 안 한 것은 측정 안 했다고 보여주는 게 이 모듈의 원칙
    (docstring 첫 문단 참조)이라, 호출부가 실제 판정을 넘기지 않으면 미측정으로 남긴다.
    """
    traces = _store()["traces"]
    traces.append({
        "ts": ts if ts is not None else time.time(),
        "page": page,
        "model": model,
        "route": route,
        "latency_ms": int(latency_ms),
        "guard": guard,          # None = 미측정 (UI에서 "—"로 렌더)
        "nodes": nodes or [],
        "ok": ok,
    })
    if len(traces) > 500:            # 상한 (메모리 보호)
        del traces[: len(traces) - 500]


def get_traces():
    return list(_store()["traces"])


def clear_traces():
    _store()["traces"].clear()


class timer:
    """with timer() as t: ...  → t.ms 로 경과 밀리초."""
    def __enter__(self):
        self._t0 = time.time()
        self.ms = 0
        return self

    def __exit__(self, *exc):
        self.ms = int((time.time() - self._t0) * 1000)
        return False
