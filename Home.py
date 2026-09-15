import streamlit as st
import secrets
from services.common_service import get_services, is_user_name_available, encrypt_password, decrypt_password, add_user_session, get_user_session, clear_session
from constants.style_constant import page_style

st.set_page_config(page_title="RAG App", page_icon="🤖", layout="wide")

st.markdown(page_style, unsafe_allow_html=True)

db, rag, user_db = get_services()

@st.dialog("Login / Register", on_dismiss="ignore")
def login_message_dialog(is_login_succes: bool = False, is_user_name_available: bool = True, is_password_mismatch: bool = False, is_field_reqiured: bool = False, is_invalid_details: bool = False):
    if is_login_succes:
        st.success("Registration successful. Please login.")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(label="Login", icon="🔑", icon_position="left"):
                st.switch_page("Home.py")
    if not is_user_name_available:
        st.error("Username is already taken.")
    if is_invalid_details:
        st.error("Invalid username or password")
    if is_password_mismatch:
        st.error("Passwords do not match.")
    if is_field_reqiured:
        st.error("All fields are required.")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "auth_tab" not in st.session_state:
    st.session_state.auth_tab = "Login"

user_id = get_user_session()
if user_id is not None:
    st.session_state.user_id = user_id
    user_details = user_db.get_user(user_id)
    st.session_state.authenticated = True
    st.session_state.user_name = user_details["display_name"] if user_details["display_name"] else user_details["username"]

if not st.session_state.authenticated:
    st.title("Welcome to RAG App")

    selected_tab = st.segmented_control(
        "",
        ["Login", "Register"],
        default=st.session_state.auth_tab,
        key="auth_tab"
    )

    if selected_tab == "Login":
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            submitted = st.form_submit_button(label="Login", icon="🔑", icon_position="right", use_container_width=True)

            if submitted:
                user = user_db.get_user_by_username(username)
                if user is not None:
                    user_password = decrypt_password(user.get("password")).__str__()
                    if password == user_password:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        user_id = user.get("id")
                        st.session_state.user_id = user_id
                        add_user_session(user_id)
                        st.success("Login successful!")

                        st.switch_page("pages/1_Chat.py")
                    else:
                        login_message_dialog(is_invalid_details=True)
                else:
                    login_message_dialog(is_invalid_details=True)

    elif selected_tab == "Register":
        with st.form("register_form"):
            username = st.text_input("Username", key="register_username")
            email = st.text_input("Email")
            display_name = st.text_input("Display Name")
            password = st.text_input("Password", type="password",key="register_password")

            confirm_password = st.text_input("Confirm Password", type="password")

            submitted = st.form_submit_button("Register", icon="📲", icon_position="right", use_container_width=True)

            if submitted:
                if not username or not email or not password:
                    login_message_dialog(is_field_reqiured=True)
                elif password != confirm_password:
                    login_message_dialog(is_password_mismatch=True)
                elif not is_user_name_available(username):
                    login_message_dialog(is_user_name_available=False)
                else:
                    encrypted_password = encrypt_password(password)
                    user_id = user_db.create_user(display_name, email, username, encrypted_password)
                    login_message_dialog(is_login_succes=True)
                    st.session_state.auth_tab = "Login"
                    st.stop()
                    st.rerun()