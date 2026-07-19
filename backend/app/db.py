from __future__ import annotations

import sqlite3
from pathlib import Path

from .mock_seed_data import generate_database


APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "edu_insight_v2.db"


def _database_is_valid(db_path: Path) -> bool:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return False

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('students', 'classes', 'submissions')"
            )
            existing = {row[0] for row in cursor.fetchall()}
        return {"students", "classes", "submissions"}.issubset(existing)
    except sqlite3.DatabaseError:
        return False


def ensure_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _database_is_valid(DB_PATH):
        reset_database()


def reset_database() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    generate_database(DB_PATH)
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    ensure_database()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection
