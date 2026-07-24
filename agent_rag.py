"""Agentic RAG 루프 — 검색을 한 번에 끝내지 않고 스스로 판단·재시도하는 L3 에이전트.

루프:
  ① 검색(retrieve)
  ② 관련성 평가(grade) — 검색 결과가 질문에 충분한가? (YES/NO)
  ③ 부실하면 쿼리 재작성(rewrite) + 재검색  ← 자기교정 (교차언어·키워드 보강)
  ④ 근거 기반 생성(generate) + 인용
  ⑤ 근거 자기점검(self-check) — 답이 컨텍스트로 뒷받침되나? (faithfulness)

각 단계를 trace로 남겨 "에이전트가 스스로 판단하고 재시도했다"를 눈으로 보여준다.
이 다단계 루프가 단방향 RAG(L1)와 에이전트(L3)를 가르는 지점.
"""
from langchain_core.prompts import ChatPromptTemplate

from prompts import (
    RAG_ANSWER_PROMPT_TEMPLATE,
    RAG_GRADE_PROMPT_TEMPLATE,
    RAG_REWRITE_PROMPT_TEMPLATE,
    RAG_GROUNDEDNESS_PROMPT_TEMPLATE,
    clean_response,
)
from rag_corpus import format_context


def _ask(llm, template, **variables) -> str:
    """프롬프트 1회 호출 → 후처리된 텍스트."""
    return clean_response((ChatPromptTemplate.from_template(template) | llm).invoke(variables).content)


def _yesno(llm, template, **variables) -> str:
    """YES/NO 판정을 결정적으로 파싱."""
    out = _ask(llm, template, **variables).upper()
    return "YES" if "YES" in out else "NO"


def _rewrite(llm, question: str) -> str:
    """검색용 쿼리 재작성 — 첫 비어있지 않은 줄만."""
    out = _ask(llm, RAG_REWRITE_PROMPT_TEMPLATE, question=question)
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
    for attempt in range(max_retries + 1):
        grade = _yesno(llm, RAG_GRADE_PROMPT_TEMPLATE, question=question, context=format_context(chunks))
        trace.append({"step": "grade", "detail": f"relevant = {grade}"})
        if grade == "YES" or attempt == max_retries:
            break
        # 부실 → 쿼리 재작성 후 재검색 (자기교정)
        query = _rewrite(llm, question)
        rewrote = True
        trace.append({"step": "rewrite", "detail": query})
        chunks = retriever.invoke(query)
        trace.append({"step": "retrieve", "detail": f"\"{query[:60]}\" → {len(chunks)} chunks"})

    # 생성
    ctx = format_context(chunks)
    answer = _ask(llm, RAG_ANSWER_PROMPT_TEMPLATE, context=ctx, question=question)
    trace.append({"step": "generate", "detail": f"{len(answer)} chars"})

    # 근거 자기점검 (faithfulness)
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
                   reasoning_effort="none", max_tokens=1500)

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
