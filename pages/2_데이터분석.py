import time
import streamlit as st
import pandas as pd
from langchain_core.messages import ChatMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

st.set_page_config(page_title="JisangFolio · 데이터 분석", page_icon="📂")

try:
    groq_api_key = st.secrets["groq_api_key"]
except KeyError:
    st.error("⚠️ Secrets에 groq_api_key가 설정되지 않았습니다.")
    st.stop()

GROQ_MODEL = "qwen/qwen3-32b"

# --- 사이드바 ---
with st.sidebar:
    if st.button("← 소개 페이지"):
        st.switch_page("jisangfolio.py")
    if st.button("💬 대화하기"):
        st.switch_page("pages/1_대화하기.py")
    st.divider()
    st.header("파일 업로드")
    uploaded_file = st.file_uploader("CSV 또는 Excel 파일 업로드", type=["csv", "xlsx"])
    st.divider()
    st.caption("AI는 실수를 할 수 있습니다. 중요한 정보는 직접 확인해 주세요.")

# --- 파일 처리 ---
# 캐시 키를 파일 내용(bytes)으로 설정 → 같은 이름 다른 파일도 올바르게 구분
@st.cache_resource(show_spinner="업로드된 파일을 분석 중...")
def build_vectorstore(file_bytes: bytes, file_name: str):
    # 1. 파일 읽기
    import io
    try:
        if file_name.endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="cp949")
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        st.error(f"❌ 파일을 읽는 도중 오류가 발생했습니다: {e}")
        return None, None

    if df.empty:
        st.error("❌ 파일에 데이터가 없습니다.")
        return None, None

    # 2. 텍스트로 변환
    documents = []
    for idx, row in df.iterrows():
        content_parts = [
            f"{col}: {row[col]}"
            for col in df.columns
            if pd.notna(row[col]) and str(row[col]).strip() != ""
        ]
        documents.append(Document(
            page_content="\n".join(content_parts),
            metadata={"row": idx, "source": file_name, "summary_title": str(row[df.columns[0]])[:50]},
        ))

    # 3. 청크 분할
    splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(documents)
    if not splits:
        st.error("❌ 데이터를 처리할 수 없습니다.")
        return None, None

    # 4. 임베딩 (rate limit 대응: 에러 시에만 backoff)
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    progress_bar = st.progress(0, text="임베딩 생성 중...")
    vectorstore = None
    batch_size = 10

    for i in range(0, len(splits), batch_size):
        batch = splits[i : i + batch_size]
        for attempt in range(4):
            try:
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(batch, embedding=embedding)
                else:
                    vectorstore.add_documents(batch)
                break
            except Exception as e:
                if attempt == 3:
                    st.error(f"임베딩 오류: {e}")
                    return None, None
                time.sleep(2 ** attempt)  # 1, 2, 4초 backoff

        percent = min((i + batch_size) / len(splits), 1.0)
        progress_bar.progress(percent, text=f"임베딩 생성 중... ({int(percent * 100)}%)")

    progress_bar.empty()
    st.sidebar.success(f"✅ 저장된 데이터 수: {vectorstore.index.ntotal}개")

    # k는 전체 데이터의 20% 또는 최대 10개
    k = max(1, min(10, vectorstore.index.ntotal // 5))
    return df, vectorstore.as_retriever(search_kwargs={"k": k})


# --- 메인 ---
st.title("📂 내 파일과 대화하기")
st.caption("CSV 또는 Excel 파일을 업로드하면 AI가 데이터를 분석하고 질문에 답변해 드립니다.")

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        ChatMessage(role="assistant", content="CSV나 Excel 파일을 업로드해주시면 내용을 분석해 드릴게요.")
    ]
if "current_file" not in st.session_state:
    st.session_state["current_file"] = None

if uploaded_file:
    file_bytes = uploaded_file.getvalue()
    df, retriever = build_vectorstore(file_bytes, uploaded_file.name)

    # 파일이 바뀌면 대화 초기화
    if st.session_state["current_file"] != uploaded_file.name:
        st.session_state["messages"] = [
            ChatMessage(role="assistant", content=f"'{uploaded_file.name}' 파일을 분석했습니다. 궁금한 점을 물어보세요!")
        ]
        st.session_state["current_file"] = uploaded_file.name

    if retriever:
        st.success(f"✅ '{uploaded_file.name}' 분석 완료! ({len(df)}개의 데이터)")
else:
    st.info("👈 왼쪽 사이드바에서 CSV 또는 Excel 파일을 업로드해주세요.")
    df, retriever = None, None

for msg in st.session_state["messages"]:
    st.chat_message(msg.role).write(msg.content)

llm = ChatGroq(model=GROQ_MODEL, groq_api_key=groq_api_key, temperature=0)
user_input = st.chat_input("이 데이터에 대해 궁금한 점을 물어보세요")

if user_input and retriever:
    st.chat_message("user").write(user_input)
    st.session_state["messages"].append(ChatMessage(role="user", content=user_input))

    retrieved_docs = retriever.invoke(user_input)
    context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])

    # 이전 대화 히스토리 (최근 3턴, 환영 메시지 제외)
    history_msgs = [m for m in st.session_state["messages"][:-1] if "파일을 업로드" not in m.content and "분석했습니다" not in m.content]
    history_text = "\n".join(
        f"{'사용자' if m.role == 'user' else 'AI'}: {m.content}"
        for m in history_msgs[-6:]
    )

    prompt = ChatPromptTemplate.from_template(
        """/no_think
당신은 업로드된 데이터를 기반으로 답변하는 AI 데이터 분석가입니다.
반드시 한국어(한글)로만 답변하세요. 중국어, 일본어 한자를 절대 사용하지 마세요.

[이전 대화 (있을 경우 참고)]:
{history}

[데이터 문맥]:
{context}

규칙:
1. 문맥에 없는 내용은 지어내지 말고 "데이터에서 찾을 수 없습니다"라고 답하세요.
2. 답변은 친절하고 전문적으로 작성하세요.
3. 수치나 통계를 언급할 때는 구체적인 데이터를 근거로 하세요.

질문: {question}

답변:"""
    )

    with st.chat_message("assistant"):
        response_container = st.empty()
        full_response = ""
        buffer = ""
        in_think = True
        with st.spinner("분석 중..."):
            for chunk in (prompt | llm).stream({
                "question": user_input,
                "context": context_text,
                "history": history_text,
            }):
                delta = chunk.content
                if in_think:
                    buffer += delta
                    if "</think>" in buffer:
                        after = buffer.split("</think>", 1)[1].lstrip("\n")
                        full_response = after
                        in_think = False
                        response_container.markdown(full_response)
                else:
                    full_response += delta
                    response_container.markdown(full_response)
        st.session_state["messages"].append(ChatMessage(role="assistant", content=full_response))

elif user_input and not retriever:
    st.warning("먼저 파일을 업로드해주세요.")
