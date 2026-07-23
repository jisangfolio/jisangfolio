"""Durable visitor-conversation logging to a PRIVATE Google Sheet (owner-only view).

Every chat turn is appended as one row. The owner reads the log simply by opening
the private Sheet in their own Google account — visitors never see it.

Fails silent by design: if the Streamlit secrets / service-account creds are missing
or the Sheets API errors, logging no-ops so a logging failure can never break the
chat for a visitor. Locally (no creds) it is simply inert.

Setup (one time):
  1) Google Cloud → create a Service Account → download its JSON key. Enable the
     "Google Sheets API" for the project.
  2) Create a private Google Sheet. Share it (Editor) with the service account's
     client_email (…@….iam.gserviceaccount.com).
  3) In Streamlit Cloud → app → Settings → Secrets, add:
        log_sheet_url = "https://docs.google.com/spreadsheets/d/<ID>/edit"
        [gcp_service_account]
        type = "service_account"
        project_id = "…"
        private_key_id = "…"
        private_key = "-----BEGIN PRIVATE KEY-----\\n…\\n-----END PRIVATE KEY-----\\n"
        client_email = "…@….iam.gserviceaccount.com"
        client_id = "…"
        token_uri = "https://oauth2.googleapis.com/token"
     (paste every field from the JSON; keep the private_key's \\n escapes).
  4) Add `gspread` to requirements.txt (already done).
"""
import streamlit as st

_HEADER = ["timestamp (KST)", "session", "page", "question", "answer",
           "latency_ms", "guard", "model"]


@st.cache_resource(show_spinner=False)
def _worksheet():
    """Authorize once per process; return the target worksheet, or None if unconfigured."""
    try:
        if "gcp_service_account" not in st.secrets or "log_sheet_url" not in st.secrets:
            return None
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        ws = gspread.authorize(creds).open_by_url(st.secrets["log_sheet_url"]).sheet1
        if not ws.acell("A1").value:  # 빈 시트면 헤더 1회 기록
            ws.append_row(_HEADER, value_input_option="RAW")
        return ws
    except Exception:
        return None


def log_conversation(session, page, question, answer,
                     latency_ms="", guard="", model=""):
    """Append one conversation turn. Never raises — logging must not break the chat."""
    try:
        ws = _worksheet()
        if ws is None:
            return
        from datetime import datetime, timezone, timedelta
        ts = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
        ws.append_row(
            [ts, session, page, str(question)[:4000], str(answer)[:8000],
             latency_ms, guard, model],
            value_input_option="RAW",
        )
    except Exception:
        pass  # fail silent
