import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "generated" / "lifecycleiq.db"


def get_connection():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}. "
            "Run the data generator first."
        )

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def fetch_all(query, params=()):
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def fetch_one(query, params=()):
    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()
        return dict(row) if row else None


def fetch_value(query, params=()):
    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()
        return row[0] if row else 0