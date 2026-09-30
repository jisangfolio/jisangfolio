"""전 직장 반출선(§8) — **리포 전체**를 훑는다.

`find_retired` 는 챗봇이 1인칭으로 말하는 네 표면만 본다(resume_text · 프로필 그래프
노드 · MCP 소스 · 홈 문자열). 그건 "틀린 주장"을 잡기엔 맞는 범위지만, **맞는 주장인데
내보내면 안 되는 것**에는 좁다 — 이 리포는 공개 저장소라 주석·독스트링·문서도 그대로
나간다.

실제로 그래서 샜다: `pages/4_MLOps_Docs.py` 독스트링에 사내 시스템 이름이 7월부터
있었는데, 화면에도 챗봇 근거에도 안 나와서 네 표면 검사를 전부 통과했다(2026-09-30
외부 검토가 소스를 직접 읽고 발견).

여기서는 **재현 가능성이 걸린 소수 항목만** 본다. 표현 교정은 retired_claims 의 몫이다.
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# (패턴, 사유) — 좁게 유지한다. 넓히면 정직한 설명까지 잡혀 아무도 안 고치게 된다.
EXPORT_LINE = [
    (r"U-?Ecotron|부경대|PKNU|송산\s*그린시티|Songsan", "협력 기관·테스트베드 실명"),
    (r"\bKAigen\b", "사내 시스템 이름"),
    (r"\b(model_gate|alert_check|onnx_export|onnx_validate|onnx_deploy|portal_restart)\.ya?ml\b"
     r"|\bmlops\.ya?ml\b", "전 직장 워크플로 파일명"),
    (r"(콘솔|console)[^\n]{0,30}(로그인\s*없|인증(이)?\s*없|no\s+\w*\s*auth|접근\s*(제어|권한)|access\s+control)",
     "미조치 접근 통제 상태"),
    (r"root\s+disk\s+at\s+\d|디스크\s*9\d\s*%", "미조치 용량 상태"),
    (r"mlops_grafana", "내부 대시보드 캡처"),
]

# 이 파일들은 **금지어 목록 자체**이거나 왜 금지인지 적은 자리다.
EXEMPT = {"tests/test_export_line.py", "tests/retired_claims.py"}
TEXT_SUFFIX = {".py", ".md", ".toml", ".jsonl", ".yml", ".yaml", ".sh", ".txt"}


def _tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    for rel in out.stdout.split("\n"):
        if not rel or rel in EXEMPT:
            continue
        p = ROOT / rel
        if p.suffix in TEXT_SUFFIX and p.exists():
            yield rel, p


def test_no_export_line_violations_anywhere_in_the_repo():
    if not list(_tracked()):
        pytest.skip("git ls-files 결과 없음")
    bad = []
    for rel, p in _tracked():
        text = p.read_text(encoding="utf-8", errors="replace")
        for pat, why in EXPORT_LINE:
            for m in re.finditer(pat, text):
                line = text[: m.start()].count("\n") + 1
                bad.append(f"{rel}:{line}  {m.group(0)!r} — {why}")
    assert not bad, "반출선 위반:\n" + "\n".join(bad)
