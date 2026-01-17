import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "books.sqlite"
SCHEMA_PATH = Path("schema.sql")

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH.as_posix(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
