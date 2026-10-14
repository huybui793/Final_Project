import streamlit as st
import os
import uuid
from core.pdf_process import (
    load_and_split_pdf, create_vector_store, create_retriever, add_documents_to_retriever
)
from core.rag_pipeline import answer_question
from core.exam_process import is_history_document, generate_exam_questions
from database.database import (
    create_chat, update_chat_title, add_message, get_all_chats, get_messages,
    create_exam, get_all_exams, get_exam_by_id, submit_exam, save_quiz_result
)
from auth_ui import render_auth_page
from slide_ui import render_slide_creator
from report_ui import render_exam_report

st.set_page_config(page_title="Trợ lý học tập Lịch sử AI", page_icon="📚")

# ================== KIỂM TRA ĐĂNG NHẬP ==================
if "user_id" not in st.session_state:
    render_auth_page()
    st.stop()

# ================== KHỞI TẠO ==================
if "vector_store" not in st.session_state:
    st.session_state.vector_store = create_vector_store()

if "retriever" not in st.session_state:
    st.session_state.retriever = create_retriever(st.session_state.vector_store)

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None


def new_chat():
    chat_id = str(uuid.uuid4())
    create_chat(chat_id, st.session_state.user_id, "Cuộc trò chuyện mới")
    st.session_state.current_chat_id = chat_id


def clear_exam_state():
    for key in [
        "current_exam_id", "exam_submitted", "exam_score",
        "exam_results_detail", "report_videos"
    ]:
        st.session_state.pop(key, None)


def clear_slide_state():
    for key in ["view", "slides", "slide_index", "slide_topic", "gamma_result"]:
        st.session_state.pop(key, None)


if st.session_state.current_chat_id is None:
    user_chats = get_all_chats(st.session_state.user_id)
    if user_chats:
        st.session_state.current_chat_id = user_chats[0][0]
    else:
        new_chat()

# Đang làm bài kiểm tra? (chỉ áp dụng cho học sinh)
in_exam = (
    st.session_state.user_role == "student"
    and "current_exam_id" in st.session_state
)

# ================== ẨN SIDEBAR KHI ĐANG LÀM BÀI ==================
if in_exam:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarCollapsedControl"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ================== SIDEBAR ==================
role_label = "Giáo viên" if st.session_state.user_role == "teacher" else "Học sinh"
st.sidebar.write(f"👤 **{st.session_state.user_name}** ({role_label})")
st.sidebar.caption(st.session_state.user_email)

if st.sidebar.button("Đăng xuất", key="logout_btn"):
    for key in [
        "user_id", "user_name", "user_email", "user_role", "current_chat_id", "auth_view"
    ]:
        st.session_state.pop(key, None)
    clear_exam_state()
    clear_slide_state()
    st.rerun()

st.sidebar.divider()

if not in_exam:
    if st.sidebar.button("➕ New chat", use_container_width=True, key="new_chat_button"):
        new_chat()
        clear_slide_state()
        st.rerun()

    if st.sidebar.button("🖼️ Tạo slide", use_container_width=True, key="open_slides_btn"):
        st.session_state.view = "slides"
        st.rerun()

    st.sidebar.divider()
    st.sidebar.header("Upload tài liệu")
    uploaded_file = st.sidebar.file_uploader("Chọn file PDF", type=["pdf"], key="rag_upload")

    if uploaded_file is not None:
        if st.sidebar.button("Xử lý tài liệu", key="process_doc_button"):
            with st.spinner("Đang xử lý tài liệu (file dài có thể mất vài phút)..."):
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                documents = load_and_split_pdf(temp_path)
                try:
                    add_documents_to_retriever(st.session_state.retriever, documents)
                    st.sidebar.success(f"Đã thêm tài liệu! ({len(documents)} trang)")
                except Exception as e:
                    st.sidebar.error(f"Lỗi: {e}")
                os.remove(temp_path)

    st.sidebar.divider()
    st.sidebar.subheader("Lịch sử trò chuyện")

    user_chats = get_all_chats(st.session_state.user_id)
    for chat_id, title in user_chats:
        is_current = chat_id == st.session_state.current_chat_id
        label = ("🟢 " if is_current else "") + title
        if st.sidebar.button(label, key=f"select_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            clear_slide_state()
            st.rerun()

    # ---------- Phân quyền: giáo viên / học sinh ----------
    st.sidebar.divider()

    if st.session_state.user_role == "teacher":
        st.sidebar.subheader("📝 Tạo bài kiểm tra")
        exam_file = st.sidebar.file_uploader("Upload tài liệu để tạo đề", type=["pdf"], key="exam_upload")
        exam_title = st.sidebar.text_input("Tên bài kiểm tra", key="exam_title")

        if exam_file is not None and st.sidebar.button("Kiểm tra & Tạo đề", key="create_exam_btn"):
            with st.spinner("Đang kiểm tra tài liệu..."):
                temp_path = f"temp_exam_{exam_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(exam_file.getbuffer())
                documents = load_and_split_pdf(temp_path)
                full_text = "\n".join([d.page_content for d in documents[:5]])
                os.remove(temp_path)

                if not is_history_document(full_text):
                    st.sidebar.error("Tài liệu này không thuộc lĩnh vực Lịch sử. Vui lòng upload tài liệu khác.")
                else:
                    with st.spinner("Đang tạo câu hỏi..."):
                        try:
                            questions = generate_exam_questions(full_text)
                            exam_id = str(uuid.uuid4())
                            title = exam_title or f"Bài kiểm tra {exam_file.name}"
                            create_exam(exam_id, st.session_state.user_id, title, questions)
                            st.sidebar.success(f"Đã tạo bài kiểm tra '{title}' ({len(questions)} câu hỏi)!")
                        except Exception as e:
                            st.sidebar.error(f"Không tạo được đề, hãy thử lại: {e}")

    else:  # student
        st.sidebar.subheader("📝 Bài kiểm tra")
        all_exams = get_all_exams()
        if all_exams:
            exam_titles = {e["exam_id"]: e["title"] for e in all_exams}
            selected_exam_id = st.sidebar.selectbox(
                "Chọn bài kiểm tra",
                options=list(exam_titles.keys()),
                format_func=lambda x: exam_titles[x],
                key="select_exam",
            )
            if st.sidebar.button("Làm bài", key="start_exam_btn"):
                clear_exam_state()
                clear_slide_state()
                st.session_state.current_exam_id = selected_exam_id
                st.rerun()
        else:
            st.sidebar.info("Chưa có bài kiểm tra nào")

# ================== MÀN HÌNH LÀM BÀI KIỂM TRA (HỌC SINH) ==================
if in_exam:
    exam = get_exam_by_id(st.session_state.current_exam_id)
    exam_id = exam["exam_id"]

    if not st.session_state.get("exam_submitted", False):
        # --- Đang làm bài ---
        if st.button("← Thoát bài kiểm tra", key="exit_exam_btn"):
            clear_exam_state()
            st.rerun()

        st.title(f"📝 {exam['title']}")

        user_answers = {}
        for i, q in enumerate(exam["questions"]):
            st.write(f"**Câu {i + 1}: {q['question']}**")
            user_answers[i] = st.radio(
                "",
                q["options"],
                key=f"exam_q_{exam_id}_{i}",
                index=None,
                label_visibility="collapsed",
            )

        if st.button("Nộp bài", key="submit_exam_btn"):
            unanswered = [i + 1 for i, ans in user_answers.items() if ans is None]
            if unanswered:
                st.error(f"Bạn chưa trả lời câu {', '.join(map(str, unanswered))}.")
            else:
                score = 0
                answers_to_save = {}
                results_detail = []

                for i, q in enumerate(exam["questions"]):
                    is_correct = user_answers[i][0] == q["correct_answer"]
                    if is_correct:
                        score += 1
                    save_quiz_result(st.session_state.user_id, q["topic"], q["question"], is_correct)
                    answers_to_save[str(i)] = user_answers[i]  # key phải là string để lưu MongoDB
                    results_detail.append({
                        "question": q["question"],
                        "topic": q["topic"],
                        "options": q["options"],
                        "selected": user_answers[i],
                        "correct_answer": q["correct_answer"],
                        "is_correct": is_correct,
                    })

                submit_exam(exam_id, st.session_state.user_id, answers_to_save, score, len(exam["questions"]))
                st.session_state.exam_submitted = True
                st.session_state.exam_score = score
                st.session_state.exam_results_detail = results_detail
                st.rerun()

    else:
        # --- Xem điểm, báo cáo và đáp án ---
        st.title(f"📝 {exam['title']}")
        score = st.session_state.exam_score
        total = len(exam["questions"])
        st.success(f"Bạn đúng {score}/{total} câu ({round(score / total * 100)}%)")

        render_exam_report(st.session_state.exam_results_detail, st.session_state.user_id)

        st.divider()
        st.subheader("Chi tiết đáp án")

        for i, r in enumerate(st.session_state.exam_results_detail):
            st.write(f"**Câu {i + 1}: {r['question']}**")
            for opt in r["options"]:
                if opt[0] == r["correct_answer"]:
                    st.markdown(f"✅ {opt} *(đáp án đúng)*")
                elif opt == r["selected"] and not r["is_correct"]:
                    st.markdown(f"❌ {opt} *(bạn đã chọn)*")
                else:
                    st.write(opt)
            st.write("")

        if st.button("Quay lại", key="back_from_exam"):
            clear_exam_state()
            st.rerun()

    st.stop()

# ================== TRANG TẠO SLIDE ==================
if st.session_state.get("view") == "slides":
    render_slide_creator()
    st.stop()

# ================== KHU VỰC CHAT CHÍNH ==================
st.title("📚 Trợ lý học tập Lịch sử AI")
st.subheader("Đặt câu hỏi")

messages = get_messages(st.session_state.current_chat_id)
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Hỏi gì đó về tài liệu..."):
    add_message(st.session_state.current_chat_id, "user", prompt)

    if len(messages) == 0:
        title = prompt[:30] + ("..." if len(prompt) > 30 else "")
        update_chat_title(st.session_state.current_chat_id, title)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
            result = answer_question(st.session_state.retriever, st.session_state.vector_store, prompt)

        if result["type"] == "rag_answer":
            answer = result["answer"]
            st.markdown(answer)
            st.caption(f"📄 {result['source']}")
        else:
            answer = result["message"]
            st.markdown(answer)
            for video in result["videos"]:
                st.video(video["url"])
                st.caption(video["title"])

        add_message(st.session_state.current_chat_id, "assistant", answer)

    st.rerun()