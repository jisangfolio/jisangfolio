"""대시보드가 모듈 자신의 원칙을 어기던 회귀.

observability.log_trace 는 guard 기본값을 None 으로 두고, 그 독스트링이 이유를 못박는다:

    "ok"를 기본으로 두면 **가드레일을 아예 돌지 않은 경로**까지 대시보드에 '통과'로 찍힌다.

그런데 대시보드는 `(df["guard"] != "ok").sum()` 으로 차단을 셌다. None != "ok" 는 True 라,
미측정 턴과 쿼터 거절까지 전부 '가드레일 차단'으로 집계됐다 — 원칙을 정확히 반대편으로
어긴 것이고, 하필 이 리포가 자랑하는 지표 카드였다.

카테고리 목록을 화면에 하드코딩하는 대신 route=="blocked" 로 세는 이유는 아래
test_new_guard_category_does_not_need_a_dashboard_change 가 고정한다.
"""
from observability import BLOCK_ROUTE, summarize_guard

TRACES = [
    # 정상 채팅 — 가드 통과
    {"route": "chat", "guard": "ok"},
    {"route": "chat", "guard": "ok"},
    # 가드가 막은 턴
    {"route": "blocked", "guard": "prompt_injection"},
    {"route": "blocked", "guard": "too_long"},
    # 쿼터 거절 — 가드가 막은 게 아니다
    {"route": "quota", "guard": "quota"},
    # 가드를 아예 안 타는 경로 = 미측정
    {"route": "rag_docs", "guard": None},
    {"route": "data", "guard": ""},
]


def test_counts_only_real_blocks():
    blocked, _ = summarize_guard(TRACES)
    assert blocked == 2


def test_unmeasured_is_not_counted_as_a_block():
    """구 로직 `guard != "ok"` 는 여기서 5를 냈다 (차단 2 + 쿼터 1 + 미측정 2)."""
    blocked, unmeasured = summarize_guard(TRACES)
    assert blocked == 2
    assert unmeasured == 2
    assert sum(1 for t in TRACES if t["guard"] != "ok") == 5, "구 로직의 오답을 고정해 둔다"


def test_quota_rejection_is_not_a_guardrail_block():
    blocked, _ = summarize_guard([{"route": "quota", "guard": "quota"}])
    assert blocked == 0


def test_empty_traces():
    assert summarize_guard([]) == (0, 0)


def test_new_guard_category_does_not_need_a_dashboard_change():
    """guardrails 에 카테고리가 추가돼도 집계가 조용히 틀리면 안 된다.

    차단 카테고리 집합을 화면에 복사해두는 대안은, 이번엔 반대 방향으로 같은 버그를
    만든다(새 카테고리를 **누락**). route 로 세면 그 실패가 구조적으로 불가능하다.
    """
    blocked, _ = summarize_guard([{"route": BLOCK_ROUTE, "guard": "some_future_category"}])
    assert blocked == 1
