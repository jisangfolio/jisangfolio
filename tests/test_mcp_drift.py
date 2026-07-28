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

    - 62%→94%: 재현 불가라 '골든셋 10/16→15/16'으로 정정한 수치
    - Kubeflow: 사용 경험 없음
    - 전화번호: 공개 산출물에서 제거한 개인정보
    """
    assert "62%" not in MCP_SRC and "94%" not in MCP_SRC, "정정한 62→94 수치가 MCP에 남아 있음"
    assert "Kubeflow" not in MCP_SRC, "미사용 기술(Kubeflow)이 MCP에 있음"
    assert not re.search(r"01[016][- ]?\d{3,4}[- ]?\d{4}", MCP_SRC), "MCP에 전화번호가 있음"


def test_graphrag_naming_is_qualified():
    """'GraphRAG'를 쓰더라도 Microsoft GraphRAG가 아님을 밝혀야 한다."""
    if "GraphRAG" in MCP_SRC:
        assert "not Microsoft GraphRAG" in MCP_SRC, \
            "GraphRAG를 단서 없이 주장하고 있음 (실체는 어휘 시드 + 1-hop 탐색)"
