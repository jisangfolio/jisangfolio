"""일일 한도(TPD)가 풀리는 대로 평가를 이어 돌리는 무인 러너.

무료 티어는 하루 20만 토큰이고 전체 실행 1회가 그 대부분을 먹는다. 한도가 차면
기다리는 것 말고 방법이 없는데, 리필은 조금씩 계속 들어온다. 그래서 주기적으로
아주 작은 호출로 문을 두드려 보고, 열리면 `--resume`으로 남은 케이스만 이어 돌린다.
체크포인트 덕분에 매 시도가 조금씩 전진하고, 이미 끝난 케이스는 다시 태우지 않는다.

거부된 429 요청은 토큰을 소비하지 않으므로 두드리는 비용은 사실상 없다(요청 수만 쓴다).

사용:  python evals/watch_run.py [--section rag|all] [--attempts N] [--interval SEC]
로그:  evals/.watch_log.txt  (사람이 읽는 진행 요약)
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ratelimit import is_daily_limit, parse_wait_seconds  # noqa: E402

KST = timezone(timedelta(hours=9))
LOG = ROOT / "evals" / ".watch_log.txt"
CACHE = ROOT / "evals" / ".cache_results.json"
GOLDEN = {"chat": "golden_chat.jsonl", "router": "golden_router.jsonl", "rag": "golden_rag.jsonl"}


def log(msg: str):
    line = f"[{datetime.now(KST).strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def golden_count(name: str) -> int:
    p = ROOT / "evals" / GOLDEN[name]
    return sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip())


def cached_counts() -> dict:
    if not CACHE.exists():
        return {}
    try:
        return {k: len(v) for k, v in json.loads(CACHE.read_text(encoding="utf-8")).get("sections", {}).items()}
    except Exception:  # noqa: BLE001
        return {}


def probe(client, model: str, need: int = 2500):
    """문 두드리기. 실제 케이스 규모(need)만큼 **예약**을 요청해 본다.

    Groq은 프롬프트+max_tokens를 요청량으로 계산하므로, max_tokens를 크게 잡으면
    '실제 케이스가 통과할 여유가 있는가'를 잰다. 답변은 한 단어라 실제 소비는 미미하다.
    (1토큰으로 두드리면 리필 잔량이 조금만 있어도 '열림'으로 오판한다 — 실측으로 확인.)
    """
    try:
        client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "Reply with OK"}], max_tokens=need)
        return True, ""
    except Exception as e:  # noqa: BLE001
        wait = parse_wait_seconds(e)
        kind = "일일(TPD)" if is_daily_limit(e) else "분당(TPM)"
        return False, f"{kind} 한도 — 서버 안내 대기 {wait:.0f}s" if wait else f"{kind} 한도"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", default="rag", choices=["rag", "all"],
                    help="rag=열린 질문(청킹 변경 검증)부터, all=전체")
    ap.add_argument("--attempts", type=int, default=10)
    ap.add_argument("--interval", type=int, default=2700, help="시도 간격(초). 리필 속도(~14k토큰/시)를 감안해 넉넉히")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT / "evals"))
    from run_evals import CHAT_MODEL
    from groq import Groq

    secrets = tomllib.load(open(ROOT / ".streamlit" / "secrets.toml", "rb"))
    client = Groq(api_key=secrets["groq_api_key"])

    target = golden_count("rag") if args.section == "rag" else sum(golden_count(k) for k in GOLDEN)
    cmd = [sys.executable, str(ROOT / "evals" / "run_evals.py"), "--resume"]
    if args.section == "rag":
        cmd.append("--rag-only")

    log(f"=== 워처 시작 (섹션={args.section}, 최대 {args.attempts}회, 간격 {args.interval//60}분) ===")
    log(f"현재 캐시: {cached_counts()} / 목표 {target}건")

    for attempt in range(1, args.attempts + 1):
        done = cached_counts()
        have = done.get("rag", 0) if args.section == "rag" else sum(done.values())
        if have >= target:
            log(f"✅ 목표 달성 ({have}/{target}건) — 워처 종료")
            break

        ok, why = probe(client, CHAT_MODEL)
        if not ok:
            log(f"[{attempt}/{args.attempts}] 아직 막힘: {why} — {args.interval//60}분 후 재시도")
            time.sleep(args.interval)
            continue

        log(f"[{attempt}/{args.attempts}] 한도 열림 → 평가 실행")
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        tail = [ln for ln in (r.stdout or "").splitlines()
                if any(k in ln for k in ("PASS", "FAIL", "ERROR", "중단", "리포트", "페이싱", "rate limit"))]
        for ln in tail[-25:]:
            log("   " + ln.strip())
        after = cached_counts()
        log(f"   진행: {after} (이전 {done})")
        if after == done:
            log("   전진 없음 — 리필 대기")
        time.sleep(args.interval)
    else:
        log(f"⏹ 최대 시도 횟수 도달 — 캐시 {cached_counts()} 상태로 종료 (다시 돌리면 이어서 진행)")

    log("=== 워처 종료. `python evals/run_evals.py --resume`로 언제든 이어서 가능 ===")


if __name__ == "__main__":
    main()
