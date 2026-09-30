"""공개 리포에 평문으로 둘 수 없는 금칙 토큰 — **해시로만** 싣는다.

이 파일이 생긴 이유: 금칙어 목록을 평문 정규식으로 적었더니 **목록 자체가 그 단어를
공개하는 자리**가 됐다(2026-09-30 외부 검토 적발). 게다가 "협력 기관 실명" 같은 라벨이
옆에 붙어 있어서, 원래 본문에 흩어져 있을 때보다 무엇인지 더 분명해졌다. 가드가 지키려던
것을 가드가 내보내고 있었다.

그래서 여기엔 **정규화 토큰의 SHA-256 앞 16자**만 둔다. 검사는 대상 텍스트를 토큰으로
쪼개 해시를 맞춰 보므로 평문 없이 돈다. 위반 메시지도 일치한 문자열을 찍지 않는다 —
공개 리포의 Actions 로그는 누구나 읽는다. `파일:줄`까지만 알려주고, 그 줄은 고치는
사람이 자기 diff 에서 바로 본다.

한글은 조사가 붙어 토큰 경계가 흐려지므로(예: "…시티의") 등록된 **길이만큼의 부분열**을
훑는다. 길이를 아는 건 해시를 만들 때 함께 적어두기 때문이고, 길이 자체는 단어를
복원해 주지 않는다.

토큰을 추가하려면:  python tests/banned_tokens.py <단어> ...
"""
import hashlib
import re
import sys

_PREFIX = 16

# 한글: {글자수: [다이제스트]} — 부분열 검사를 그 길이에만 돌린다.
KO_BY_LEN = {
    2: ['22e677a755b09519'],
    3: ['7a848701e6741e29'],
    6: ['121d665985c8b2c7'],
}

# ASCII/숫자: 토큰 단위로 정확히 일치시킨다(조사 문제가 없다).
ASCII_DIGESTS = {
    "a2557303cb269022",
    "38737a483d7d35bc",
    "1817709bfdda832e",
    "d5586b59d690caf1",
    "7e6fcb4bddf1f84e",
    "a3a4a0d916f95ff3",
    "155db705f08a2d57",
    "809dc7cd50ea883a",
    "caf0f7e5875bf0b0",
    "4b1118b965d5f4f5",
    "6a61ad78775ea066",
    "85d006ca16842a78",
    "9d522838ebf4aa7c",
    "5d56221ebfae648a",
    "ddd331c4892fae03",
    "73af6e98d9a2e1c4",
}

_ASCII_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]*")
_KO_RUN = re.compile(r"[가-힣]+")


def _h(text: str) -> str:
    return hashlib.sha256(text.lower().encode()).hexdigest()[:_PREFIX]


def scan(text: str):
    """금칙 토큰이 있는 **줄 번호** 목록을 돌려준다. 일치한 문자열은 돌려주지 않는다."""
    hits = set()
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())

    def lineno(pos):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    for m in _ASCII_TOKEN.finditer(text):
        if _h(m.group(0)) in ASCII_DIGESTS:
            hits.add(lineno(m.start()))
    for m in _KO_RUN.finditer(text):
        run = m.group(0)
        for L, digests in KO_BY_LEN.items():
            for i in range(len(run) - L + 1):
                if _h(run[i:i + L]) in digests:
                    hits.add(lineno(m.start() + i))
    return sorted(hits)


if __name__ == "__main__":
    for word in sys.argv[1:]:
        kind = "KO_BY_LEN[%d]" % len(word) if _KO_RUN.fullmatch(word) else "ASCII_DIGESTS"
        print(f'{kind}: "{_h(word)}",')
