import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "books.sqlite"
SCHEMA_FILE = "schema.sql"

DB_PATH.parent.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)
with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
    conn.executescript(f.read())

conn.commit()
conn.close()

print("✅ Base SQLite créée proprement")
