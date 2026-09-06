import streamlit as st
from rag import RAGEngine
from db import ChatDB

st.set_page_config(page_title="RAG Chat", page_icon="💬", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
#MainMenu, footer { visibility: hidden; }
[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128,128,128,.18);
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
}
.chat-title {
    font-size: 1.35rem;
    font-weight: 650;
    margin-bottom: .25rem;
}
.chat-subtitle {
    color: #7b7b7b;
    font-size: .9rem;
    margin-bottom: 1rem;
}
.history-item button {
    text-align: left !important;
    border: 0 !important;
}
div[data-testid="stChatMessage"] {
    padding-top: .7rem;
    padding-bottom: .7rem;
}
.source-box {
    border: 1px solid rgba(128,128,128,.2);
    border-radius: 10px;
    padding: .6rem .8rem;
    margin-top: .5rem;
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_services():
    return ChatDB(), RAGEngine()

db, rag = get_services()

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

def load_chat(chat_id):
    st.session_state.chat_id = chat_id
    st.session_state.messages = db.get_messages(chat_id)

def new_chat():
    chat_id = db.create_chat("New chat")
    st.session_state.chat_id = chat_id
    st.session_state.messages = []

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown('<div class="chat-title">💬 RAG Chat</div>', unsafe_allow_html=True)
    st.markdown('<div class="chat-subtitle">Chat with your documents</div>', unsafe_allow_html=True)

    if st.button("＋  New chat", use_container_width=True):
        new_chat()
        st.rerun()

    st.divider()

    uploaded = st.file_uploader(
        "Add documents",
        type=["pdf", "txt", "md", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded:
        for f in uploaded:
            if st.button(f"📄  Index {f.name}", key=f"index_{f.name}", use_container_width=True):
                with st.spinner(f"Indexing {f.name}..."):
                    result = rag.ingest_file(f)
                st.success(f"{result} chunks indexed.")

    st.caption("Chat history")

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
                    f"💬  {label}",
                    key=f"chat_{chat['id']}",
                    use_container_width=True,
                ):
                    load_chat(chat["id"])
                    st.rerun()

    st.divider()
    st.caption(f"Indexed chunks: {rag.collection.count()}")

# ---------------- Main chat ----------------
if st.session_state.chat_id is None:
    new_chat()

st.markdown("### RAG Assistant")
st.caption("Ask questions about the documents you indexed.")

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

prompt = st.chat_input("Ask anything about your documents…")

if prompt:
    if not rag.is_configured:
        st.error("Azure OpenAI is not configured. Copy .env.example to .env and add your credentials.")
        st.stop()

    if not st.session_state.messages:
        db.rename_chat(st.session_state.chat_id, prompt[:60])

    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    db.add_message(st.session_state.chat_id, "user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    recent_history = st.session_state.messages[-8:]
    result = rag.answer(prompt, recent_history)

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
    db.add_message(
        st.session_state.chat_id,
        "assistant",
        result["answer"],
        result["sources"],
    )
