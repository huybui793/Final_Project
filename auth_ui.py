import streamlit as st
import uuid
from database.database import register_user, verify_login
from auth import is_valid_email, validate_password


def login_view():
    st.markdown("## 📚 Đăng nhập")
    st.caption("Trợ lý học tập Lịch sử AI")

    email = st.text_input("Email", placeholder="ban@example.com", key="login_email")
    password = st.text_input("Mật khẩu", type="password", key="login_password")

    if st.button("Đăng nhập", key="login_submit", use_container_width=True):
        if not email or not password:
            st.error("Vui lòng nhập đầy đủ email và mật khẩu")
        elif not is_valid_email(email):
            st.error("Email không đúng định dạng")
        else:
            user_id, name, role = verify_login(email, password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.user_name = name or email
                st.session_state.user_email = email
                st.session_state.user_role = role
                st.rerun()
            else:
                st.error("Email hoặc mật khẩu không đúng")

    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("Chưa có tài khoản?")
    with col2:
        if st.button("Đăng ký", key="go_register"):
            st.session_state.auth_view = "register"
            st.rerun()


def register_view():
    st.markdown("## 📚 Tạo tài khoản")
    st.caption("Trợ lý học tập Lịch sử AI")

    name = st.text_input("Họ và tên", placeholder="Nguyễn Văn A", key="reg_name")
    email = st.text_input("Email", placeholder="ban@example.com", key="reg_email")
    password = st.text_input("Mật khẩu", type="password", key="reg_password")
    password2 = st.text_input("Nhập lại mật khẩu", type="password", key="reg_password2")
    role_label = st.radio("Bạn là:", ["Học sinh", "Giáo viên"], key="reg_role", horizontal=True)

    st.caption("Mật khẩu cần: tối thiểu 8 ký tự, có chữ hoa, chữ thường và số.")

    if st.button("Tạo tài khoản", key="register_submit", use_container_width=True):
        errors = []

        if not name.strip():
            errors.append("Vui lòng nhập họ tên")
        if not email:
            errors.append("Vui lòng nhập email")
        elif not is_valid_email(email):
            errors.append("Email không đúng định dạng")

        if not password:
            errors.append("Vui lòng nhập mật khẩu")
        else:
            valid, pw_errors = validate_password(password)
            errors.extend(pw_errors)

        if password != password2:
            errors.append("Mật khẩu nhập lại không khớp")

        if errors:
            for e in errors:
                st.error(e)
        else:
            role = "student" if role_label == "Học sinh" else "teacher"
            success = register_user(str(uuid.uuid4()), email, password, name.strip(), role)
            if success:
                st.success("Tạo tài khoản thành công! Hãy đăng nhập.")
                st.session_state.auth_view = "login"
                st.rerun()
            else:
                st.error("Email này đã được đăng ký")

    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("Đã có tài khoản?")
    with col2:
        if st.button("Đăng nhập", key="go_login"):
            st.session_state.auth_view = "login"
            st.rerun()


def render_auth_page():
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "login"

    _, center, _ = st.columns([1, 2, 1])
    with center:
        if st.session_state.auth_view == "login":
            login_view()
        else:
            register_view()