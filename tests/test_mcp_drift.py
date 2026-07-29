"""MCP 서버 내용이 프로필 SSOT와 어긋나면 실패시킨다.

jisangfolio_mcp.py 는 이력서를 하드코딩한 **2차 사본**이다(프로필 그래프 노드보다 서술이
상세해 자동 파생이 어렵다). 사본인 이상 원본과 갈라지는 건 시간 문제고, 실제로 갈라져 있었다 —
Agentic RAG·하이브리드 검색이 앱에는 있는데 MCP 스킬 목록에는 빠져 있었다.

이 테스트는 "MCP를 SSOT에서 자동 생성한다"의 대체물이다. 자동 생성만큼 강하진 않지만,
**두 소스가 공유하는 핵심 사실이 어긋나면 CI가 잡는다**. fastmcp 미설치 환경(CI)에서도
돌아야 하므로 모듈을 import 하지 않고 소스 텍스트를 읽는다.
"""
import re
from pathlib import Path

import profile_graph

ROOT = Path(__file__).resolve().parents[1]
MCP_SRC = (ROOT / "jisangfolio_mcp.py").read_text(encoding="utf-8")


def _graph_text() -> str:
    """프로필 그래프의 한/영 설명을 한 덩어리로."""
    return " ".join(
        f"{n.get('ko','')} {n.get('en','')} {n.get('desc_ko','')} {n.get('desc_en','')}"
        for n in profile_graph.NODES
    )


def test_core_stack_present_in_both():
    """앱이 내세우는 핵심 스택은 MCP 스킬 목록에도 있어야 한다."""
    graph = _graph_text()
    for term in ("Triton", "MLflow", "ONNX", "Gitea", "Prometheus", "Grafana", "FAISS", "LangChain"):
        assert term in graph, f"프로필 그래프에 없음: {term}"
        assert term in MCP_SRC, f"MCP 사본에 누락 — 드리프트: {term}"


def test_pipeline_features_present_in_mcp():
    """포트폴리오의 4개 파이프라인 특성이 MCP 서술에도 반영돼 있어야 한다.

    실제로 여기서 드리프트가 났었다(Agentic RAG·하이브리드 검색 누락).
    """
    for term in ("Agentic RAG", "Hybrid retrieval", "guardrails", "observability"):
        assert term.lower() in MCP_SRC.lower(), f"MCP 사본에 누락 — 드리프트: {term}"


def test_no_retired_claims():
    """폐기한 표현이 MCP에 되살아나지 않았는지.

    목록은 tests/retired_claims.py 가 소유한다 — 예전엔 이 함수가 자기 목록을 들고
    있었고, 그래서 같은 검사가 resume_text·profile_graph 에는 걸리지 않았다.
    """
    from retired_claims import find_retired

    hits = find_retired(MCP_SRC)
    assert not hits, "MCP 사본에 폐기된 주장이 있음:\n" + "\n".join(
        f"  · {m!r} — {why}" for m, why in hits)


def test_mcp_uses_the_shared_post_processing_helper():
    """후처리 사본이 앱과 다르게 굴던 회귀 (2026-07-29).

    MCP 는 </think> 를 직접 잘랐고, 그 사본이 두 경우에 앱과 갈라졌다:
      · 닫히지 않은 <think> → 앱은 "" / MCP 는 **사고 과정을 원문 그대로 노출**
      · 문장 중간 <think>   → 앱은 앞뒤 보존 / MCP 는 앞 문장을 통째로 삭제
    README 가 "MCP 서버는 후처리 헬퍼를 공유한다"고 적어둔 바로 그 지점이라
    소스 텍스트 수준에서 사본이 되살아나지 않게 고정한다.
    """
    from prompts import clean_response

    assert "clean_response(" in MCP_SRC, "MCP 가 공유 후처리 헬퍼를 안 쓴다"
    assert 'split("</think>"' not in MCP_SRC, "MCP 에 think 제거 사본이 되살아났다"

    # 사본이 틀렸던 바로 그 두 입력에서 공유 헬퍼가 어떻게 동작하는지도 못박는다.
    assert clean_response("<think>unclosed reasoning leaks") == ""
    assert "Intro sentence." in clean_response("Intro sentence. <think>secret</think> Rest.")


def test_graphrag_naming_is_qualified():
    """'GraphRAG'를 쓰더라도 Microsoft GraphRAG가 아님을 밝혀야 한다."""
    if "GraphRAG" in MCP_SRC:
        assert "not Microsoft GraphRAG" in MCP_SRC, \
            "GraphRAG를 단서 없이 주장하고 있음 (실체는 어휘 시드 + 1-hop 탐색)"
