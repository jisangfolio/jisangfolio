"""입력 가드레일 레이어 (프로그램적).

챗봇 페르소나 프롬프트의 스코프 규칙 위에, 코드 레벨의 결정적 가드를 한 겹 더 둔다.
프롬프트만으로는 못 막는 프롬프트 인젝션·과길이·빈입력을 LLM 호출 전에 차단한다.
(Guardrails AI · NeMo Guardrails · LlamaGuard 계열의 경량 자체 구현 — LLM 판정 가드로 확장 가능.)
"""
import re

# 프롬프트 인젝션 / 탈옥 시도 패턴
_INJECTION = re.compile(
    r"(ignore\s+(all|any|the|your|previous|above|prior)[\s\w]{0,24}(instruction|prompt|rule)"
    r"|disregard\s+(the|your|all|previous)"
    r"|system\s+prompt"
    r"|you\s+are\s+now\b"
    r"|pretend\s+to\s+be"
    r"|act\s+as\s+(a|an|if)"
    r"|jailbreak|DAN\s+mode"
    r"|forget\s+(your|the|all|everything|previous)"
    r"|reveal\s+(your|the)\s+(prompt|instruction|system))",
    re.IGNORECASE,
)

MAX_LEN = 2000


def check_input(text: str) -> dict:
    """사용자 입력을 검사해 판정을 반환한다.

    return: {"allowed": bool, "category": str, "reason": str}
    category ∈ {ok, empty, too_long, prompt_injection}
    """
    text = (text or "").strip()
    if not text:
        return {"allowed": False, "category": "empty", "reason": "Empty input."}
    if len(text) > MAX_LEN:
        return {"allowed": False, "category": "too_long",
                "reason": f"Input too long ({len(text)} chars, max {MAX_LEN})."}
    if _INJECTION.search(text):
        return {"allowed": False, "category": "prompt_injection",
                "reason": "Looks like a prompt-injection / jailbreak attempt — blocked before reaching the model."}
    return {"allowed": True, "category": "ok", "reason": "Passed input guardrails."}


def blocked_message(verdict: dict, lang: str = "English") -> str:
    """차단 시 사용자에게 보여줄 박지상 톤의 안내."""
    if verdict["category"] == "prompt_injection":
        return ("음, 그건 제 시스템 지시를 바꾸려는 시도로 보이네요 :) 저는 박지상의 경력·프로젝트에 대해서만 답합니다."
                if lang == "한국어" else
                "Hmm, that looks like an attempt to override my instructions :) I only answer about Jisang's experience and projects.")
    if verdict["category"] == "too_long":
        return ("질문이 너무 길어요. 조금 줄여서 다시 물어봐 주세요." if lang == "한국어"
                else "That's a bit long — please shorten it and ask again.")
    return ("질문을 입력해 주세요." if lang == "한국어" else "Please type a question.")
