import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

# ==============================
# CONFIG
# ==============================

DB_PATH = Path("data") / "books.sqlite"

st.set_page_config(
    page_title="Bibliothèque personnelle",
    layout="wide"
)

# ==============================
# DB
# ==============================

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_conn()

# ==============================
# UI
# ==============================

st.title("📚 Bibliothèque personnelle")

# --- Recherche ---
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
    params.extend([f"%{search}%", f"%{search}%"])

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

rows = conn.execute(query, params).fetchall()

if not rows:
    st.warning("Aucun livre trouvé.")
else:
    df = pd.DataFrame([dict(r) for r in rows])
    st.success(f"{len(df)} livres trouvés")
    st.dataframe(df, use_container_width=True, height=600)
