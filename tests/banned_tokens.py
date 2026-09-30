"""공개 리포에 평문으로 둘 수 없는 금칙 토큰 — **해시로만** 싣는다.

이 파일이 생긴 이유: 금칙어 목록을 평문 정규식으로 적었더니 **목록 자체가 그 단어를
공개하는 자리**가 됐다(2026-09-30 외부 검토 적발). 옆에 범주 라벨까지 붙어 있어서,
원래 본문에 흩어져 있을 때보다 무엇인지 더 분명해졌다. 가드가 지키려던 것을 가드가
내보내고 있었다.

⚠️ **해시는 암호화가 아니다.** 후보 단어를 이미 짐작한 사람은 하나씩 넣어 대조할 수
   있다. 이 장치가 막는 건 *한눈에 읽히는 것*과 *검색으로 걸리는 것*이지 결정적인
   추적이 아니다. 개인 포트폴리오 수준에서는 이걸로 충분하다고 판단했고, 더 숨겨야
   하면 목록을 CI secret 으로 옮기면 된다(그 대가는 포크·외부 기여 환경에서 검사가
   꺼진다는 것).

토큰 경계에서 새던 것들 — 전부 같은 원인(토큰을 글자 그대로만 봤다):
  · 문장 끝 마침표      "…기관명."       → 끝 문장부호를 떼고 다시 본다
  · 확장자 붙은 파일명  "파일명.yml."     → 떼고 + 점 앞 본체(stem)도 본다
  · 경로 안의 이미지    "assets/파일.png" → stem 검사가 잡는다
  · 정규식 이스케이프   "값\\.값"           → 역슬래시를 뺀 사본으로 한 번 더 훑는다
                                          (길이를 보존해야 줄 번호가 안 어긋난다)

토큰을 추가하려면:  python tests/banned_tokens.py <단어> ...
"""
import hashlib
import re
import sys

_PREFIX = 16

# 한글: {글자수: [다이제스트]} — 조사가 붙어 경계가 흐려지므로 그 길이의 부분열만 훑는다.
KO_BY_LEN = {
    2: ['22e677a755b09519'],
    3: ['7a848701e6741e29'],
    6: ['121d665985c8b2c7'],
}

# ASCII/숫자: 토큰 단위. 아래 _variants 가 경계 변형을 흡수한다.
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
_TRIM = "._-"


def _h(text: str) -> str:
    return hashlib.sha256(text.lower().encode()).hexdigest()[:_PREFIX]


def _variants(token: str):
    """토큰 하나에서 비교해 볼 표기들 — 끝 문장부호를 떼고, 확장자도 벗긴다."""
    seen, queue = set(), [token]
    while queue:
        t = queue.pop()
        if not t or t in seen:
            continue
        seen.add(t)
        stripped = t.strip(_TRIM)
        if stripped != t:
            queue.append(stripped)
        if "." in t:
            queue.append(t.rsplit(".", 1)[0])
    return seen


def _line_index(text: str):
    starts = [0] + [m.end() for m in re.finditer(r"\n", text)]

    def lineno(pos):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    return lineno


def scan(text: str, *, ascii_digests=None, ko_by_len=None):
    """금칙 토큰이 있는 **줄 번호** 목록. 일치한 문자열은 돌려주지 않는다.

    digest 집합을 주입할 수 있게 열어 둔 건 경계 테스트 때문이다 — 테스트가 진짜
    금칙어를 쓰면 그 테스트가 다시 유출 지점이 된다. 더미 단어로 돌려야 한다.
    """
    ascii_digests = ASCII_DIGESTS if ascii_digests is None else ascii_digests
    ko_by_len = KO_BY_LEN if ko_by_len is None else ko_by_len

    hits = set()
    lineno = _line_index(text)
    # 2회 훑는다: 원문, 그리고 역슬래시를 **뺀** 사본(정규식 이스케이프 형태 대응).
    # 공백으로 치환하면 숫자가 쪼개져 못 잡으므로 삭제하되, 지운 만큼 원문 위치를
    # 되짚을 수 있게 offset 지도를 함께 만든다 — 줄 번호가 어긋나면 안 된다.
    clean, offsets = [], []
    for i, ch in enumerate(text):
        if ch != "\\":
            clean.append(ch)
            offsets.append(i)
    passes = [(text, None), ("".join(clean), offsets)]

    for body, omap in passes:
        def orig(pos, _omap=omap):
            return pos if _omap is None else _omap[pos]

        for m in _ASCII_TOKEN.finditer(body):
            if any(_h(v) in ascii_digests for v in _variants(m.group(0))):
                hits.add(lineno(orig(m.start())))
        for m in _KO_RUN.finditer(body):
            run = m.group(0)
            for length, digests in ko_by_len.items():
                for i in range(len(run) - length + 1):
                    if _h(run[i:i + length]) in digests:
                        hits.add(lineno(orig(m.start() + i)))
    return sorted(hits)


if __name__ == "__main__":
    for word in sys.argv[1:]:
        kind = "KO_BY_LEN[%d]" % len(word) if _KO_RUN.fullmatch(word) else "ASCII_DIGESTS"
        print(f'{kind}: "{_h(word)}",')
