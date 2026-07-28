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

여전히 샌드박스가 아니다: 타임아웃도, 메모리 상한도, 프로세스 격리도 없다.
'축소된 권한의 네임스페이스'이고 README에도 그렇게 적혀 있다.
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


PD_FACADE = PandasFacade()

# pandas 자체 표현식 평가기(eval)와 Styler(style → to_html/to_excel/to_latex 재노출)를 막는다.
BANNED_ATTRS = frozenset({"eval", "style"})

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
        if isinstance(node, ast.Attribute):
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
    local_vars = {"df": df.copy(), "pd": PD_FACADE}
    try:
        exec(code, {"__builtins__": SAFE_BUILTINS}, local_vars)
    except Exception as e:  # noqa: BLE001
        return None, None, str(e)
    return (local_vars.get("result", "Could not produce a result."),
            local_vars.get("chart_df"), None)
