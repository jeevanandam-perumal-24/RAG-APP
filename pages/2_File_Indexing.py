import streamlit as st
import os
from services.common_service import get_services
from constants.style_constant import page_style

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

@st.dialog("Login / Register", on_dismiss="rerun")
def login_warning_dialog():
    st.warning("Login needed to access this page!")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button(label="Login", icon="🔑", icon_position="left"):
            st.switch_page("./Home.py")

if not st.session_state.authenticated:
    login_warning_dialog()

db, rag, user_db = get_services()
st.set_page_config(page_title="Document Indexer", page_icon="📄", layout="wide", initial_sidebar_state="expanded")

st.markdown(page_style, unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"<div class='no-cursor' style='font-weight: bold; color:#88C0D0;'>Total Indexed chunks:</div><div class='no-cursor' style='color: #ECEFF4'>{rag.collection.count()}</div>", unsafe_allow_html=True)

st.markdown('<div class="files no-cursor" style="font-weight: bold; color: #88C0D0;">📜Indexed documents</div>', unsafe_allow_html=True)

if st.session_state.authenticated:
    folder_path = r"./data"
    files = [
        file for file in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, file))
    ]
    file_iterator = 0
    for file in files:
        if file.startswith("."):
            continue
        else:
            file_iterator += 1

            file_path = os.path.join(folder_path, file)
            col1, col2 = st.columns([6, 1], vertical_alignment="center")

            with col1:
                st.markdown(f"<div class='no-cursor' style='color: #ECEFF4;'>{file}</div>", unsafe_allow_html=True)

            with col2:
                with open(file_path, "rb") as f:
                    st.download_button(
                        "⬇️",
                        data=f,
                        file_name=file,
                        key=f"download_{file}",
                        help=f"Download-->{file}"
                    )

st.markdown('<div class="no-cursor" style="width: 100%; border-top: 1px solid #444; margin: 20px 0;"></div>', unsafe_allow_html=True)
st.markdown('<div class="files no-cursor" style="font-weight: bold; color: #88C0D0;">📤Upload documents<br></div>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    label="Add documents",
    type=["pdf", "txt", "md", "docx"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    max_upload_size=50,  # 50 MB
)

if uploaded:
    for f in uploaded:
        if st.button(f"📄  Index {f.name}", key=f"index_{f.name}", use_container_width=True):
            with st.spinner(f"Indexing {f.name}..."):
                result = rag.ingest_file(f)
            st.success(f"{result} chunks indexed.")