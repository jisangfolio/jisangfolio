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
# .json 은 평가 실행 기록(evals/runs/*.json)이 여기 해당한다. 지금은 깨끗하지만
# 다음 실행이 어떤 문자열을 담을지는 알 수 없으니 검사 대상에 둔다.
TEXT_SUFFIX = {".py", ".md", ".toml", ".json", ".jsonl", ".yml", ".yaml",
               ".sh", ".txt", ".html"}


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


def test_scanner_handles_token_boundaries():
    """경계에서 새던 것들을 고정한다 — 전부 같은 원인(토큰을 글자 그대로만 봤다).

    ⚠️ 여기서 **진짜 금칙어를 쓰면 이 테스트가 다시 유출 지점이 된다.** 그래서
    더미 단어의 다이제스트를 만들어 주입한다. scan() 이 digest 집합을 인자로
    받게 열어 둔 이유가 이것이다.
    """
    import hashlib

    def d(w):
        return hashlib.sha256(w.lower().encode()).hexdigest()[:16]

    ascii_set = {d("zzdummyorg"), d("zzdummy.yml"), d("zzdummyimg")}
    ko_set = {5: [d("가나다라마")]}

    cases = {
        "문장 끝 마침표": "앞 zzdummyorg. 뒤",
        "확장자+마침표": "앞 zzdummy.yml. 뒤",
        "이미지 경로": "![](assets/zzdummyimg.png)",
        "정규식 이스케이프": r'r"zzdummy\.yml"',
        "한글 조사": "가나다라마의 과제",
    }
    for label, text in cases.items():
        assert scan(text, ascii_digests=ascii_set, ko_by_len=ko_set), f"놓침: {label}"

    clean = "관련 없는 문장 abc.def 0.548 입니다"
    assert not scan(clean, ascii_digests=ascii_set, ko_by_len=ko_set), "오탐"


def test_line_numbers_survive_the_deescape_pass():
    """역슬래시를 뺀 사본으로도 훑는데, 지운 만큼 줄 번호가 밀리면 안 된다."""
    import hashlib
    ascii_set = {hashlib.sha256(b"zzdummy.yml").hexdigest()[:16]}
    text = "1\n2\n3\n" + r'  x = r"zzdummy\.yml"' + "\n"
    assert scan(text, ascii_digests=ascii_set, ko_by_len={}) == [4]
