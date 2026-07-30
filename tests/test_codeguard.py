"""codeguard.py 회귀 테스트 — LLM 생성 코드의 실행 경계.

이 리포에서 가장 위험한 코드다. 실제로 세 번 뚫렸고 셋 다 여기 케이스로 박아둔다:

  1. `pd` 모듈을 그대로 넘겨 `pd.io.common.os.popen(...)` 으로 임의 명령 실행이 됐다.
     배포 컨테이너엔 Groq 키·GCP 개인키·SMTP 자격증명·비공개 이력서가 있었다.
  2. 쓰기 메서드를 열거해 막았더니 `to_string(buf=)`·`to_html(buf=)`·
     `to_markdown(buf=)`·`df.style.to_html(path)` 로 파일이 그대로 써졌다.
  3. dunder 를 문자열 리터럴에 숨기고 `str.format` 에게 속성 탐색을 시키니
     `'{0.__class__.__init__.__globals__[sys].modules[os].environ}'.format(df)` 로
     프로세스 환경변수 전체가 나왔다 — AST 는 문자열 *안*을 안 보기 때문이다.

그래서 이 테스트는 "막혔는가"만 보지 않고 **실제로 디스크에 파일이 생겼는지**,
**심어둔 카나리가 결과에 섞여 나왔는지**까지 본다.
"""
import os

import pandas as pd
import pytest

from codeguard import ALLOWED_TO, check_generated_code, run_generated_code


@pytest.fixture
def df():
    return pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})


# ── 실행돼선 안 되는 것 ──────────────────────────────────────────────
ESCAPES = [
    ("os 모듈 도달",      "result = pd.io.common.os.popen('id').read()"),
    ("builtins 회수",     "result = pd.io.common.__builtins__"),
    ("임의 파일 읽기",     "result = pd.read_csv('.streamlit/secrets.toml')"),
    ("dunder 체인",       "result = df.__class__.__mro__[0].__subclasses__()"),
    ("globals",          "result = df.__class__.__init__.__globals__"),
    ("import",           "import os\nresult = os.getcwd()"),
    ("from import",      "from os import system\nresult = system('id')"),
    ("pandas eval",      "result = df.eval('a * 2')"),
    ("pandas query",     "result = df.query('a > 1')"),
    ("dunder 이름",       "result = __import__('os').getcwd()"),
    # ── §4: 문자열 리터럴에 숨긴 dunder + str.format 이 대신 타 주는 속성 체인
    ("format 환경변수",   "result = '{0.__class__.__init__.__globals__[sys].modules[os].environ}'.format(df)"),
    ("format 변수 경유",  "s = '{0.__class__.__mro__}'\nresult = s.format(df)"),
    ("format_map",       "result = '{d.__class__}'.format_map({'d': df})"),
    ("문자열 dunder 단독", "result = str(df) + '__class__'"),
    ("무한루프",          "while True:\n    pass\nresult = 1"),
]


@pytest.mark.parametrize("label,code", ESCAPES, ids=[e[0] for e in ESCAPES])
def test_escape_is_blocked(df, label, code):
    result, chart, err = run_generated_code(code, df)
    assert err is not None, f"탈출 성공: {label}"
    assert result is None


# ── 파일 쓰기: 차단 여부 + 실제 디스크 생성 여부 ──────────────────────
WRITERS = ["to_csv", "to_excel", "to_json", "to_pickle", "to_parquet", "to_hdf",
           "to_sql", "to_feather", "to_stata", "to_orc", "to_xml", "to_latex",
           "to_clipboard", "to_string", "to_html", "to_markdown", "to_gbq"]


@pytest.mark.parametrize("meth", WRITERS)
def test_writer_methods_rejected(df, meth, tmp_path):
    """to_* writer는 전부 정적 거부. denylist 열거는 반드시 빠지므로 allowlist다."""
    target = tmp_path / f"{meth}.out"
    _, _, err = run_generated_code(f"result = df.{meth}('{target}')", df)
    assert err is not None, f"{meth} 가 통과했다"
    assert not target.exists(), f"{meth} 가 실제로 파일을 만들었다: {target}"


def test_styler_writers_rejected(df, tmp_path):
    """df.style 은 Styler를 통해 to_html/to_excel/to_latex 를 다시 노출한다."""
    target = tmp_path / "styled.html"
    _, _, err = run_generated_code(f"result = df.style.to_html('{target}')", df)
    assert err is not None
    assert not target.exists()


def test_no_file_created_by_any_escape(df, tmp_path):
    """탈출 시도 후 임시 디렉토리가 비어 있어야 한다."""
    for _, code in ESCAPES:
        run_generated_code(code, df)
    assert list(tmp_path.iterdir()) == []


def test_no_secret_leaks_through_any_escape(df, monkeypatch):
    """'막혔다'가 아니라 '안 샜다'를 본다.

    Streamlit Cloud 는 시크릿을 환경변수로도 노출한다. 카나리를 심고 모든 탈출
    시도의 결과·에러 문자열 어디에도 안 섞여 나오는지 확인한다 — 차단 사유만
    보면 값이 에러 메시지에 실려 나가는 경우를 놓친다.
    """
    monkeypatch.setenv("PLANTED_SECRET", "CANARY_123")
    for label, code in ESCAPES:
        result, chart, err = run_generated_code(code, df)
        blob = f"{result}{chart}{err}"
        assert "CANARY_123" not in blob, f"카나리 유출: {label}"
    assert os.environ["PLANTED_SECRET"] == "CANARY_123"  # 카나리가 실제로 심겼는지


# ── 정상 코드는 그대로 돌아야 한다 (과차단 방지) ──────────────────────
LEGIT = [
    ("groupby 집계",  "result = df.groupby('b')['a'].mean()"),
    ("to_numeric",   "result = pd.to_numeric(df['a'], errors='coerce').sum()"),
    ("describe",     "result = df['a'].describe()"),
    ("to_frame",     "result = df['a'].describe().to_frame()"),
    ("to_dict",      "result = df.head(1).to_dict()"),
    ("to_list",      "result = df['b'].to_list()"),
    ("DataFrame 생성", "result = pd.DataFrame({'x': [1, 2]}).sum()"),
    ("정렬·슬라이싱",   "result = df.sort_values('a', ascending=False).head(2)"),
]


@pytest.mark.parametrize("label,code", LEGIT, ids=[c[0] for c in LEGIT])
def test_legitimate_code_runs(df, label, code):
    result, chart, err = run_generated_code(code, df)
    assert err is None, f"정상 코드가 막혔다 ({label}): {err}"
    assert result is not None


def test_chart_df_is_returned(df):
    code = "chart_df = df.groupby('b')['a'].sum().to_frame()\nresult = chart_df"
    result, chart, err = run_generated_code(code, df)
    assert err is None and chart is not None


def test_allowed_to_list_has_no_writers():
    """allowlist에 실수로 writer가 들어가면 실패시킨다."""
    leaky = {"to_csv", "to_excel", "to_json", "to_pickle", "to_html",
             "to_string", "to_markdown", "to_latex", "to_sql", "to_parquet"}
    assert not (ALLOWED_TO & leaky), f"allowlist에 writer 혼입: {ALLOWED_TO & leaky}"


def test_syntax_error_reported_not_raised():
    assert "syntax error" in (check_generated_code("result = (") or "")


# ── 속성 쓰기로 facade 를 영구 오염시키던 회귀 (2026-07-29) ──────────
# 정적 검사가 Load/Store 를 구분하지 않아 `pd.to_numeric = len` 이 통과했고,
# PD_FACADE 가 모듈 전역 싱글턴이라 그 오염이 **이후 모든 실행**에 남았다.
# 권한 상승은 아니지만 컨테이너 재시작 전까지 지속되는 DoS다.
ATTRIBUTE_WRITES = [
    "pd.to_numeric = len\nresult = 1",
    "pd.DataFrame = None\nresult = 1",
    "df.attrs = {}\nresult = 1",
    "del pd.to_numeric\nresult = 1",
]


@pytest.mark.parametrize("code", ATTRIBUTE_WRITES)
def test_attribute_writes_are_blocked(code):
    assert check_generated_code(code) is not None, code


def test_facade_is_not_shared_between_runs():
    """정적 검사가 뚫려도 오염이 이 호출 안에서 끝나야 한다(2중 방어)."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    run_generated_code("result = pd.to_numeric(df['a']).sum()", df)
    _, _, err = run_generated_code("result = pd.to_numeric(df['a']).sum()", df)
    assert err is None, f"두 번째 실행이 오염됐다: {err}"


# ── 정지 문제: while 만 막으면 range 로 그대로 재현된다 ──────────────
UNBOUNDED_LOOPS = [
    "for i in range(10**12):\n    pass\nresult = 1",
    "result = sum(1 for _ in range(10**12))",
    "result = [i for i in range(999999999)]",
]


@pytest.mark.parametrize("code", UNBOUNDED_LOOPS)
def test_unbounded_range_is_blocked(code):
    assert check_generated_code(code) is not None, code


def test_small_range_still_works():
    """상한 자체가 목적이 아니다 — 작은 리터럴 range 는 통과해야 한다."""
    assert check_generated_code("result = list(range(5))") is None


# --- 속성 쓰기: 과차단 교정 (2026-07-30) --------------------------------------
#
# 전면 금지였다가, 데모 리허설에서 `chart_df.columns = [...]` 이 실행 전에 막혔다.
# 그건 LLM 이 표를 만들 때 늘 쓰는 정상 코드다. 더 나쁜 건 실패 모드였다 —
# 페이지가 RAG 로 폴백했고, 폴백은 집계 질문에 검색된 일부 행만 보고
# **조용히 틀린 평균**을 냈다. 막는 쪽이 안전하다는 가정이 여기선 틀렸다.
#
# 원래 위협(`pd.to_numeric = len` 이 프로세스 전역 파사드를 오염)은 이미 런타임에서
# 닫혀 있다 — 파사드를 호출마다 새로 만들고 df 는 copy 를 넘긴다. 정적 금지는
# 그 위의 2중 방어이므로, 방어가 실제로 필요한 지점만 남긴다.

ATTR_WRITES_ALLOWED = [
    "chart_df.columns = ['Study', 'Mean']",
    "df.index = [1, 2, 3]",
    "s.name = 'x'",
]

ATTR_WRITES_BLOCKED = [
    "pd.to_numeric = len",      # 원래 위협. to_numeric 은 ALLOWED_TO 라 to_* 검사로는 안 걸린다
    "pd.read_csv = 1",          # 주입된 이름의 다른 속성
    "chart_df.evil = 1",        # 허용 목록 밖
    "a.b.c = 1",                # 중첩 베이스 — 무엇에 쓰는지 정적으로 모른다
    "del df.columns",           # Store 만 허용, Del 은 계속 거부
    "x.__class__ = 1",          # dunder 는 쓰기 규칙 이전에 걸린다
]


@pytest.mark.parametrize("code", ATTR_WRITES_ALLOWED)
def test_local_attribute_writes_are_allowed(code):
    assert check_generated_code(code) is None, code


@pytest.mark.parametrize("code", ATTR_WRITES_BLOCKED)
def test_protected_and_unlisted_attribute_writes_stay_blocked(code):
    assert check_generated_code(code) is not None, code


def test_facade_rebinding_cannot_leak_between_runs(df):
    """정적 검사가 뚫려도 오염이 다음 실행으로 안 넘어가는지 — 2중 방어의 아래층."""
    from codeguard import PandasFacade
    a, b = PandasFacade(), PandasFacade()
    a.to_numeric = len
    assert b.to_numeric is not len, "파사드가 호출 간에 공유되고 있다"
