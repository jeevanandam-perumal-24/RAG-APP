import os
import secrets
import streamlit as st

from cryptography.fernet import Fernet
from services.cookie_handler import CookieHandler
from db import ChatDB, UserDB
from rag import RAGEngine
from datetime import datetime, timedelta

@st.cache_resource
def get_services():
    return ChatDB(), RAGEngine(), UserDB()


encryption_key = os.getenv("ENCRYPTION_KEY", "")
user_session_cookie_key = os.getenv("USER_SESSION_COOKIE_KEY", "")
encryption = Fernet(encryption_key)

chat_db, rag, user_db = get_services()
cookie_handler = CookieHandler()

def is_user_name_available(username):
    user = user_db.get_user_by_username(username)
    return user is None

def encrypt_password(password: str):
    if password is None:
        return None
    return encryption.encrypt(password.encode("utf-8"))

def decrypt_password(encrypted_password: str):
    if encrypted_password is None:
        return None
    return encryption.decrypt(encrypted_password).decode()

def add_user_session(user_id: str):
    expiry = datetime.now() + timedelta(hours=1)
    session_token = secrets.token_urlsafe(32)
    cookie_handler.set_cookie(user_session_cookie_key, session_token, expiry)
    user_db.add_user_session(user_id, session_token, expiry)

def get_user_session() -> str:
    token = cookie_handler.get_cookie(user_session_cookie_key)
    if token:
        return user_db.get_user_session(token)
    else:
        return None

def clear_session():
    token = cookie_handler.get_cookie(user_session_cookie_key)
    cookie_handler.clear_cookie(user_session_cookie_key)
    user_db.delete_user_session(token)