"""codeguard.py 회귀 테스트 — LLM 생성 코드의 실행 경계.

이 리포에서 가장 위험한 코드다. 실제로 두 번 뚫렸고 둘 다 여기 케이스로 박아둔다:

  1. `pd` 모듈을 그대로 넘겨 `pd.io.common.os.popen(...)` 으로 임의 명령 실행이 됐다.
     배포 컨테이너엔 Groq 키·GCP 개인키·SMTP 자격증명·비공개 이력서가 있었다.
  2. 쓰기 메서드를 열거해 막았더니 `to_string(buf=)`·`to_html(buf=)`·
     `to_markdown(buf=)`·`df.style.to_html(path)` 로 파일이 그대로 써졌다.

그래서 이 테스트는 "막혔는가"만 보지 않고 **실제로 디스크에 파일이 생겼는지**까지 본다.
"""
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
    ("dunder 이름",       "result = __import__('os').getcwd()"),
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
