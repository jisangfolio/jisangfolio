"""검색 계층 자기진단 — 임베딩 절단률·코퍼스 구성·교차언어 검색 실패를 실측한다.

이 스크립트의 목적은 성능 자랑이 아니라 **자기 시스템의 결함을 수치로 확정**하는 것이다.
측정 대상:
  ① 청크가 임베딩 인코더(all-MiniLM-L6-v2, max_seq_length=256 word pieces)에서
     얼마나 잘리는가 — 전체/한국어/영어 청크별 절단률과 평균 도달률
  ② 코퍼스 구성 — 문서별 청크 점유율(단일 문서 편중도)
  ③ 교차언어 검색 — 영어 질의가 한국어 목표 문서를 top-k에 올리는가

사용:  python retrieval_probe.py
"""
import re
from collections import Counter

from rag_corpus import load_corpus, build_retriever

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MAX_SEQ = 256  # 모델 카드 기준 max_seq_length (word pieces)

_HANGUL = re.compile(r"[가-힣]")


def is_korean(text, ratio=0.10):
    """한글 문자 비율이 임계 이상이면 한국어 청크로 본다."""
    if not text:
        return False
    return sum(bool(_HANGUL.match(c)) for c in text) / len(text) >= ratio


def main():
    print("=" * 74)
    print("검색 계층 자기진단 (retrieval probe)")
    print("=" * 74)

    corpus = load_corpus()
    print(f"\n[코퍼스] 총 {len(corpus)} 청크")

    # ── ② 코퍼스 구성 ────────────────────────────────────────────
    by_src = Counter(d.metadata["source_file"] for d in corpus)
    print("\n[② 문서별 점유율]")
    for src, n in by_src.most_common():
        print(f"   {n:4d} 청크  {100*n/len(corpus):5.1f}%   {src}")
    top_share = 100 * by_src.most_common(1)[0][1] / len(corpus)
    print(f"   → 최대 단일 문서 점유율: {top_share:.1f}%")

    # ── ① 절단률 ────────────────────────────────────────────────
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL)

    rows = []
    for d in corpus:
        n_tok = len(tok.tokenize(d.page_content))
        rows.append((n_tok, is_korean(d.page_content)))

    def stats(subset, label):
        if not subset:
            print(f"   {label}: 해당 없음")
            return
        trunc = [n for n, _ in subset if n > MAX_SEQ]
        reach = [min(n, MAX_SEQ) / n for n, _ in subset]  # 인코더에 도달한 토큰 비율
        print(f"   {label:12s} n={len(subset):4d} | 절단 {len(trunc):4d}건 "
              f"({100*len(trunc)/len(subset):5.1f}%) | 평균 도달률 {100*sum(reach)/len(reach):5.1f}% "
              f"| 중앙 토큰수 {sorted(n for n, _ in subset)[len(subset)//2]}")

    print(f"\n[① 임베딩 절단 — {MODEL}, max_seq_length={MAX_SEQ}]")
    stats(rows, "전체")
    stats([r for r in rows if r[1]], "한국어 청크")
    stats([r for r in rows if not r[1]], "영어 청크")

    # ── ③ 교차언어 검색 ──────────────────────────────────────────
    print("\n[③ 교차언어 검색 — 영어 질의 → 한국어 목표 문서(KETI)]")
    r = build_retriever(corpus, k=5)
    KETI = "keti_mlops_pipeline.md"
    probes = [
        "How does the on-prem pipeline serve models with Triton?",
        "What CI pipeline validates ONNX models before deployment?",
        "How is data drift monitored in the on-prem MLOps stack?",
        "How are model versions governed in the on-prem registry?",
        "What monitoring dashboards exist for inference metrics?",
    ]
    miss = 0
    for q in probes:
        hits = sum(1 for d in r.invoke(q) if d.metadata["source_file"] == KETI)
        if hits == 0:
            miss += 1
        print(f"   top-5 중 목표문서 {hits}건  | {q[:58]}")
    print(f"   → 영어 질의 {len(probes)}건 중 {miss}건에서 목표 한국어 문서가 top-5에 0건")

    print("\n" + "=" * 74)
    print("주의: n이 작다(질의 5건). 경향 진단이지 벤치마크가 아니다.")
    print("=" * 74)


if __name__ == "__main__":
    main()
