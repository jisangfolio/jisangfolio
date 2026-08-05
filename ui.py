"""공유 스타일 주입 (Pretendard 폰트 + 카드/버튼 라운딩) + 페이지 공통 응답 처리.

config.toml 이 색/테마를 담당하고, 이 모듈은 폰트와 미세 라운딩만 얹는다.
멀티페이지라 각 페이지 set_page_config 직후 apply_style() 을 호출한다.

스트림 마감(finalize_stream)과 LLM 오류 문구(friendly_llm_error)도 여기 둔다.
둘 다 원래 페이지마다 인라인으로 복사돼 있었고, 그래서 1_Chat.py 에서 고친
버그가 2_Data_Analysis.py 에는 안 넘어간 채로 남아 있었다.
"""
from prompts import clean_response

_STYLE = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

/* 디자인 시스템 토큰 — 어두운 표면(이 앱)용.
   밝은 표면(이력서·포트폴리오 PDF)은 같은 계열의 다른 명도를 쓴다. */
:root {
  --jf-accent:     #4BBFAE;   /* 어두운 표면용 액센트 (밝은 표면은 #0E6E62) */
  --jf-surface:    #1E2128;   /* 결과 블록 배경 */
  --jf-rule:       #2B2F36;   /* 괘선 — 장식 전용 */
  --jf-ink:        #ECEEF0;   /* 블록 내부 본문 */
  --jf-ink-sub:    #B7BCC4;   /* 블록 내부 보조 */
  --jf-ink-cap:    #9AA0A8;   /* 블록 내부 캡션 */
}

html, body, [class*="css"], .stMarkdown, button, input, textarea, .stTextInput, .stChatInput {
  font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif !important;
}

/* 본문 행간 — 디자인 시스템 1.55 */
.stMarkdown p, .stMarkdown li { line-height: 1.55; }

/* 버튼 미세 hover. 라운딩은 config.toml 의 buttonRadius 가 담당한다
   (테마 키로 넘기면 버전마다 바뀌는 내부 셀렉터에 의존하지 않는다). */
.stButton > button { transition: transform .06s ease, border-color .15s ease; }
.stButton > button:hover { transform: translateY(-1px); }

/* 링크: 밑줄은 hover에서만 (색은 config.toml linkColor) */
a, a:visited { text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── 디자인 시스템 컴포넌트 ──────────────────────────────────
   전부 자체 클래스(.jf-*)라 Streamlit 내부 DOM 에 의존하지 않는다.
   색은 배경과 전경을 **함께** 지정한다 — 방문자가 Settings 에서 테마를
   바꿔도 블록 내부 대비가 유지되게 하기 위해서다. */

.jf-section {
  font-size: 1.05rem; font-weight: 800; letter-spacing: -0.2px;
  border-bottom: 1px solid var(--jf-rule);
  padding-bottom: .35rem; margin: 1.6rem 0 .7rem;
  display: flex; align-items: baseline; gap: .7rem;
}
.jf-section .jf-num { color: var(--jf-accent); font-size: .8rem; letter-spacing: 1px; flex: none; }
.jf-section .jf-t { flex: 1; }
.jf-section .jf-meta { font-size: .78rem; font-weight: 400; color: var(--jf-ink-cap); flex: none; }

.jf-label {
  font-size: .72rem; font-weight: 700; color: var(--jf-accent);
  letter-spacing: .6px; margin-bottom: .25rem;
}

.jf-metrics { display: flex; gap: .6rem; flex-wrap: wrap; margin: .2rem 0 .6rem; }
.jf-metric {
  flex: 1 1 150px; border: 1px solid var(--jf-rule);
  border-top: 2.5px solid var(--jf-accent);
  padding: .6rem .8rem; background: var(--jf-surface);
}
.jf-metric .jf-val {
  font-size: 1.35rem; font-weight: 800; color: var(--jf-accent);
  letter-spacing: -.5px; line-height: 1.15;
}
.jf-metric .jf-cap { font-size: .74rem; color: var(--jf-ink-cap); margin-top: .2rem; line-height: 1.35; }

.jf-result {
  background: var(--jf-surface); border-left: 2.4px solid var(--jf-accent);
  padding: .6rem .85rem; margin: .3rem 0 .5rem;
}
.jf-result p { margin: 0; color: var(--jf-ink); line-height: 1.55; }

.jf-caveat { font-size: .78rem; color: var(--jf-ink-cap); line-height: 1.5; }

.jf-stack {
  font-size: .76rem; color: var(--jf-ink-cap);
  padding-top: .35rem; border-top: 1px solid var(--jf-rule); margin-top: .5rem;
}
.jf-stack b { color: var(--jf-ink-sub); font-weight: 700; letter-spacing: .5px; margin-right: .5rem; }

.jf-arrow { font-size: 2rem; text-align: center; padding-top: .6rem; color: var(--jf-ink-cap); }
</style>
"""


def apply_style():
    """폰트·라운딩 CSS를 주입한다. set_page_config 이후에 호출.

    streamlit 은 여기서만 필요하므로 모듈 최상단이 아니라 함수 안에서 임포트한다.
    최상단에 두면 finalize_stream 회귀 테스트가 streamlit 없는 CI 에서 수집조차
    안 돼(ModuleNotFoundError) 전체 런이 중단된다. CI 는 키 없이 빠르게 도는 게
    설계 의도라 streamlit 을 설치하지 않는다 — 임포트를 여기로 내려서 그 의도를
    지키면서 회귀 테스트가 CI 에서 실제로 돌게 한다.
    """
    import streamlit as st

    st.markdown(_STYLE, unsafe_allow_html=True)


# ── 디자인 시스템 마크업 헬퍼 ────────────────────────────────────
# 각 헬퍼는 **한 번의 st.markdown 호출로 완결된 HTML** 을 뱉는다. 열린 태그를
# 따로 내보내고 나중에 닫는 방식(st.markdown("<div>") … st.markdown("</div>"))은
# 구조적으로 불가능하다 — Streamlit 이 요소마다 별도 컨테이너로 렌더하고
# sanitizer 가 열린 태그를 그 자리에서 닫아버린다. 네이티브 위젯을 블록 안에
# 넣어야 하면 st.container(key=...) 의 .st-key-<key> 훅을 쓸 것.
#
# _esc 로 이스케이프하는 이유: 인자에 사용자/데이터 유래 문자열이 섞일 수 있는데
# unsafe_allow_html=True 경로라 그대로 두면 마크업이 깨지거나 주입된다.

def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def section_header(title, num=None, meta=None):
    """번호·제목·메타로 된 섹션 헤더 HTML 을 반환한다(하단 1px 실선)."""
    parts = []
    if num:
        parts.append(f'<span class="jf-num">{_esc(num)}</span>')
    parts.append(f'<span class="jf-t">{_esc(title)}</span>')
    if meta:
        parts.append(f'<span class="jf-meta">{_esc(meta)}</span>')
    return f'<div class="jf-section">{"".join(parts)}</div>'


def metric_tiles(items):
    """지표 타일 묶음. items = [(값, 캡션), ...]

    캡션에는 반드시 측정조건을 담는다 — 조건 없는 수치는 이 컴포넌트에 넣지 않는다.
    한 줄에 4개를 넘기면 각각의 무게가 사라지므로 호출부에서 3개 안팎으로 유지할 것.
    """
    tiles = "".join(
        f'<div class="jf-metric"><div class="jf-val">{_esc(v)}</div>'
        f'<div class="jf-cap">{_esc(c)}</div></div>'
        for v, c in items
    )
    return f'<div class="jf-metrics">{tiles}</div>'


def result_block(text, label="결과"):
    """좌측 액센트 바 + 배경을 가진 결과 블록. 한 섹션에 하나만 쓴다."""
    return (f'<div class="jf-result"><div class="jf-label">{_esc(label)}</div>'
            f'<p>{_esc(text)}</p></div>')


def stack_list(items, label="STACK"):
    """프로젝트 하단에 붙는 기술 스택 한 줄."""
    return f'<div class="jf-stack"><b>{_esc(label)}</b>{_esc(" · ".join(items))}</div>'


# 모델에 다시 보내도 되는 role. 가드가 막은 턴은 화면·내보내기에는 남기되
# (가드가 작동하는 장면 자체가 이 사이트의 데모다) 재전송 대상에서는 뺀다.
REPLAYABLE_ROLES = ("user", "assistant")

# 재전송할 최근 메시지 수(user+assistant 합산). 상한이 없으면 대화가 길어질수록
# 턴당 토큰이 단조 증가해, 세션 상한의 비용 근거가 뒤로 갈수록 어긋난다.
REPLAY_MAX_MESSAGES = 12


def replayable_history(history, max_messages=REPLAY_MAX_MESSAGES):
    """대화 히스토리에서 **모델에 다시 보낼** 항목만, 최근 것부터 상한만큼 남긴다.

    history: (role, content) 시퀀스.

    이게 없던 시절엔 가드 판정과 무관하게 입력을 히스토리에 넣고 다음 턴에 통째로
    재전송해서, 차단된 문자열이 role:"user" 로 모델에 그대로 도달했다 — guardrails 가
    반환하는 "blocked before reaching the model" 이 한 턴 뒤엔 거짓이 됐다.
    진짜 위험은 탈옥 자체보다 다단 스머글링이다: 1턴에 페이로드를 심고(차단되지만 보존됨)
    2턴에 "위에서 시킨 대로 해"라고만 하면 단일 메시지 정규식으로는 잡을 수가 없다.
    """
    kept = [(role, content) for role, content in history if role in REPLAYABLE_ROLES]
    return kept[-max_messages:] if max_messages else kept


def _delta_text(chunk):
    """스트림 청크에서 텍스트를 꺼낸다.

    Groq SDK 는 chunk.choices[0].delta.content, LangChain 은 chunk.content 로 준다.
    이 차이가 스트림 루프를 세 벌로 복사해 둔 이유 중 하나였다.
    """
    choices = getattr(chunk, "choices", None)
    if choices:
        return getattr(choices[0].delta, "content", None) or ""
    return getattr(chunk, "content", None) or ""


def stream_answer(chunks, render=None, lang="English"):
    """<think> 블록을 걷어내며 부분 응답을 render 로 흘리고, 최종 확정 텍스트를 반환한다.

    이 상태기계는 원래 세 곳(1_Chat 1개 · 2_Data_Analysis 2개)에 거의 동일하게 복사돼
    있었고, 그래서 1_Chat 에서 고친 '짧은 응답이 빈 말풍선이 되는' 버그가 2_Data_Analysis
    에는 그대로 남아 있었다. 회귀 테스트조차 이 루프를 **재구현한 사본**을 검사하고
    있었어서, 실물이 바뀌어도 테스트는 초록일 수 있었다.

    render: 부분 응답을 그릴 콜백(커서 장식 등 페이지별 차이는 여기서 흡수).
    예외는 삼키지 않는다 — 호출부의 try/except 가 friendly_llm_error 로 처리해야 하고,
    여기서 잡으면 그 오류 문구를 finalize 결과가 덮어쓴다.
    """
    full_response, buffer, in_think = "", "", None
    for chunk in chunks:
        delta = _delta_text(chunk)
        if in_think is None:
            buffer += delta
            if "<think>" in buffer:
                in_think = True
            elif len(buffer) >= 50:
                in_think = False
                full_response = buffer
                if render:
                    render(full_response)
        elif in_think:
            buffer += delta
            if "</think>" in buffer:
                full_response = buffer.split("</think>", 1)[1].lstrip("\n")
                in_think = False
                if render:
                    render(full_response)
        else:
            full_response += delta
            if render:
                render(full_response)
    return finalize_stream(full_response, buffer, in_think, lang)


def finalize_stream(full_response, buffer, in_think, lang="English"):
    """스트리밍 종료 후 최종 응답을 확정한다.

    스트림 루프는 <think> 블록 판정을 위해 앞 50자를 buffer 에 모아두고, 50자를
    넘어야 buffer 를 full_response 로 승격한다. 그래서 **50자 미만 응답은 buffer 에만
    남은 채 끝난다** — 프롬프트가 지시하는 거절 문구 "I can't find that in the data."
    (30자)가 정확히 여기 걸려서 빈 말풍선으로 렌더링되고 히스토리에 content=""
    으로 영구 저장됐다. 짧은 답변일수록 중요한 답변인 경우가 많다.
    """
    if in_think is None:          # 50자에 도달하지 못하고 스트림이 끝난 경우
        full_response = buffer
    out = clean_response(full_response)
    if not out.strip():           # 후처리가 전부 깎아낸 경우 원본으로 되돌린다
        out = clean_response(buffer)
    if not out.strip():
        out = ("(응답이 비어 있어요. 다시 한 번 물어봐 주세요.)" if lang == "한국어"
               else "(Empty response — please try again.)")
    return out


def friendly_llm_error(err, lang="English"):
    """모델 호출 실패를 사용자용 문구로 바꾼다. 원문 예외는 절대 렌더링하지 않는다.

    Groq 의 429 본문에는 조직 ID 와 쿼터가 실려 나온다. 그대로 화면에 뿌리면
    방문자에게 계정 정보를 보여주는 셈이라 예외 '종류'만 노출한다.
    """
    name = type(err).__name__
    ko = (lang == "한국어")
    if isinstance(err, TimeoutError):
        # 턴 예산 초과(agent_rag.APP_TURN_BUDGET_S). 사용자 입장에선 rate limit 과 원인이
        # 같으므로 같은 톤으로 안내하되, '멈춰 있는' 대신 '포기하고 돌아왔다'를 알린다.
        return ("⚠️ 모델 사용 한도 때문에 대기가 길어져 이번 질문은 여기서 멈췄습니다. "
                "이 데모는 무료 티어라 그럴 수 있어요. 잠시 후 다시 시도해 주세요."
                if ko else
                "⚠️ The model was rate-limited long enough that I stopped waiting for this "
                "question — this demo runs on a free tier. Please try again in a moment.")
    if "RateLimit" in name or "429" in str(err):
        return ("⚠️ 지금은 모델 사용 한도에 걸려 답할 수 없습니다. 이 데모는 무료 티어를 "
                "쓰기 때문에 한도에 닿을 수 있어요. 잠시 후 다시 시도해 주세요." if ko else
                "⚠️ The model is rate-limited right now — this demo runs on a free tier. "
                "Please try again in a moment.")
    return (f"⚠️ 답변 생성 중 오류가 발생했습니다 ({name}). 잠시 후 다시 시도해 주세요." if ko
            else f"⚠️ Something went wrong while generating the answer ({name}). Please try again.")
