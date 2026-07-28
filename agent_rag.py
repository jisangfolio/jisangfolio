"""Agentic RAG 루프 — 검색을 한 번에 끝내지 않고 판단·재시도하는 자기교정 파이프라인.

수준 표기(정직): 자율 에이전트가 아니다. 판단 지점 3개(관련성·재작성 발동·근거점검),
그중 실제로 제어를 바꾸는 분기는 1개, 재시도 상한 1회로 경계가 명시된 L2 루프다.
도구 선택(function calling)·상태기계·계획 수립은 없다.

루프:
  ① 검색(retrieve)
  ② 관련성 평가(grade) — 검색 결과가 질문에 충분한가? (YES/NO)
  ③ 부실하면 쿼리 재작성(rewrite) + 재검색  ← 자기교정 (교차언어·키워드 보강)
  ④ 근거 기반 생성(generate) + 인용
  ⑤ 근거 자기점검(self-check) — 답이 컨텍스트로 뒷받침되나?

각 단계를 trace로 남겨 판단·재시도 과정을 눈으로 확인할 수 있게 한다.

알려진 한계(설계상 인지하고 남긴 것):
  · ⑤ 근거점검은 게이트가 아니라 라벨이다 — grounded=NO여도 답변은 이미 반환된다.
  · ③ 재작성은 이전 쿼리가 아니라 원본 질문을 다시 넘기므로 점진적 개선이 안 된다
    (그래서 재시도 상한 1이 실질적 한계).
  · ② 관련성 평가는 청크 세트 단위 1회 YES/NO이며, 나쁜 청크를 버리는 필터가 아니다.
  · 재검색 결과는 기존 검색 결과를 덮어쓴다(비교·병합 없음).
"""
import re
import time

from langchain_core.prompts import ChatPromptTemplate

from prompts import (
    RAG_ANSWER_PROMPT_TEMPLATE,
    RAG_GRADE_PROMPT_TEMPLATE,
    RAG_REWRITE_PROMPT_TEMPLATE,
    RAG_GROUNDEDNESS_PROMPT_TEMPLATE,
    clean_response,
)
from rag_corpus import format_context
from ratelimit import estimate_tokens, is_daily_limit, pacer_for, parse_wait_seconds


# Groq 무료 티어는 분당 토큰(TPM) 상한이 낮고, **요청한 max_tokens가 그대로 예약분으로
# 잡힌다**. 한 질문이 판정→(재작성)→생성→근거점검으로 3~4콜을 연달아 쏘므로, YES/NO 한
# 단어를 받자고 1500토큰을 예약하면 실제 사용량의 몇 배를 상한에 물린다 → 429.
# 그래서 호출 성격별로 출력 예산을 따로 준다(프롬프트가 '한 단어만' 지시하므로 안전).
_YESNO_TOKENS = 16
_REWRITE_TOKENS = 96
# 생성 예산도 여기서 고정한다 — 앱(pages/4)과 평가 하니스가 각자 ChatGroq을 만들기 때문에
# 호출부에 맡기면 둘이 갈라지고, 그러면 '평가가 앱을 대변한다'는 전제가 깨진다(앱만 길게
# 답하거나 평가만 잘리는 상황). 인용 포함 간결 답변 기준.
ANSWER_MAX_TOKENS = 768

_RATE_LIMITED = re.compile(r"rate.?limit|429", re.IGNORECASE)
# 폴백 백오프. TPM 버킷은 최대 60초까지 기다려야 회복될 수 있으므로 1·2·4·8초처럼
# 창보다 짧은 대기는 사실상 재시도를 포기하는 것과 같다(실측으로 확인).
_FALLBACK_WAITS = (10, 30, 60, 60)


def _invoke_with_retry(chain, variables, attempts: int = 5):
    """429면 서버가 알려준 대기시간만큼 쉬고 재시도. 일일 한도면 즉시 중단."""
    for i in range(attempts):
        try:
            return chain.invoke(variables)
        except Exception as e:  # noqa: BLE001 — 프로바이더 예외 타입에 의존하지 않는다
            if not _RATE_LIMITED.search(str(e)) or i == attempts - 1:
                raise
            if is_daily_limit(e):
                print("    · 일일 한도(TPD/RPD) 소진 — 기다려도 안 풀리므로 중단합니다")
                raise
            wait = parse_wait_seconds(e) or _FALLBACK_WAITS[min(i, len(_FALLBACK_WAITS) - 1)]
            wait = min(wait + 0.5, 90)
            print(f"    · rate limit — {wait:.1f}s 대기 후 재시도 ({i + 1}/{attempts - 1})")
            time.sleep(wait)


def _usage_tokens(resp, fallback: int) -> int:
    """응답에서 실제 사용 토큰을 꺼낸다(없으면 추정치)."""
    meta = getattr(resp, "usage_metadata", None) or {}
    total = meta.get("total_tokens") if isinstance(meta, dict) else None
    return int(total) if total else fallback


def _ask(llm, template, _max_tokens=None, **variables) -> str:
    """프롬프트 1회 호출 → 후처리된 텍스트. _max_tokens로 출력 예산을 좁힐 수 있다.

    호출 전 페이서에 예산을 신청하고(선제 대기), 호출 후 실제 사용량을 되먹인다.
    """
    prompt = ChatPromptTemplate.from_template(template)
    model = llm.bind(max_tokens=_max_tokens) if _max_tokens else llm

    rendered = prompt.format(**variables)
    need = estimate_tokens(rendered) + (_max_tokens or ANSWER_MAX_TOKENS)
    pacer = pacer_for(getattr(llm, "model_name", None) or str(getattr(llm, "model", "unknown")))
    pacer.wait_for(need)

    resp = _invoke_with_retry(prompt | model, variables)
    pacer.record(_usage_tokens(resp, need))
    return clean_response(resp.content)


def _yesno(llm, template, **variables) -> str:
    """YES/NO 판정을 결정적으로 파싱."""
    out = _ask(llm, template, _max_tokens=_YESNO_TOKENS, **variables).upper()
    return "YES" if "YES" in out else "NO"


def _rewrite(llm, question: str) -> str:
    """검색용 쿼리 재작성 — 첫 비어있지 않은 줄만."""
    out = _ask(llm, RAG_REWRITE_PROMPT_TEMPLATE, _max_tokens=_REWRITE_TOKENS, question=question)
    for line in out.splitlines():
        if line.strip():
            return line.strip()
    return question


def agentic_answer(llm, retriever, question: str, max_retries: int = 1) -> dict:
    """자기교정 RAG 루프 실행. return {answer, chunks, trace, grounded, rewrote}.

    trace: [{"step","detail"}] — UI가 에이전트의 단계를 그대로 렌더한다.
    """
    trace = []
    query = question
    chunks = retriever.invoke(query)
    trace.append({"step": "retrieve", "detail": f"\"{query[:60]}\" → {len(chunks)} chunks"})

    rewrote = False
    # 판정은 "재검색을 할까?"를 결정할 때만 부른다. 재시도 예산이 남아있지 않으면
    # 판정 결과가 제어를 바꿀 수 없으므로 호출하지 않는다 — 예전에는 마지막 회차에도
    # 판정을 불러 결과를 버렸고, 그건 답변에 영향 없이 LLM 호출만 한 번 더 쓰는 낭비였다.
    for attempt in range(max_retries):
        grade = _yesno(llm, RAG_GRADE_PROMPT_TEMPLATE, question=question, context=format_context(chunks))
        trace.append({"step": "grade", "detail": f"relevant = {grade}"})
        if grade == "YES":
            break
        # 부실 → 쿼리 재작성 후 재검색 (자기교정)
        query = _rewrite(llm, question)
        rewrote = True
        trace.append({"step": "rewrite", "detail": query})
        chunks = retriever.invoke(query)
        trace.append({"step": "retrieve", "detail": f"\"{query[:60]}\" → {len(chunks)} chunks"})

    # 생성
    ctx = format_context(chunks)
    answer = _ask(llm, RAG_ANSWER_PROMPT_TEMPLATE, _max_tokens=ANSWER_MAX_TOKENS, context=ctx, question=question)
    trace.append({"step": "generate", "detail": f"{len(answer)} chars"})

    # 근거 자기점검 — LLM에 YES/NO 이진 판정 1회. RAGAS faithfulness(claim 단위 분해·
    # 연속값)와는 다르며, 게이트가 아니라 라벨로만 쓴다(답변은 이미 생성됨).
    grounded = _yesno(llm, RAG_GROUNDEDNESS_PROMPT_TEMPLATE, answer=answer, context=ctx)
    trace.append({"step": "self_check", "detail": f"grounded = {grounded}"})

    return {"answer": answer, "chunks": chunks, "trace": trace, "grounded": grounded, "rewrote": rewrote}


# ── CLI 스모크 테스트: python agent_rag.py ───────────────────────────
if __name__ == "__main__":
    import tomllib
    from langchain_groq import ChatGroq
    from rag_corpus import build_retriever

    with open(".streamlit/secrets.toml", "rb") as f:
        key = tomllib.load(f)["groq_api_key"]

    print("검색기 구축(임베딩)...")
    r = build_retriever(k=5)
    llm = ChatGroq(model="qwen/qwen3.6-27b", groq_api_key=key, temperature=0,
                   reasoning_effort="none", max_tokens=ANSWER_MAX_TOKENS)

    for q in [
        "How does the on-prem pipeline detect data drift?",   # 영어 질문 → 한국어 KETI 문서 (재작성 유도)
        "What triggers retraining in an ML pipeline?",         # 클라우드 문서 (바로 충분)
        "Who won the 2022 World Cup?",                          # 코퍼스 밖 (거절)
    ]:
        res = agentic_answer(llm, r, q, max_retries=1)
        print("\n" + "=" * 74)
        print("Q:", q)
        print("  🔁 trace:")
        for s in res["trace"]:
            print(f"     {s['step']:10} | {s['detail']}")
        print("  💬 answer:", res["answer"][:280])
