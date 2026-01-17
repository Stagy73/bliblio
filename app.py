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

st.set_page_config(
    page_title="Bibliothèque personnelle",
    layout="wide"
)

# ==============================
# DB INIT (CLOUD SAFE)
# ==============================

def init_db():
    DATA_DIR.mkdir(exist_ok=True)

    if not DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialisation AU DÉMARRAGE
init_db()

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
# EXEC (THREAD SAFE)
# ==============================

with get_conn() as conn:
    rows = conn.execute(query, params).fetchall()

if not rows:
    st.warning("Aucun livre trouvé.")
else:
    df = pd.DataFrame([dict(r) for r in rows])
    st.success(f"{len(df)} livres trouvés")
    st.dataframe(df, width="stretch", height=600)
