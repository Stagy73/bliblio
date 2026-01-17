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

st.set_page_config("📚 Bibliothèque personnelle", layout="wide")

# ==============================
# DB
# ==============================
def get_conn():
    DATA_DIR.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT,
            category TEXT,
            author TEXT,
            title TEXT,
            language TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==============================
# UTILS
# ==============================
def clean(v):
    if pd.isna(v):
        return ""
    return str(v).replace("\n", " ").strip()

def normalize_columns(df):
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )
    return df

def find_col(df, names):
    for c in df.columns:
        for n in names:
            if n.lower() in c.lower():
                return c
    return None

# ==============================
# UI IMPORT
# ==============================
st.title("📚 Bibliothèque personnelle")
st.markdown("## 📥 Import Excel")

uploaded = st.file_uploader("Fichier Excel", type=["xlsx"])

if uploaded:
    xls = pd.ExcelFile(uploaded)
    sheet = st.selectbox("Onglet", xls.sheet_names)
    category = st.selectbox("Type", ["Livre", "BD"])
    wipe = st.checkbox("🗑️ Vider la base avant import")

    if st.button("🚀 Importer"):
        df = pd.read_excel(xls, sheet_name=sheet)
        df = normalize_columns(df)

        col_owner = find_col(df, ["proprio", "owner"])
        col_author = find_col(df, ["auteur", "author"])
        col_title = find_col(df, ["titre", "title"])
        col_lang = find_col(df, ["eng", "fr", "lang"])

        if not col_owner or not col_author or not col_title:
            st.error(f"❌ Colonnes introuvables : {df.columns.tolist()}")
            st.stop()

        conn = get_conn()
        cur = conn.cursor()

        if wipe:
            cur.execute("DELETE FROM books")
            conn.commit()

        inserted = 0

        for _, r in df.iterrows():
            owner = clean(r[col_owner])
            author = clean(r[col_author])
            title = clean(r[col_title])
            lang = clean(r[col_lang]) if col_lang else ""

            # ⚠️ on accepte même si langue vide
            if owner and author and title:
                cur.execute("""
                    INSERT INTO books (owner, category, author, title, language)
                    VALUES (?, ?, ?, ?, ?)
                """, (owner, category, author, title, lang))
                inserted += 1

        conn.commit()
        conn.close()

        st.success(f"✅ Import terminé : {inserted} lignes")

# ==============================
# RECHERCHE
# ==============================
st.divider()
st.markdown("## 🔍 Recherche")

c1, c2, c3 = st.columns(3)

with c1:
    search = st.text_input("Titre ou Auteur")

with c2:
    owner = st.selectbox("Propriétaire", ["TOUS", "Axel", "Carole", "Nils"])

with c3:
    category_f = st.selectbox("Type", ["TOUS", "Livre", "BD"])

query = "SELECT owner, category, author, title, language FROM books WHERE 1=1"
params = []

if search:
    query += " AND (title LIKE ? OR author LIKE ?)"
    params += [f"%{search}%", f"%{search}%"]

if owner != "TOUS":
    query += " AND owner = ?"
    params.append(owner)

if category_f != "TOUS":
    query += " AND category = ?"
    params.append(category_f)

query += " ORDER BY owner, category, author, title"

conn = get_conn()
rows = conn.execute(query, params).fetchall()
conn.close()

if rows:
    df = pd.DataFrame(rows, columns=[
        "Propriétaire", "Type", "Auteur", "Titre", "Langue"
    ])
    st.dataframe(df, use_container_width=True, height=650)
else:
    st.info("📭 Aucun résultat")
