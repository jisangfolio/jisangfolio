import os
import time
import streamlit as st
import pandas as pd
from langchain_core.messages import ChatMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

st.set_page_config(page_title="JisangFolio · 데이터 분석", page_icon="📂")

try:
    os.environ["GOOGLE_API_KEY"] = st.secrets["google_api_key"]
except KeyError:
    st.error("⚠️ Secrets에 google_api_key가 설정되지 않았습니다.")
    st.stop()

GEMINI_MODEL = "gemini-2.0-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"

# --- 사이드바 ---
with st.sidebar:
    if st.button("← 소개 페이지"):
        st.switch_page("jisangfolio.py")
    if st.button("💬 대화하기"):
        st.switch_page("pages/1_대화하기.py")
    st.divider()
    st.header("파일 업로드")
    uploaded_file = st.file_uploader("CSV 또는 Excel 파일 업로드", type=["csv", "xlsx"])

# --- 파일 처리 ---
@st.cache_resource(show_spinner="업로드된 파일을 분석 중...")
def process_uploaded_file(file):
    if file is None:
        return None, None
    try:
        if file.name.endswith(".csv"):
            try:
                df = pd.read_csv(file, encoding="utf-8")
            except UnicodeDecodeError:
                file.seek(0)
                df = pd.read_csv(file, encoding="cp949")
        else:
            df = pd.read_excel(file)
    except Exception as e:
        st.error(f"❌ 파일을 읽는 도중 오류가 발생했습니다: {e}")
        return None, None

    documents = []
    for idx, row in df.iterrows():
        content_parts = []
        for col in df.columns:
            val = row[col]
            if pd.notna(val) and str(val).strip() != "":
                content_parts.append(f"{col}: {val}")
        doc = Document(
            page_content="\n".join(content_parts),
            metadata={"row": idx, "source": file.name, "summary_title": str(row[df.columns[0]])[:50]},
        )
        documents.append(doc)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = splitter.split_documents(documents)

    embedding = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    progress_bar = st.progress(0, text="데이터 저장 시작...")
    vectorstore = None
    batch_size = 10

    for i in range(0, len(splits), batch_size):
        batch = splits[i : i + batch_size]
        if vectorstore is None:
            vectorstore = FAISS.from_documents(batch, embedding=embedding)
        else:
            vectorstore.add_documents(batch)
        percent = min((i + batch_size) / len(splits), 1.0)
        progress_bar.progress(percent, text=f"데이터 저장 중... ({int(percent*100)}%)")
        time.sleep(2)

    progress_bar.empty()
    if vectorstore:
        st.sidebar.success(f"✅ 저장된 데이터 수: {vectorstore.index.ntotal}개")

    return df, vectorstore.as_retriever(search_kwargs={"k": 50}) if vectorstore else (df, None)

# --- 메인 ---
st.title("📂 내 파일과 대화하기")
st.caption("CSV 또는 Excel 파일을 업로드하면 AI가 데이터를 분석하고 질문에 답변해 드립니다.")

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        ChatMessage(role="assistant", content="CSV나 Excel 파일을 업로드해주시면 내용을 분석해 드릴게요.")
    ]

if uploaded_file:
    df, retriever = process_uploaded_file(uploaded_file)
    if retriever:
        st.success(f"✅ '{uploaded_file.name}' 분석 완료! ({len(df)}개의 데이터)")
else:
    st.info("👈 왼쪽 사이드바에서 CSV 또는 Excel 파일을 업로드해주세요.")
    df, retriever = None, None

for msg in st.session_state["messages"]:
    st.chat_message(msg.role).write(msg.content)

llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0)
user_input = st.chat_input("이 데이터에 대해 궁금한 점을 물어보세요")

if user_input and retriever:
    st.chat_message("user").write(user_input)
    st.session_state["messages"].append(ChatMessage(role="user", content=user_input))

    retrieved_docs = retriever.invoke(user_input)
    context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])

    prompt = ChatPromptTemplate.from_template(
        """당신은 업로드된 데이터를 기반으로 답변하는 AI 데이터 분석가입니다.
아래의 [데이터 문맥]을 바탕으로 사용자의 질문에 답변하세요.

규칙:
1. 문맥에 없는 내용은 지어내지 말고 "데이터에서 찾을 수 없습니다"라고 답하세요.
2. 답변은 친절하고 전문적으로 작성하세요.
3. 출처(데이터의 내용)를 근거로 답변하세요.

[데이터 문맥]:
{context}

질문: {question}

답변:"""
    )

    with st.chat_message("assistant"):
        with st.spinner("데이터 분석 중..."):
            response_container = st.empty()
            full_response = ""
            for chunk in (prompt | llm).stream({"question": user_input, "context": context_text}):
                full_response += chunk.content
                response_container.markdown(full_response)
            st.session_state["messages"].append(ChatMessage(role="assistant", content=full_response))

elif user_input and not retriever:
    st.warning("먼저 파일을 업로드해주세요.")
