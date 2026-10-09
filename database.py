"""
database.py - Local SQLite Database Layer for Customer Concern Analyzer.
Handles schema initialization, persistence, retrieval, and deletion of customer concerns.
"""

import sqlite3
import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "concerns.db")


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Creates a database connection with dictionary-like row factory."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the SQLite database and creates the customer_concerns table if not present."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_concerns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                organization TEXT NOT NULL,
                urgency TEXT NOT NULL,
                core_concerns TEXT NOT NULL,
                transcript TEXT NOT NULL,
                drafted_response TEXT NOT NULL,
                audio_path TEXT NOT NULL
            )
            """
        )
        conn.commit()
    logger.debug("Database initialized successfully at %s", db_path)


def insert_concern(
    organization: str,
    urgency: str,
    core_concerns: List[str],
    transcript: str,
    drafted_response: str,
    audio_path: str,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Inserts a new analyzed concern record into the database. Returns the new row ID."""
    concerns_json = json.dumps(core_concerns)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO customer_concerns (
                timestamp, organization, urgency, core_concerns, transcript, drafted_response, audio_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                organization,
                urgency,
                concerns_json,
                transcript,
                drafted_response,
                audio_path,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_concerns(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves all past concern records ordered by newest first."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customer_concerns ORDER BY id DESC")
        rows = cursor.fetchall()

    results = []
    for row in rows:
        item = dict(row)
        try:
            item["core_concerns_list"] = json.loads(item["core_concerns"])
        except Exception:
            item["core_concerns_list"] = [item["core_concerns"]]
        results.append(item)
    return results


def get_concern_by_id(concern_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves a single concern record by ID."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customer_concerns WHERE id = ?", (concern_id,))
        row = cursor.fetchone()

    if row is None:
        return None

    item = dict(row)
    try:
        item["core_concerns_list"] = json.loads(item["core_concerns"])
    except Exception:
        item["core_concerns_list"] = [item["core_concerns"]]
    return item


def delete_concern(concern_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Deletes a concern record by ID."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customer_concerns WHERE id = ?", (concern_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_recent_summary_context(limit: int = 5, db_path: str = DEFAULT_DB_PATH) -> str:
    """Returns a compact summary of recent interactions to ground AI context."""
    records = get_all_concerns(db_path)[:limit]
    if not records:
        return "No previous interaction history."
    summary_lines = []
    for r in records:
        concerns = ", ".join(r.get("core_concerns_list", []))
        summary_lines.append(
            f"- Case #{r['id']} ({r['timestamp']}): {r['organization']} [{r['urgency']} Urgency] — Concerns: {concerns}"
        )
    return "\n".join(summary_lines)
