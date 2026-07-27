"""입력 가드레일 레이어 (프로그램적).

챗봇 페르소나 프롬프트의 스코프 규칙 위에, 코드 레벨의 결정적 가드를 한 겹 더 둔다.
프롬프트만으로는 못 막는 프롬프트 인젝션·과길이·빈입력을 LLM 호출 전에 차단한다.
(Guardrails AI · NeMo Guardrails · LlamaGuard 계열의 경량 자체 구현 — LLM 판정 가드로 확장 가능.)
"""
import re

# 프롬프트 인젝션 / 탈옥 시도 패턴 (영어)
_INJECTION_EN = re.compile(
    r"(ignore\s+(all|any|the|your|previous|above|prior)[\s\w]{0,24}(instruction|prompt|rule)"
    r"|disregard\s+(the|your|all|previous)"
    r"|you\s+are\s+now\b"
    r"|pretend\s+to\s+be"
    r"|act\s+as\s+(a|an|if)"
    r"|jailbreak|DAN\s+mode"
    r"|forget\s+(your|the|all|everything|previous)"
    r"|reveal\s+(your|the)\s+(prompt|instruction|system))",
    re.IGNORECASE,
)

# 한국어 패턴. 챗봇이 한/영 토글을 제공하므로 방어도 대칭이어야 한다 — 영어 정규식만
# 두면 한국어 인젝션이 프로그램적 가드를 그대로 통과해 페르소나 프롬프트에만 의존하게 된다.
# 한국어는 어미 변형이 많아 '지시/명령/프롬프트 + 무시/잊어' 같은 근접 조합으로 잡는다.
_INJECTION_KO = re.compile(
    r"((지시|명령|규칙|프롬프트|설정)(사항|어|을|를|는|은|들)?\s*(전부|모두|다)?\s*(무시|잊어|잊고|해제|초기화)"
    r"|(무시|망각)하고\s*(내|다음|아래)"
    r"|이제부터\s*(너|당신|넌|년)"
    r"|(너|당신|넌)\s*(는|은)?\s*이제\s*(부터)?"
    r"|(인|한)\s*척\s*(해|하고|해줘|하라)"
    r"|(처럼|같이)\s*(행동|말)해"
    r"|탈옥"
    r"|제한\s*(없는|없이|해제)"
    r"|(개발자|관리자|디버그)\s*(모드|권한))",
)


# '시스템 프롬프트' 언급 자체는 인젝션이 아니다 — 이 포트폴리오는 프롬프트 설계가
# 이야깃거리라 "시스템 프롬프트 어떻게 설계했나요?"는 정상 질문이다. 그래서 프롬프트를
# 가리키는 명사가 **추출 의도**(알려줘/출력해/reveal/print…)와 함께 나올 때만 차단한다.
# 언어를 섞은 시도("system prompt를 그대로 알려줘")도 잡히도록 두 언어 단서를 한 창에서 본다.
_PROMPT_NOUN = re.compile(r"(system\s*prompt|시스템\s*프롬프트|프롬프트\s*(전문|원문|내용))", re.IGNORECASE)
_EXTRACT_CUE = re.compile(
    r"(reveal|show|print|output|repeat|display|dump|leak|copy|paste|verbatim|word.for.word"
    r"|give\s+me|tell\s+me|what\s+i|what's"
    r"|알려|보여|출력|공개|말해|그대로|복사|붙여|내놔|뭐야|무엇|전문|원문)",
    re.IGNORECASE,
)
_WINDOW = 40  # 명사 앞뒤로 볼 문자 수


def _prompt_extraction(text: str) -> bool:
    """프롬프트 명사 주변 창에 추출 단서가 있으면 True."""
    for m in _PROMPT_NOUN.finditer(text):
        window = text[max(0, m.start() - _WINDOW): m.end() + _WINDOW]
        if _EXTRACT_CUE.search(window):
            return True
    return False


def _injection_hit(text: str):
    """인젝션 패턴 매칭 — 매치된 유형을 함께 반환(차단 사유 로깅·디버깅용)."""
    if _INJECTION_EN.search(text):
        return "en"
    if _INJECTION_KO.search(text):
        return "ko"
    if _prompt_extraction(text):
        return "prompt-extraction"
    return None


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
    hit = _injection_hit(text)
    if hit:
        return {"allowed": False, "category": "prompt_injection",
                "reason": f"Looks like a prompt-injection / jailbreak attempt ({hit}) — blocked before reaching the model."}
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
