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

st.set_page_config(
    page_title="Bibliothèque personnelle",
    layout="wide"
)

# ==============================
# DB
# ==============================

def get_conn():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT,
            type TEXT,
            author TEXT,
            title TEXT,
            language TEXT,
            read INTEGER,
            kept INTEGER,
            publisher TEXT,
            UNIQUE(owner, author, title)
        )
    """)
    conn.commit()
    conn.close()


init_db()

# ==============================
# UTILS
# ==============================

def to_bool(val):
    return str(val).strip().lower() in ("true", "1", "yes", "x")

# ==============================
# UI – IMPORT
# ==============================

st.title("📚 Bibliothèque personnelle")
st.markdown("## 📥 Import Excel (format propre)")

uploaded = st.file_uploader(
    "Importer le fichier livre_clean.xlsx",
    type=["xlsx"]
)

force = st.checkbox("🔁 Vider la base avant import")

if uploaded and st.button("🚀 Importer"):
    with st.spinner("Import en cours…"):
        conn = get_conn()
        cur = conn.cursor()

        if force:
            cur.execute("DELETE FROM books")
            conn.commit()

        df = pd.read_excel(uploaded)

        REQUIRED = {
            "owner", "type", "auteur", "titre",
            "langue", "lu", "garde", "edition"
        }

        if not REQUIRED.issubset(df.columns):
            st.error("❌ Mauvais format Excel")
            st.stop()

        inserted = 0

        for _, row in df.iterrows():
            if not str(row["titre"]).strip():
                continue

            cur.execute("""
                INSERT OR IGNORE INTO books
                (owner, type, author, title, language, read, kept, publisher)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["owner"],
                row["type"],
                row["auteur"],
                row["titre"],
                row["langue"],
                to_bool(row["lu"]),
                to_bool(row["garde"]),
                row["edition"]
            ))

            if cur.rowcount > 0:
                inserted += 1

        conn.commit()
        conn.close()

    st.success(f"✅ {inserted} livres importés")
    st.rerun()

st.divider()

# ==============================
# RECHERCHE
# ==============================

c1, c2, c3 = st.columns(3)

with c1:
    search = st.text_input("Titre / Auteur")

with c2:
    owner = st.selectbox("Propriétaire", ["TOUS", "CAROLE", "NILS", "AXEL"])

with c3:
    type_ = st.selectbox("Type", ["TOUS", "Livre", "BD"])

query = "SELECT owner, author, title, publisher, language, type, read, kept FROM books WHERE 1=1"
params = []

if search:
    query += " AND (title LIKE ? OR author LIKE ?)"
    params += [f"%{search}%", f"%{search}%"]

if owner != "TOUS":
    query += " AND owner = ?"
    params.append(owner)

if type_ != "TOUS":
    query += " AND type = ?"
    params.append(type_)

query += " ORDER BY owner, author, title"

conn = get_conn()
rows = conn.execute(query, params).fetchall()
conn.close()

if not rows:
    st.info("📭 Aucun livre")
else:
    df = pd.DataFrame(rows, columns=[
        "Propriétaire", "Auteur", "Titre",
        "Éditeur", "Langue", "Type",
        "Lu", "Gardé"
    ])

    df["Lu"] = df["Lu"].apply(lambda x: "✓" if x else "")
    df["Gardé"] = df["Gardé"].apply(lambda x: "✓" if x else "")

    st.success(f"📚 {len(df)} livres")
    st.dataframe(df, use_container_width=True, height=650)
