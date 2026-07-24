"""MLOps 문서 코퍼스 로더 · 하이브리드 검색기 (Agentic RAG의 검색 계층).

rag_docs/ 안의 공식 MLOps 파이프라인 문서(Google/AWS/Azure/Vertex + 온프레 KETI)를
로드→헤딩 단위 청킹→임베딩(FAISS)+BM25 하이브리드 검색기로 만든다.

설계 포인트
- 청킹: 마크다운 헤딩(##/###) 단위로 먼저 나눠 "어느 문서·어느 섹션"을 메타데이터로
  보존(출처 인용의 근거). 긴 섹션만 1200자로 재분할.
- 검색: FAISS(dense, 의미) + BM25(sparse, 키워드)를 Reciprocal Rank Fusion으로 융합.
  pages/2_Data_Analysis.py의 HybridRetriever와 동일 패턴(일관성).
- 임베딩: sentence-transformers/all-MiniLM-L6-v2 (로컬, 외부 API 없음 — 온프레 철학).
"""
import os
import re
import glob

# 무거운 torch/faiss/embeddings 의존은 build_retriever 안에서 지연 임포트한다.

RAG_DIR = os.path.join(os.path.dirname(__file__), "rag_docs")


# ── 토크나이저 / RRF (2_Data_Analysis.py와 동일 구현) ──────────────
def _tok(s):
    return re.findall(r"[a-z0-9가-힣]+", (s or "").lower())


def _rrf(ranklists, k=5, c=60):
    """Reciprocal Rank Fusion — 여러 랭크 리스트를 하나로 융합."""
    scores, docmap = {}, {}
    for docs in ranklists:
        for rank, d in enumerate(docs):
            key = d.page_content
            scores[key] = scores.get(key, 0.0) + 1.0 / (c + rank + 1)
            docmap[key] = d
    top = sorted(scores, key=scores.get, reverse=True)[:k]
    return [docmap[key] for key in top]


class HybridRetriever:
    """dense(FAISS) + sparse(BM25) 하이브리드 검색, RRF 융합. .invoke(query) 인터페이스."""

    def __init__(self, vectorstore, splits, bm25, k=5):
        self.vs, self.splits, self.bm25, self.k = vectorstore, splits, bm25, k

    def invoke(self, query, k=None):
        k = k or self.k
        dense = self.vs.similarity_search(query, k=k * 3)
        scores = self.bm25.get_scores(_tok(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k * 3]
        sparse = [self.splits[i] for i in order]
        return _rrf([dense, sparse], k=k)


# ── 코퍼스 로딩 · 청킹 ────────────────────────────────────────────
_META_KEYS = ("source", "title", "url", "vendor", "topic")


def _parse_header(text: str) -> dict:
    """문서 상단의 <!-- key: value --> 메타데이터를 뽑는다."""
    meta = {}
    for key in _META_KEYS:
        m = re.search(rf"<!--\s*{key}:\s*(.*?)\s*-->", text, re.IGNORECASE)
        if m:
            meta[key] = m.group(1).strip()
    return meta


def load_corpus():
    """rag_docs/*.md 를 헤딩 단위로 청킹한 Document 리스트로 반환.

    각 청크 metadata: source_file, vendor, title, url, section(헤딩 경로).
    """
    from langchain_text_splitters import (
        MarkdownHeaderTextSplitter,
        RecursiveCharacterTextSplitter,
    )
    from langchain_core.documents import Document

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,   # 헤딩 텍스트를 본문에 남겨 문맥·BM25 키워드로 활용
    )
    char_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)

    docs = []
    for path in sorted(glob.glob(os.path.join(RAG_DIR, "*.md"))):
        raw = open(path, encoding="utf-8").read()
        fname = os.path.basename(path)
        hdr = _parse_header(raw)
        # <!-- ... --> 주석(메타 헤더) 제거 후 본문만 청킹
        body = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

        for sec in header_splitter.split_text(body):
            md = sec.metadata
            section_path = " > ".join(
                p for p in (md.get("h2"), md.get("h3")) if p
            ) or md.get("h1", "")
            for chunk in char_splitter.split_text(sec.page_content):
                if not chunk.strip():
                    continue
                docs.append(Document(
                    page_content=chunk,
                    metadata={
                        "source_file": fname,
                        "vendor": hdr.get("vendor", ""),
                        "title": hdr.get("title", fname),
                        "url": hdr.get("url", ""),
                        "section": section_path,
                    },
                ))
    return docs


def build_retriever(docs=None, k=5):
    """코퍼스 → FAISS+BM25 하이브리드 검색기. docs 미지정 시 load_corpus()."""
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from rank_bm25 import BM25Okapi

    docs = docs if docs is not None else load_corpus()
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(docs, embedding=embedding)
    bm25 = BM25Okapi([_tok(d.page_content) for d in docs])
    return HybridRetriever(vectorstore, docs, bm25, k=k)


# ── 인용/문맥 포맷 (생성 단계에서 사용) ──────────────────────────
def format_context(chunks) -> str:
    """검색된 청크를 번호+출처 태그가 붙은 컨텍스트 문자열로 조립."""
    parts = []
    for i, d in enumerate(chunks, 1):
        m = d.metadata
        loc = m.get("section") or m.get("title") or m.get("source_file")
        parts.append(f"[{i}] ({m.get('vendor', '?')} · {loc})\n{d.page_content}")
    return "\n\n".join(parts)


def source_lines(chunks):
    """UI 하단에 보여줄 출처 목록 (번호, vendor, 섹션, url)."""
    out = []
    for i, d in enumerate(chunks, 1):
        m = d.metadata
        out.append({
            "n": i,
            "vendor": m.get("vendor", ""),
            "section": m.get("section", ""),
            "source_file": m.get("source_file", ""),
            "url": m.get("url", ""),
        })
    return out


# ── CLI 스모크 테스트: python rag_corpus.py ───────────────────────
if __name__ == "__main__":
    print("코퍼스 로딩·청킹 중...")
    corpus = load_corpus()
    from collections import Counter
    by_src = Counter(d.metadata["source_file"] for d in corpus)
    print(f"\n총 청크: {len(corpus)}")
    for src, n in by_src.items():
        print(f"  {src}: {n} 청크")

    print("\n검색기 구축 중(임베딩)...")
    r = build_retriever(corpus, k=4)

    for q in [
        "What is MLOps level 1 pipeline automation?",
        "How does SageMaker Pipelines define pipeline steps?",
        "How did the on-prem KETI pipeline handle model serving with Triton?",
    ]:
        print("\n" + "=" * 70)
        print("Q:", q)
        for d in r.invoke(q):
            m = d.metadata
            print(f"  → [{m['vendor']} · {m['section'][:50]}] {d.page_content[:90].strip()}...")
