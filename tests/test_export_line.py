"""전 직장 식별자 — **리포 전체**를 훑는다.

`find_retired` 는 챗봇이 1인칭으로 말하는 네 표면만 본다(resume_text · 프로필 그래프
노드 · MCP 소스 · 홈 문자열). 표현 교정에는 맞는 범위지만, **맞는 서술인데 내보내면
안 되는 것**에는 좁다 — 이 리포는 공개 저장소라 주석·독스트링·문서도 그대로 나간다.
실제로 한 모듈 독스트링이 그 경로로 오래 남아 있었고, 화면에도 챗봇 근거에도 안 떠서
네 표면 검사를 전부 통과했다(2026-09-30 외부 검토가 소스를 직접 읽고 발견).

금칙 토큰은 `tests/banned_tokens.py` 가 **해시로만** 들고 있다. 목록을 평문으로 적으면
목록이 곧 유출 지점이 되기 때문이다 — 그래서 이 파일도 예외 없이 스스로 검사 대상이다.
실패 메시지는 일치한 문자열을 찍지 않고 `파일:줄`까지만 알려준다. 공개 리포의 Actions
로그는 누구나 읽고, 고치는 사람은 자기 diff 에서 그 줄을 바로 본다.
"""
import subprocess
from pathlib import Path

import pytest

from banned_tokens import scan

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIX = {".py", ".md", ".toml", ".jsonl", ".yml", ".yaml", ".sh", ".txt", ".html"}


def _tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    for rel in out.stdout.split("\n"):
        p = ROOT / rel
        if rel and p.suffix in TEXT_SUFFIX and p.exists():
            yield rel, p


def test_no_prior_employer_identifiers_anywhere_in_the_repo():
    files = list(_tracked())
    if not files:
        pytest.skip("git ls-files 결과 없음 (git 없는 환경)")
    bad = [f"{rel}:{ln}" for rel, p in files
           for ln in scan(p.read_text(encoding="utf-8", errors="replace"))]
    assert not bad, (
        "전 직장 식별자로 등록된 토큰이 있다(해당 줄을 직접 확인할 것 — "
        "문자열은 로그에 남기지 않는다):\n  " + "\n  ".join(bad))


def test_the_scanner_is_actually_looking_at_files():
    """스캔이 공허하게 통과하지 않는지 — 파일을 못 읽으면 위 검사는 영원히 초록이다."""
    files = list(_tracked())
    if not files:
        pytest.skip("git 없는 환경")
    assert len(files) > 20, f"{len(files)}개 파일만 수집됨 — 수집이 깨졌을 가능성"


def test_the_scanner_catches_a_planted_token():
    """검출기가 살아 있는지 — 심어놓은 위반을 잡는지 해시로 확인한다."""
    import hashlib
    from banned_tokens import ASCII_DIGESTS
    probe = "zz-probe-token"
    assert hashlib.sha256(probe.encode()).hexdigest()[:16] not in ASCII_DIGESTS
    assert scan(f"line1\n{probe}\n") == [], "등록 안 된 토큰을 잡으면 오탐이다"
    # 등록된 토큰 하나를 해시로만 되짚어 탐지가 실제로 도는지 본다
    assert ASCII_DIGESTS, "ASCII 다이제스트가 비어 있다 — 검사가 무의미해진다"
