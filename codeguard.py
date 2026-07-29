"""LLM이 생성한 pandas 코드를 실행하기 위한 축소 권한 네임스페이스.

이 모듈이 **보안 경계**다. 원래 `pages/2_Data_Analysis.py` 안에 인라인으로 있었는데,
Streamlit 페이지는 import 시점에 `st.set_page_config()` 등을 실행해서 테스트가 불러올 수
없다 — 즉 리포에서 가장 위험한 코드에 회귀 테스트가 하나도 못 붙어 있었다.
`tests/test_codeguard.py`가 붙도록 분리했다.

설계 원칙 세 가지:

1. **`pandas` 모듈을 절대 넘기지 않는다.** 모듈 객체는 어떤 builtins allowlist도 우회하는
   통로다 — `pd.io.common.os.popen(...)`은 OS에 닿고 `pd.io.common.__builtins__`는
   builtins 사전을 통째로 돌려준다. 그래서 `pd`는 프롬프트가 요구하는 최상위 헬퍼만
   노출하는 facade다.
2. **dunder 접근을 정적으로 거부한다.** `__class__`/`__globals__`/`__subclasses__`가
   없으면 평범한 객체(DataFrame)는 막다른 길이다.
3. **쓰기 계열은 denylist가 아니라 allowlist다.** 처음엔 `to_csv`·`to_excel` 등 14개를
   열거해 막았는데 `to_string(buf=)`·`to_html(buf=)`·`to_markdown(buf=)`·
   `df.style.to_html(path)`로 파일이 그대로 써졌다. pandas가 writer를 추가하면 열거형
   denylist는 그날로 뚫린다 → **아는 것만 허용**한다.
4. **속성 탐색을 대신해 주는 함수도 막는다.** AST는 `Attribute`/`Name` 노드만 보므로
   문자열 리터럴 *안*의 dunder는 원칙 2를 그냥 지나간다. 그리고 `str.format`은 실행
   시점에 그 문자열을 읽어 대신 속성을 타 준다:

       result = '{0.__class__.__init__.__globals__[sys].modules[os].environ}'.format(df)

   정적 검사를 통과하고 프로세스 환경변수 전체를 돌려줬다(재현 확인). 배포 컨테이너엔
   Groq 키·GCP 개인키·SMTP 자격증명이 있으므로 이건 자격증명 유출 프리미티브다.
   → 문자열 리터럴에 `__`가 있으면 정적 거부 + `format`/`format_map`을 금지 속성으로.
   `df.query`도 `df.eval`과 같은 pandas 표현식 엔진이라 함께 막는다(원래 누락).

5. **속성 쓰기를 거부한다.** 정적 검사가 Load/Store를 구분하지 않던 시절엔
   `pd.to_numeric = len` 이 통과했고, facade가 프로세스 전역 싱글턴이라 그 오염이
   컨테이너 재시작 전까지 **이후 모든 방문자**에게 남았다. 권한 상승은 아니지만
   지속성 있는 DoS다 → Store/Del 컨텍스트 거부 + facade를 호출마다 새로 생성.

여전히 샌드박스가 아니다: 메모리 상한도 프로세스 격리도 없다. 정지 문제는 `while`
금지에 더해 **상한 없는 `range()` 거부**로 구멍을 좁혔지만(벡터화 pandas만 요구하는
codegen 프롬프트에 정당한 용례가 없다), `df.apply` 로 큰 프레임을 도는 식의 느린
경로는 여전히 남는다 — 스레드에서 도는 Streamlit 스크립트라 `signal.alarm`이 안 먹고,
제대로 고치려면 별도 프로세스 + 벽시계 타임아웃 + `setrlimit`이 필요하다. 다만 그
비용이 만만치 않다(fork는 Streamlit의 멀티스레드 프로세스에서 교착 위험, spawn은
매 질의마다 DataFrame 피클링 + 인터프리터 기동). 지금은 입력 크기 쪽에서
`maxUploadSize`(10MB)와 인덱싱 행 상한으로 bound를 걸어두고, 이 모듈은
'축소된 권한의 네임스페이스'로 남긴다 — README에도 그렇게 적혀 있다.
"""
import ast

import pandas as pd

# codegen 프롬프트가 실제로 요구하는 최상위 pandas 헬퍼만.
_ALLOWED_PD = (
    "to_numeric", "to_datetime", "to_timedelta", "isna", "notna",
    "concat", "merge", "cut", "qcut", "pivot_table", "crosstab",
    "DataFrame", "Series", "date_range", "NA", "NaT",
)


class PandasFacade:
    """`pandas` 모듈이 아니라, 필요한 최상위 함수만 담은 얇은 객체."""

    def __init__(self):
        for name in _ALLOWED_PD:
            setattr(self, name, getattr(pd, name))


# range() 인자로 허용할 리터럴 상한. `range(10**12)` 하나로 워커가 그대로 멈춘다.
_MAX_RANGE = 100_000

# pandas 자체 표현식 평가기(eval·query)와 Styler(style → to_html/to_excel/to_latex 재노출),
# 그리고 실행 시점에 문자열을 읽어 속성 탐색을 대신해 주는 str.format 계열을 막는다(§4).
BANNED_ATTRS = frozenset({"eval", "query", "style", "format", "format_map"})

# to_* 중 **읽기/변환만** 허용. 나머지 to_* 는 전부 거부된다(§3 원칙).
ALLOWED_TO = frozenset({
    "to_numeric", "to_datetime", "to_timedelta", "to_period", "to_timestamp",
    "to_frame", "to_series", "to_dict", "to_list", "to_numpy", "to_records",
})

# 주의: numpy 배열 메서드(예: `df['a'].to_numpy().mean()`)는 numpy 내부가 `__import__`를
# 쓰기 때문에 여기서 실패한다. `__import__`를 열어주면 격리가 통째로 무너지므로 열지 않는다.
# pandas 연산(`df['a'].mean()`)은 정상 동작하고, 실패 시 페이지는 RAG로 폴백한다.
SAFE_BUILTINS = {
    "len": len, "sum": sum, "min": min, "max": max, "round": round,
    "sorted": sorted, "list": list, "dict": dict, "set": set, "tuple": tuple,
    "str": str, "int": int, "float": float, "bool": bool, "abs": abs,
    "enumerate": enumerate, "zip": zip, "range": range, "type": type,
    "isinstance": isinstance, "True": True, "False": False, "None": None,
    "print": lambda *a, **kw: None,
}


def check_generated_code(code: str):
    """생성 코드의 정적 AST 검사. 실행하면 안 되는 이유(str), 통과면 None."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"syntax error: {e.msg}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return "imports are not allowed"
        # §4: 문자열 리터럴 안의 dunder. AST는 여기를 안 보는데 str.format 이 실행 시점에
        # 대신 읽어서 속성을 타 준다. 정당한 pandas 코드에 "__" 리터럴이 나올 일은 없다.
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "__" in node.value:
                return "dunder inside a string literal is not allowed"
        # 타임아웃이 없으므로(스레드라 signal.alarm 불가) 무한루프는 워커를 그대로 멈춘다.
        # 벡터화 pandas 를 요구하는 codegen 프롬프트에 while 의 정당한 용례가 없다.
        if isinstance(node, ast.While):
            return "while loops are not allowed"
        # while 만 막으면 `for i in range(10**12)` 로 같은 정지가 그대로 재현된다.
        # 상한 없는 range 를 거부해 while 금지와 구멍을 맞춘다 — 벡터화 pandas 를
        # 요구하는 codegen 프롬프트엔 큰 range 의 정당한 용례가 없고, 거부되면
        # 페이지가 RAG 로 폴백하므로 실패 모드도 안전하다.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            for arg in node.args:
                if not (isinstance(arg, ast.Constant) and isinstance(arg.value, int)
                        and abs(arg.value) <= _MAX_RANGE):
                    return "range() needs small literal bounds here (use vectorized pandas)"
        if isinstance(node, ast.Attribute):
            # 속성 **쓰기** 금지. 정적 검사는 Load/Store 를 구분하지 않아서
            # `pd.to_numeric = len` 이 통과했고, PD_FACADE 가 프로세스 전역 싱글턴이라
            # 그 오염이 컨테이너 재시작 전까지 **이후 모든 방문자**에게 남았다.
            # (권한 상승은 아니지만 지속성 있는 DoS다.)
            if not isinstance(node.ctx, ast.Load):
                return f"attribute assignment is not allowed ({node.attr})"
            if node.attr.startswith("__"):
                return f"dunder attribute access is not allowed ({node.attr})"
            if node.attr in BANNED_ATTRS:
                return f"attribute is not allowed ({node.attr})"
            if node.attr.startswith("to_") and node.attr not in ALLOWED_TO:
                return f"writer-style attribute is not allowed ({node.attr})"
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            return f"dunder name is not allowed ({node.id})"
    return None


def run_generated_code(code: str, df):
    """정적 검사 통과 시 축소 네임스페이스에서 실행. (result, chart_df, error) 반환."""
    reason = check_generated_code(code)
    if reason:
        return None, None, f"blocked before execution: {reason}"
    # facade 도 호출마다 새로 만든다. 예전엔 모듈 전역 싱글턴을 그대로 넘겨서,
    # 정적 검사를 통과한 속성 재바인딩 한 줄이 이후 모든 실행에 남았다.
    # (정적 Store 금지와 2중 방어 — 어느 한쪽이 뚫려도 오염이 이 호출 안에서 끝난다.)
    local_vars = {"df": df.copy(), "pd": PandasFacade()}
    try:
        exec(code, {"__builtins__": SAFE_BUILTINS}, local_vars)
    except Exception as e:  # noqa: BLE001
        return None, None, str(e)
    return (local_vars.get("result", "Could not produce a result."),
            local_vars.get("chart_df"), None)
