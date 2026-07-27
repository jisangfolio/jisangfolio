"""경량 LLM 옵저버빌리티 (자체호스팅 스타일).

모든 챗봇·데이터 분석 턴을 트레이싱한다: 지연(latency)·모델·라우트·가드 판정·GraphRAG 노드.
토큰/비용 회계는 의도적으로 범위 밖 — 정확한 토크나이저 없이 추정치를 적으면 대시보드가
틀린 숫자를 사실처럼 보여준다. 필요해지면 Groq 응답의 usage를 받아 기록할 것.
외부 SaaS(Langfuse·Arize Phoenix) 대신, 온프레미스/무외부의존 철학에 맞춰 인앱으로 구현.
컨테이너 수명 동안 공유되는 스토어(@st.cache_resource)에 쌓고 Observability 페이지에서 시각화한다.
"""
import time
import streamlit as st


@st.cache_resource
def _store():
    # 컨테이너 수명 동안 세션·리런을 넘어 공유되는 트레이스 저장소
    return {"traces": []}


def log_trace(page: str, model: str, route: str, latency_ms: int,
              guard: str = "ok", nodes=None, ok: bool = True, ts: float = None):
    """한 턴을 트레이스로 기록한다."""
    traces = _store()["traces"]
    traces.append({
        "ts": ts if ts is not None else time.time(),
        "page": page,
        "model": model,
        "route": route,
        "latency_ms": int(latency_ms),
        "guard": guard,
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
