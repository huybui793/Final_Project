import streamlit as st
import os
import uuid

from core.pdf_process import (
    load_and_split_pdf,
    create_vector_store,
    add_documents_to_store
)

from core.rag_pipeline import answer_question


st.set_page_config(
    page_title="Trợ lý học tập Lịch sử AI",
    page_icon="📚"
)


if "chats" not in st.session_state:
    st.session_state.chats = {}

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

if "vector_store" not in st.session_state:
    st.session_state.vector_store = create_vector_store()


def new_chat():
    chat_id = str(uuid.uuid4())
    st.session_state.chats[chat_id] = {"title": "Cuộc trò chuyện mới", "messages": []}
    st.session_state.current_chat_id = chat_id

# tự tạo chat nếu chưa có
if st.session_state.current_chat_id is None:
    new_chat()

# --- Sidebar ---
st.sidebar.header("📚 Trợ lý học tập Lịch sử AI")

if st.sidebar.button("➕ New chat", use_container_width=True,key="new_chat_button"):
    new_chat()
    st.rerun()

st.sidebar.divider()
st.sidebar.header("Upload tài liệu")
uploaded_file = st.sidebar.file_uploader("Chọn file PDF", type=["pdf"])

if uploaded_file is not None:
    if st.sidebar.button("Xử lý tài liệu", key="process_doc_button"):
        with st.spinner("Đang xử lý tài liệu..."):
            temp_path = f"temp_{uploaded_file.name}"

            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            chunks = load_and_split_pdf(temp_path)

            add_documents_to_store(
                st.session_state.vector_store,
                chunks
            )

            os.remove(temp_path)


        st.sidebar.success(
            f"Đã thêm tài liệu! ({len(chunks)} đoạn)"
        )

st.sidebar.divider()
st.sidebar.subheader("Lịch sử trò chuyện")

# Hiện danh sách các cuộc chat, mới nhất lên trên
for chat_id in reversed(list(st.session_state.chats.keys())):
    chat = st.session_state.chats[chat_id]
    is_current = chat_id == st.session_state.current_chat_id
    label = ("🟢 " if is_current else "") + chat["title"]
    if st.sidebar.button(label, key=f"select_{chat_id}", use_container_width=True):
        st.session_state.current_chat_id = chat_id
        st.rerun()

#chat chính
current_chat = st.session_state.chats[st.session_state.current_chat_id]

st.title("📚 Trợ lý học tập Lịch sử AI")
st.subheader("Đặt câu hỏi")

for msg in current_chat["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Hỏi gì đó về tài liệu..."):
    current_chat["messages"].append({"role": "user", "content": prompt})
    
    # Đặt tiêu đề cuộc chat theo câu hỏi đầu tiên
    if current_chat["title"] == "Cuộc trò chuyện mới":
        current_chat["title"] = prompt[:30] + ("..." if len(prompt) > 30 else "")
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
                result = answer_question(
                    st.session_state.vector_store,
                    prompt
                )

        if result["type"] == "rag_answer":
            answer = result["answer"]
            st.markdown(answer)
            st.caption(f" {result['source']}")

        elif result["type"] == "youtube_fallback":
            answer = result["message"]
            st.markdown(answer)

            videos = result.get("videos", [])

            for video in videos:
                st.video(video["url"])
                st.caption(video["title"])

            if not videos:
                st.info("Không tìm thấy video phù hợp.")

        else:
            answer = result.get(
                "message",
                "⚠️ Đã xảy ra lỗi. Vui lòng thử lại sau."
            )
            st.warning(answer)

        current_chat["messages"].append({
            "role": "assistant",
            "content": answer
        })