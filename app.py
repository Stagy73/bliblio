import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

# ==============================
# CONFIG
# ==============================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "books.sqlite"
SCHEMA_PATH = BASE_DIR / "schema.sql"
EXCEL_FILE = BASE_DIR / "livre.xlsx"

st.set_page_config(
    page_title="Bibliothèque personnelle",
    layout="wide"
)

# ==============================
# DB CORE
# ==============================

def get_conn():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema():
    conn = get_conn()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def table_exists():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='books'
    """)
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def import_excel_once():
    if not EXCEL_FILE.exists():
        return

    conn = get_conn()
    cur = conn.cursor()

    # déjà importé ?
    cur.execute("SELECT COUNT(*) FROM books")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    sheets = {
        "Livres": "Livre",
        "BD": "BD"
    }

    for sheet, fmt in sheets.items():
        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
        except Exception:
            continue

        for _, row in df.iterrows():
            title = str(row.get("Titre", "")).strip()
            if not title:
                continue

            author = str(row.get("Auteur", "")).strip()
            publisher = str(row.get("Edition", "")).strip()
            language = str(row.get("Eng_Fr", "")).strip()
            read = bool(row.get("Lu", False))
            kept = bool(row.get("Gardé après lecture", False))

            cur.execute(
                """
                INSERT OR IGNORE INTO books
                (owner, author, title, publisher, language, format, read, kept)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "NILS",
                    author,
                    title,
                    publisher,
                    language,
                    fmt,
                    read,
                    kept
                )
            )

    conn.commit()
    conn.close()


# ==============================
# BOOTSTRAP (SAFE)
# ==============================

init_schema()

if table_exists():
    import_excel_once()

# ==============================
# UI
# ==============================

st.title("📚 Bibliothèque personnelle")

col1, col2, col3 = st.columns(3)

with col1:
    search = st.text_input("🔍 Recherche (titre / auteur)")

with col2:
    owner = st.selectbox("Propriétaire", ["TOUS", "NILS", "CAROLE"])

with col3:
    format_ = st.selectbox("Type", ["TOUS", "Livre", "BD"])

# ==============================
# QUERY (PROTÉGÉE)
# ==============================

query = """
SELECT id, owner, author, title, publisher, language, format
FROM books
WHERE 1=1
"""
params = []

if search:
    query += " AND (title LIKE ? OR author LIKE ?)"
    params += [f"%{search}%", f"%{search}%"]

if owner != "TOUS":
    query += " AND owner = ?"
    params.append(owner)

if format_ != "TOUS":
    query += " AND format = ?"
    params.append(format_)

query += " ORDER BY author, title"

# ==============================
# EXEC (ANTI-CRASH)
# ==============================

try:
    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()
except sqlite3.OperationalError:
    st.warning("📭 Base initialisée, aucun livre pour l’instant.")
    st.stop()

if not rows:
    st.info("Aucun livre trouvé.")
else:
    df = pd.DataFrame([dict(r) for r in rows])
    st.success(f"{len(df)} livres trouvés")
    st.dataframe(df, width="stretch", height=600)
