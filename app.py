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

st.set_page_config("📚 Bibliothèque personnelle", layout="wide")

# ==============================
# DB
# ==============================
def get_conn():
    DATA_DIR.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

init_db()

# ==============================
# UTILS
# ==============================
def clean(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def to_bool(v):
    return clean(v).lower() in ("1", "x", "true", "yes", "oui")

# ==============================
# UI – IMPORT
# ==============================
st.title("📚 Bibliothèque personnelle")
st.markdown("## 📥 Import Excel (onglet normalisé uniquement)")

uploaded = st.file_uploader(
    "Uploader le fichier Solde compte.xlsx",
    type=["xlsx"]
)

if uploaded:
    xls = pd.ExcelFile(uploaded)
    sheet = st.selectbox("Choisir l’onglet à importer", xls.sheet_names)
    wipe = st.checkbox("🗑️ Vider la base avant import")

    if st.button("🚀 Importer cet onglet"):
        df = pd.read_excel(xls, sheet_name=sheet)

        REQUIRED = [
            "Proprio",
            "Auteur",
            "Titre",
            "Eng, Fr",
            "Lu",
            "Gardé après lecture",
            "Edition (scolaires)"
        ]

        if not set(REQUIRED).issubset(df.columns):
            st.error("❌ Onglet NON conforme.\nUtilise uniquement l’onglet normalisé.")
            st.stop()

        conn = get_conn()
        cur = conn.cursor()

        if wipe:
            cur.execute("DELETE FROM books")
            conn.commit()

        inserted = 0

        for _, r in df.iterrows():
            owner = clean(r["Proprio"])
            author = clean(r["Auteur"])
            title = clean(r["Titre"])

            if not owner or not author or not title:
                continue

            cur.execute("""
                INSERT OR IGNORE INTO books
                (owner, category, author, title, language, read, kept, publisher)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                owner,
                "Livre",
                author,
                title,
                clean(r["Eng, Fr"]),
                to_bool(r["Lu"]),
                to_bool(r["Gardé après lecture"]),
                clean(r["Edition (scolaires)"])
            ))

            inserted += cur.rowcount

        conn.commit()
        conn.close()

        st.success(f"✅ Import terminé : {inserted} livres ajoutés")

# ==============================
# RECHERCHE
# ==============================
st.divider()
st.markdown("## 🔍 Recherche")

c1, c2, c3 = st.columns(3)

with c1:
    search = st.text_input("Titre ou Auteur")

with c2:
    owner = st.selectbox("Propriétaire", ["TOUS", "Carole", "Nils", "Axel"])

with c3:
    category = st.selectbox("Type", ["TOUS", "Livre", "BD"])

query = """
SELECT owner, category, author, title, language, read, kept, publisher
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

if category != "TOUS":
    query += " AND category = ?"
    params.append(category)

query += " ORDER BY owner, author, title"

conn = get_conn()
rows = conn.execute(query, params).fetchall()
conn.close()

if rows:
    df = pd.DataFrame(rows, columns=[
        "Propriétaire", "Type", "Auteur", "Titre",
        "Langue", "Lu", "Gardé", "Édition"
    ])
    df["Lu"] = df["Lu"].apply(lambda x: "✓" if x else "")
    df["Gardé"] = df["Gardé"].apply(lambda x: "✓" if x else "")
    st.dataframe(df, use_container_width=True, height=650)
else:
    st.info("📭 Aucun livre trouvé")
