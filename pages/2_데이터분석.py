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
@st.cache_resource(show_spinner="업로드된 파일을 분석 중...")
def build_vectorstore(file_bytes: bytes, file_name: str):
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

    splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(documents)
    if not splits:
        st.error("❌ 데이터를 처리할 수 없습니다.")
        return None, None

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
                time.sleep(2 ** attempt)

        percent = min((i + batch_size) / len(splits), 1.0)
        progress_bar.progress(percent, text=f"임베딩 생성 중... ({int(percent * 100)}%)")

    progress_bar.empty()
    st.sidebar.success(f"✅ 저장된 데이터 수: {vectorstore.index.ntotal}개")

    k = max(1, min(10, vectorstore.index.ntotal // 5))
    return df, vectorstore.as_retriever(search_kwargs={"k": k})


def get_df_info(df: pd.DataFrame) -> str:
    """LLM에게 전달할 DataFrame 요약 정보를 생성합니다."""
    info_parts = [f"컬럼: {list(df.columns)}"]
    info_parts.append(f"행 수: {len(df)}")
    info_parts.append(f"데이터 타입:\n{df.dtypes.to_string()}")
    info_parts.append(f"처음 3행:\n{df.head(3).to_string()}")
    return "\n".join(info_parts)


def classify_question(llm, question: str, df_info: str) -> str:
    """질문이 pandas 집계(코드 생성)로 처리해야 하는지, RAG 검색으로 처리해야 하는지 LLM이 판단합니다."""
    prompt = ChatPromptTemplate.from_template(
        """/no_think
아래 DataFrame 정보와 사용자 질문을 보고, 답변 방식을 하나만 골라 출력하세요.

[DataFrame 정보]
{df_info}

[질문]
{question}

[판단 기준]
- PANDAS: 평균, 합계, 최대, 최소, 정렬, 필터링, 그룹별 집계, 통계, 그래프, 카운트, 비율, 상관관계 등 전체 데이터를 대상으로 계산이 필요한 질문
- RAG: 특정 항목 검색, 내용 요약, 의미 기반 질문 등 텍스트 검색으로 답할 수 있는 질문

PANDAS 또는 RAG 중 하나만 출력하세요. 다른 말은 하지 마세요."""
    )
    result = (prompt | llm).invoke({"question": question, "df_info": df_info})
    answer = result.content.strip().upper()
    if "PANDAS" in answer:
        return "PANDAS"
    return "RAG"


def generate_and_run_code(llm, question: str, df_info: str, df: pd.DataFrame):
    """LLM이 pandas 코드를 생성하고 실행합니다. 코드와 결과를 함께 반환합니다."""
    prompt = ChatPromptTemplate.from_template(
        """/no_think
아래 DataFrame 정보를 참고하여 사용자 질문에 답하는 Python pandas 코드를 작성하세요.

[DataFrame 정보]
{df_info}

[질문]
{question}

[규칙]
1. 변수 `df`는 이미 로드되어 있습니다. import나 파일 읽기 코드를 쓰지 마세요.
2. 최종 결과를 `result` 변수에 저장하세요.
3. 시각화가 필요하면 `chart_df` 변수에 차트용 DataFrame을 저장하세요 (index=카테고리, values=수치). 시각화가 불필요하면 `chart_df`를 만들지 마세요.
4. 숫자 컬럼에 문자가 섞여 있을 수 있으니 pd.to_numeric(errors='coerce')를 사용하세요.
5. 코드만 출력하세요. 설명, 마크다운, 코드 블록(```) 없이 순수 Python 코드만 작성하세요.
6. print()를 사용하지 마세요."""
    )

    response = (prompt | llm).invoke({"question": question, "df_info": df_info})
    code = response.content.strip()

    # 코드 블록 마커 제거
    if code.startswith("```"):
        lines = code.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        code = "\n".join(lines)

    # <think> 블록 제거
    if "<think>" in code:
        code = code.split("</think>")[-1].strip()

    # 실행
    local_vars = {"df": df.copy(), "pd": pd}
    try:
        exec(code, {"__builtins__": {"len": len, "sum": sum, "min": min, "max": max, "round": round, "sorted": sorted, "list": list, "dict": dict, "str": str, "int": int, "float": float, "abs": abs, "enumerate": enumerate, "zip": zip, "range": range, "type": type, "isinstance": isinstance, "True": True, "False": False, "None": None, "print": lambda *a, **kw: None}}, local_vars)
        result = local_vars.get("result", "결과를 생성하지 못했습니다.")
        chart_df = local_vars.get("chart_df", None)
        return code, result, chart_df, None
    except Exception as e:
        return code, None, None, str(e)


# --- 메인 ---
st.title("📂 내 파일과 대화하기")
st.caption("CSV 또는 Excel 파일을 업로드하면 AI가 데이터를 분석하고 질문에 답변해 드립니다.")

if "data_messages" not in st.session_state:
    st.session_state["data_messages"] = [
        ChatMessage(role="assistant", content="CSV나 Excel 파일을 업로드해주시면 내용을 분석해 드릴게요.")
    ]
if "current_file" not in st.session_state:
    st.session_state["current_file"] = None

if uploaded_file:
    file_bytes = uploaded_file.getvalue()
    df, retriever = build_vectorstore(file_bytes, uploaded_file.name)

    if st.session_state["current_file"] != uploaded_file.name:
        st.session_state["data_messages"] = [
            ChatMessage(role="assistant", content=f"'{uploaded_file.name}' 파일을 분석했습니다. 궁금한 점을 물어보세요!")
        ]
        st.session_state["current_file"] = uploaded_file.name

    if retriever:
        st.success(f"✅ '{uploaded_file.name}' 분석 완료! ({len(df)}개의 데이터)")
else:
    st.info("👈 왼쪽 사이드바에서 CSV 또는 Excel 파일을 업로드해주세요.")
    df, retriever = None, None

for msg in st.session_state["data_messages"]:
    st.chat_message(msg.role).write(msg.content)

llm = ChatGroq(model=GROQ_MODEL, groq_api_key=groq_api_key, temperature=0)
user_input = st.chat_input("이 데이터에 대해 궁금한 점을 물어보세요")

if user_input and retriever:
    st.chat_message("user").write(user_input)
    st.session_state["data_messages"].append(ChatMessage(role="user", content=user_input))

    df_info = get_df_info(df)
    route = classify_question(llm, user_input, df_info)

    if route == "PANDAS":
        # --- pandas 코드 생성 경로 ---
        with st.chat_message("assistant"):
            with st.spinner("코드를 생성하고 있습니다..."):
                code, result, chart_df, error = generate_and_run_code(llm, user_input, df_info, df)

            # 생성된 코드 표시
            st.caption("🔧 생성된 pandas 코드")
            st.code(code, language="python")

            if error:
                # 코드 실행 실패 시 RAG로 폴백
                st.warning(f"⚠️ 코드 실행 중 오류가 발생하여 RAG 검색으로 전환합니다: {error}")
                retrieved_docs = retriever.invoke(user_input)
                context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])
                fallback_prompt = ChatPromptTemplate.from_template(
                    """/no_think
당신은 업로드된 데이터를 기반으로 답변하는 AI 데이터 분석가입니다.
반드시 한국어(한글)로만 답변하세요.
문맥에 없는 내용은 지어내지 말고 "데이터에서 찾을 수 없습니다"라고 답하세요.

[데이터 문맥]:
{context}

질문: {question}
답변:"""
                )
                full_response = ""
                response_container = st.empty()
                in_think = True
                buffer = ""
                for chunk in (fallback_prompt | llm).stream({"question": user_input, "context": context_text}):
                    delta = chunk.content
                    if in_think:
                        buffer += delta
                        if "</think>" in buffer:
                            full_response = buffer.split("</think>", 1)[1].lstrip("\n")
                            in_think = False
                            response_container.markdown(full_response)
                    else:
                        full_response += delta
                        response_container.markdown(full_response)
                st.session_state["data_messages"].append(ChatMessage(role="assistant", content=full_response))
            else:
                # 결과 표시
                if isinstance(result, pd.DataFrame):
                    st.dataframe(result, use_container_width=True)
                    result_text = f"```\n{result.to_string()}\n```"
                elif isinstance(result, pd.Series):
                    st.dataframe(result.to_frame(), use_container_width=True)
                    result_text = f"```\n{result.to_string()}\n```"
                else:
                    st.markdown(f"**결과:** {result}")
                    result_text = str(result)

                # 차트 표시
                if chart_df is not None:
                    try:
                        if isinstance(chart_df, pd.DataFrame):
                            st.bar_chart(chart_df)
                        elif isinstance(chart_df, pd.Series):
                            st.bar_chart(chart_df.to_frame())
                    except Exception:
                        pass

                st.session_state["data_messages"].append(
                    ChatMessage(role="assistant", content=f"🔧 pandas 코드로 분석했습니다.\n\n{result_text}")
                )
    else:
        # --- RAG 경로 ---
        retrieved_docs = retriever.invoke(user_input)
        context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])

        history_msgs = [m for m in st.session_state["data_messages"][:-1]
                        if "파일을 업로드" not in m.content and "분석했습니다" not in m.content]
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
            st.session_state["data_messages"].append(ChatMessage(role="assistant", content=full_response))

elif user_input and not retriever:
    st.warning("먼저 파일을 업로드해주세요.")
