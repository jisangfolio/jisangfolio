"""폐기된 주장 목록 — 여러 표면이 공유하는 단일 소스.

이 파일이 생긴 이유: 폐기-주장 검사가 이미 있었는데(test_mcp_drift.test_no_retired_claims)
**jisangfolio_mcp.py 만** 보고 있었다. 정작 라이브 챗봇이 1인칭으로 말하는 원본은
secrets.toml 의 resume_text 와 profile_graph 의 노드 설명인데, 그 둘은 아무도 안 봤다.

그래서 실제로 이런 일이 있었다(2026-07-29 발견):
  · 코드그래프는 2026-07-26 에 자체 AST 파서로 바뀌었는데(gen_codegraph.py 가 "graphify 아님"
    이라고 명시) resume_text 는 07-28 재작성을 거치고도 "(Graphify)" 를 그대로 들고 있었다.
  · README 가 "10/16 → 15/16 은 깨진 하니스 수치라 running score 가 아니다"라고 적은 뒤에도
    resume_text 와 profile_graph 는 그 숫자를 성과로 말하고 있었다.

즉 코드 드리프트는 CI 가 잡는데 **주장 드리프트는 사본마다 따로 놀았다**. 이 리포가
반복해서 겪은 그 패턴("한 곳에서 고쳤는데 사본이 못 받았다")이 이번엔 감시 장치에서 났다.
"""
import re

# (패턴, 왜 폐기됐는지) — 메시지가 곧 문서다. 실패했을 때 이유를 바로 알 수 있어야 한다.
RETIRED = [
    (r"\b62\s*%|\b94\s*%",
     "재현 불가로 폐기한 평가 수치. 골든셋 실측치(evals/runs)로만 말한다."),
    (r"10\s*/\s*16|15\s*/\s*16",
     "하니스의 lang 버그(한국어 케이스를 영어 프롬프트로 채점) 이전 값이라 "
     "현재 점수로 인용 불가. README 가 'history rather than a running score' 로 규정했다."),
    (r"[Gg]raphify",
     "코드그래프는 자체 AST 파서(gen_codegraph.py)가 만든다 — graphify 아님(2026-07-26 전환)."),
    (r"Kubeflow",
     "사용 경험 없음. 기술 스택에 넣지 않는다."),
    (r"정출연",
     "KETI 는 정출연이 아니라 산업부 소관 전문생산기술연구소다."),
    (r"자율형\s*IoT\s*연구센터",
     "이력서에는 상위 조직인 'AX 연구본부'를 쓴다."),
    (r"바이브\s*코딩",
     "KETI 업무 서술에 쓰지 않기로 한 표현."),
    # 앞뒤 숫자 경계를 못 박는다 — 경계가 없으면 GCP client_id 같은 긴 숫자열
    # ("101627182111829468756") 안에서 전화번호 패턴이 잡히는 오탐이 난다.
    # ⚠️ 이 규칙은 **공개 산출물**(리포·MCP·라이브 봇) 기준이다. 회사·교수에게
    #    직접 보내는 이력서/CV에는 연락처가 당연히 들어간다 — 그쪽엔 적용하지 말 것.
    (r"(?<!\d)01[016][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)",
     "공개 산출물에 전화번호를 넣지 않는다(직접 발송하는 이력서·CV는 예외)."),
]


def find_retired(text: str):
    """text 에서 폐기된 주장을 찾아 [(매치문자열, 사유)] 로 돌려준다."""
    hits = []
    for pattern, why in RETIRED:
        for m in re.finditer(pattern, text):
            hits.append((m.group(0), why))
    return hits
