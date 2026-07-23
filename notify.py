"""새 방문자가 챗봇과 대화를 시작하면(세션 첫 메시지) 즉시 이메일 알림.

표준 라이브러리 SMTP(Gmail)로 발송 — 새 의존성 없음. 실패해도 조용히 no-op이라
알림 실패가 채팅을 깨지 않는다. 크리덴셜이 없으면(로컬/설정 전) 그냥 inert.

Setup — Streamlit secrets에 추가:
  [email_alert]
  smtp_user     = "you@gmail.com"          # 발송 Gmail 주소
  smtp_password = "xxxxxxxxxxxxxxxx"        # Gmail '앱 비밀번호'(2단계 인증 필요, 공백 없이)
  to            = "you@gmail.com"           # 받을 주소(같아도 됨)
"""
import streamlit as st


def notify_new_session(session, first_question, page="chat"):
    """세션 첫 메시지에 1회 호출한다. 절대 예외를 올리지 않는다(fail-silent)."""
    try:
        if "email_alert" not in st.secrets:
            return
        conf = st.secrets["email_alert"]
        import smtplib, ssl
        from email.mime.text import MIMEText
        from email.utils import formataddr
        from datetime import datetime, timezone, timedelta

        ts = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
        sheet = st.secrets.get("log_sheet_url", "")
        body = (
            "새 방문자가 JisangFolio 챗봇과 대화를 시작했습니다.\n\n"
            f"· 시각(KST): {ts}\n"
            f"· 세션: {session}\n"
            f"· 페이지: {page}\n"
            f"· 첫 질문: {first_question}\n"
        )
        if sheet:
            body += f"\n전체 대화 로그: {sheet}\n"

        to_addr = conf.get("to", conf["smtp_user"])
        q = (first_question or "").strip().replace("\n", " ")
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = f"[JisangFolio] 새 방문자 · {q[:40]}"
        msg["From"] = formataddr(("JisangFolio", conf["smtp_user"]))
        msg["To"] = to_addr

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=10) as s:
            s.login(conf["smtp_user"], conf["smtp_password"])
            s.sendmail(conf["smtp_user"], [to_addr], msg.as_string())
    except Exception:
        pass  # fail silent — 알림 실패가 채팅을 막지 않게
