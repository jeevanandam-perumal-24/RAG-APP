import json
import sqlite3
import uuid
from datetime import datetime

DB_FILE = "rag.db"

class ChatDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at DATETIME2 NOT NULL,
                updated_at DATETIME2 NOT NULL)
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at DATETIME2 NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id))
        """)
        self.conn.commit()

    def create_chat(self, chat_id, title="New chat"):
        now = datetime.utcnow()
        self.conn.execute(
            "INSERT INTO chats VALUES (?, ?, ?, ?)",
            (chat_id, title, now, now),
        )
        self.conn.commit()
        return chat_id

    def rename_chat(self, chat_id, title):
        self.conn.execute(
            "UPDATE chats SET title=?, updated_at=? WHERE id=?",
            (title.strip() or "New chat", datetime.utcnow(), chat_id),
        )
        self.conn.commit()

    def add_message(self, chat_id, role, content, sources=None):
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """INSERT INTO messages(chat_id, role, content, sources, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (chat_id, role, content, json.dumps(sources or []), now),
        )
        self.conn.execute(
            "UPDATE chats SET updated_at=? WHERE id=?",
            (now, chat_id),
        )
        self.conn.commit()

    def get_messages(self, chat_id):
        rows = self.conn.execute(
            """SELECT role, content, sources
               FROM messages
               WHERE chat_id=?
               ORDER BY id""",
            (chat_id,),
        ).fetchall()

        return [
            {
                "role": row["role"],
                "content": row["content"],
                "sources": json.loads(row["sources"] or "[]"),
            }
            for row in rows
        ]

    def list_chats(self):
        rows = self.conn.execute(
            """SELECT id, title, updated_at
               FROM chats
               ORDER BY updated_at DESC"""
        ).fetchall()
        return [dict(row) for row in rows]

class UserDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                email TEXT NULL,
                username TEXT NULL,
                password TEXT NOT NULL,
                created_at DATETIME2 NOT NULL,
                updated_at DATETIME2 NOT NULL)
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                user_id TEXT NULL,
                created_at DATETIME2 NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id),
                FOREIGN KEY(user_id) REFERENCES user(id))
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_token TEXT NOT NULL,
                expires_at DATETIME2 NOT NULL,
                created_at DATETIME2 NOT NULL,
                FOREIGN KEY(user_id) REFERENCES user(id))
            """
        )
        self.conn.commit()

    def create_user(self, display_name, email, username, password):
        user_id = str(uuid.uuid4())
        now = datetime.utcnow()
        self.conn.execute(
            "INSERT INTO user VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, display_name, email, username, password, now, now),
        )
        self.conn.commit()
        return user_id

    def get_user(self, user_id):
        row = self.conn.execute(
            "SELECT * FROM user WHERE id=?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username):
        row = self.conn.execute(
            "SELECT * FROM user WHERE username=?",
            (username,),
        ).fetchone()
        return dict(row) if row else None

    def update_user(self, user_id, display_name=None, email=None, username=None, password=None):
        now = datetime.utcnow()
        updates = []
        params = []
        if display_name is not None:
            updates.append("display_name=?")
            params.append(display_name)
        if email is not None:
            updates.append("email=?")
            params.append(email)
        if username is not None:
            updates.append("username=?")
            params.append(username)
        if password is not None:
            updates.append("password=?")
            params.append(password)
        if updates:
            updates.append("updated_at=?")
            params.append(now)
            params.append(user_id)
            self.conn.execute(
                f"UPDATE user SET {', '.join(updates)} WHERE id=?",
                tuple(params),
            )
            self.conn.commit()

    def delete_user(self, user_id):
        self.conn.execute(
            "DELETE FROM user WHERE id=?",
            (user_id,),
        )
        self.conn.execute(
            "DELETE FROM user_chats WHERE user_id=?",
            (user_id,),
        )
        self.conn.commit()

    def add_user_chat(self, user_id, chat_id):
        now = datetime.utcnow()
        self.conn.execute(
            "INSERT INTO user_chats(chat_id, user_id, created_at) VALUES (?, ?, ?)",
            (chat_id, user_id, now),
        )
        self.conn.commit()

    def add_user_session(self, user_id: str, session_token: str, expires_at: datetime):
        now = datetime.utcnow()
        self.conn.execute(
            "INSERT INTO user_sessions(user_id, session_token, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (user_id, session_token, expires_at, now),
        )
        self.conn.commit()

    def delete_user_session(self, session_token: str):
        self.conn.execute(
            "DELETE FROM user_sessions WHERE session_token=?",
            (session_token),
        )
        self.conn.commit()

    def get_user_session(self, session_token: str) -> str | None:
        row = self.conn.execute(
            "SELECT user_id FROM user_sessions WHERE session_token=?",
            (session_token),
        ).fetchone()

        value = dict(row) if row else None
        return value.get("user_id")
        