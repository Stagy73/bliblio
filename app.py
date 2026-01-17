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
EXCEL_PATH = BASE_DIR / "livre.xlsx"
SCHEMA_PATH = BASE_DIR / "schema.sql"

st.set_page_config(
    page_title="Bibliothèque personnelle",
    layout="wide"
)

# ==============================
# DB INIT
# ==============================

def init_db():
    DATA_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner TEXT,
        author TEXT,
        title TEXT,
        language TEXT,
        read INTEGER,
        kept INTEGER,
        format TEXT
    )
    """)
    conn.commit()
    conn.close()

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==============================
# IMPORT EXCEL (1 seule fois)
# ==============================

def import_excel_once():
    if not EXCEL_PATH.exists():
        st.warning("📄 livre.xlsx introuvable – aucun import")
        return

    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        if count > 0:
            return  # déjà importé

        xls = pd.ExcelFile(EXCEL_PATH)

        for sheet, fmt in [("Livres", "Livre"), ("BD", "BD")]:
            if sheet not in xls.sheet_names:
                continue

            df = pd.read_excel(xls, sheet_name=sheet)

            for _, row in df.iterrows():
                author = str(row.get("Auteur", "")).strip()
                title = str(row.get("Titre", "")).strip()

                if not title:
                    continue

                language = str(
                    row.get("Eng_Fr", row.get("Langue", ""))
                ).strip()

                read = int(str(row.get("Lu", "FALSE")).upper() == "TRUE")
                kept = int(str(row.get("Gardé après lecture", "FALSE")).upper() == "TRUE")

                conn.execute("""
                INSERT INTO books (owner, author, title, language, read, kept, format)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "NILS",  # propriétaire par défaut
                    author,
                    title,
                    language,
                    read,
                    kept,
                    fmt
                ))

        conn.commit()

# ==============================
# INIT AU DÉMARRAGE
# ==============================

init_db()
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
# QUERY
# ==============================

query = """
SELECT owner, author, title, language, read, kept, format
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
# EXEC
# ==============================

with get_conn() as conn:
    rows = conn.execute(query, params).fetchall()

if not rows:
    st.info("Aucun livre trouvé.")
else:
    df = pd.DataFrame([dict(r) for r in rows])
    st.success(f"{len(df)} éléments trouvés")
    st.dataframe(df, width="stretch", height=600)
