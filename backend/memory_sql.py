import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("chat_history.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_message(session_id: str, role: str, content: str):
    """Save a message to the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.now()),
    )
    conn.commit()
    conn.close()


def get_history_for_context(session_id: str, limit: int = 20):
    """Retrieve the last N messages for a session, ordered oldest to newest."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
        (session_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return list(reversed(rows))


def get_full_history(session_id: str):
    """Return all messages for a session, ordered oldest to newest."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC, id ASC",
        (session_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def list_sessions(limit: int = 20):
    """Return a list of recent session_ids with their latest timestamp."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT session_id, MAX(timestamp) as last_time FROM messages GROUP BY session_id ORDER BY last_time DESC LIMIT ?",
        (limit,),
    )
    sessions = cursor.fetchall()
    conn.close()
    return sessions


def delete_session(session_id: str):
    """Permanently delete all messages for a session."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


# Ensure DB and table exist on import
init_db()

