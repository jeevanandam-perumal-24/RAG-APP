import streamlit as st
import uuid

from constants.style_constant import page_style
from services.common_service import get_services

st.set_page_config(page_title="RAG Chat", page_icon="💬", layout="wide", initial_sidebar_state="expanded")

st.markdown(page_style, unsafe_allow_html=True)

db, rag, user_db = get_services()

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

def load_chat(chat_id):
    st.session_state.chat_id = chat_id
    st.session_state.messages = db.get_messages(chat_id)

def new_chat():
    chat_id = uuid.uuid1
    st.session_state.chat_id = chat_id
    st.session_state.messages = []

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown('<div class="chat-title" style="color: #88C0D0; font-weight: bold;">💬 RAG Chat</div>', unsafe_allow_html=True)
    
    if st.button("＋  New chat", use_container_width=True):
        new_chat()
        st.rerun()

    st.divider()

    st.markdown('<svg width="20" height="20" viewBox="0 0 24 24"><path d="icons/chat-history.png" /></svg><div class="chat-title" style="color: #88C0D0; font-weight: bold;">🕓Chat history</div>', unsafe_allow_html=True)

    chats = db.list_chats()
    if not chats:
        st.caption("No chats yet.")
    else:
        for chat in chats:
            if(chat["title"] == "New chat"):
                continue
            else:
                label = chat["title"][:42] or "New chat"
                if st.button(
                    f"{label}",
                    key=f"chat_{chat['id']}",
                    use_container_width=True,
                ):
                    load_chat(chat["id"])
                    st.rerun()
    st.divider()

# ---------------- Main chat ----------------
if st.session_state.chat_id is None:
    new_chat()

st.markdown("<div class='no-cursor' style='font-weight: bold; font-size: 20px;'>RAG Assistant</div>", unsafe_allow_html=True)
st.caption("<div class='no-cursor'>Ask questions about the documents you indexed.</div>", unsafe_allow_html=True)
if st.session_state.authenticated:
    st.write(f"Welcome, {st.session_state.username}")
else:
    st.warning("Log in to save your chat history.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for src in message["sources"]:
                    st.markdown(
                        f"**{src['file']}** · chunk {src['chunk']}  \n"
                        f"{src['text'][:700]}"
                    )

prompt = st.chat_input("Ask anything about your documents…", accept_audio = True)

if prompt:
    if prompt.text:
        if not st.session_state.messages and st.session_state.authenticated:
            db.create_chat(st.session_state.chat_id, prompt.text[:60])

        user_message = {"role": "user", "content": prompt.text}
        st.session_state.messages.append(user_message)
        if st.session_state.authenticated:
            db.add_message(st.session_state.chat_id, "user", prompt.text)

        with st.chat_message("user"):
            st.markdown(prompt.text)
    
        recent_history = st.session_state.messages[-8:]
        result = rag.answer(prompt.text, recent_history)
    
        with st.chat_message("assistant"):
            st.markdown(result["answer"])
            if result["sources"]:
                with st.expander("Sources"):
                    for src in result["sources"]:
                        st.markdown(
                            f"**{src['file']}** · chunk {src['chunk']}  \n"
                            f"{src['text'][:700]}"
                        )
    
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
        })
        if st.session_state.authenticated:
            db.add_message(
                st.session_state.chat_id,
                "assistant",
                result["answer"],
                result["sources"],
            )
