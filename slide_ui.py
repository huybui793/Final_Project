import streamlit as st
from core.slide_process import generate_slides, build_pptx


def render_slide_creator():
    st.title("🖼️ Tạo slide bài giảng")

    if st.button("← Quay lại chat", key="exit_slides_btn"):
        for key in ["view", "slides", "slide_index", "slide_topic"]:
            st.session_state.pop(key, None)
        st.rerun()

    topic = st.text_input("Chủ đề của bộ slide", key="slide_topic_input")
    num_slides = st.slider("Số slide", 4, 10, 6, key="slide_count")

    if st.button("Tạo slide", key="generate_slides_btn"):
        if not topic.strip():
            st.error("Vui lòng nhập chủ đề")
        else:
            with st.spinner("Đang soạn slide..."):
                try:
                    docs = st.session_state.retriever.invoke(topic)
                    if not docs:
                        st.error("Chưa có tài liệu liên quan. Hãy upload tài liệu về chủ đề này trước.")
                    else:
                        context = "\n\n".join(d.page_content for d in docs[:3])
                        st.session_state.slides = generate_slides(context, topic, num_slides)
                        st.session_state.slide_topic = topic
                        st.session_state.slide_index = 0
                except Exception as e:
                    st.error(f"Không tạo được slide, hãy thử lại: {e}")

    slides = st.session_state.get("slides")
    if not slides:
        return

    st.divider()
    i = st.session_state.slide_index
    slide = slides[i]

    with st.container(border=True):
        st.subheader(slide["title"])
        for bullet in slide["bullets"]:
            st.markdown(f"- {bullet}")

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("← Trước", key="prev_slide", disabled=(i == 0)):
            st.session_state.slide_index -= 1
            st.rerun()
    with col_info:
        st.caption(f"Slide {i + 1}/{len(slides)}")
    with col_next:
        if st.button("Sau →", key="next_slide", disabled=(i == len(slides) - 1)):
            st.session_state.slide_index += 1
            st.rerun()

    st.download_button(
        "⬇️ Tải về (.pptx)",
        data=build_pptx(slides, st.session_state.slide_topic),
        file_name=f"{st.session_state.slide_topic}.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        key="download_pptx",
    )