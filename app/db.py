"""Database management and fixtures for Web Security Control Lab."""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import DB_PATH, DEFAULT_FIXTURE_USERS

_connection: Optional[sqlite3.Connection] = None


def get_db_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _connection = conn
        init_db(conn)
    return _connection


def init_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            display_name TEXT NOT NULL
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            username TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    # Insert test fixtures if not present
    for u in DEFAULT_FIXTURE_USERS:
        cursor.execute(
            """
            INSERT OR IGNORE INTO users (username, password, role, display_name)
            VALUES (?, ?, ?, ?)
            """,
            (u["username"], u["password"], u["role"], u["display_name"]),
        )
    conn.commit()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_session_record(session_id: str, username: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT OR REPLACE INTO sessions (session_id, username, created_at) VALUES (?, ?, ?)",
        (session_id, username, now_iso),
    )
    conn.commit()


def delete_session_record(session_id: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()


def get_user_from_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.id, u.username, u.role, u.display_name
        FROM sessions s
        JOIN users u ON s.username = u.username
        WHERE s.session_id = ?
        """,
        (session_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def add_audit_log(event_type: str, username: str, ip_address: str, details: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO audit_logs (event_type, username, ip_address, details, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (event_type, username, ip_address, details, now_iso),
    )
    conn.commit()


def get_audit_logs() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC")
    return [dict(row) for row in cursor.fetchall()]


def clear_audit_logs() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_logs")
    conn.commit()
