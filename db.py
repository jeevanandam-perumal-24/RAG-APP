import json
import sqlite3
import uuid
from datetime import datetime

DB_FILE = "chat_history.db"

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
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id)
            )
        """)
        self.conn.commit()

    def create_chat(self, title="New chat"):
        chat_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO chats VALUES (?, ?, ?, ?)",
            (chat_id, title, now, now),
        )
        self.conn.commit()
        return chat_id

    def rename_chat(self, chat_id, title):
        self.conn.execute(
            "UPDATE chats SET title=?, updated_at=? WHERE id=?",
            (title.strip() or "New chat", datetime.utcnow().isoformat(), chat_id),
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
