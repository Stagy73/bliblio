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
            language TEXT,
            read INTEGER,
            kept INTEGER,
            publisher TEXT
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
    return str(v).strip()

def to_bool(v):
    return clean(v).lower() in ("1", "x", "true", "yes", "oui")

def normalize_columns(df):
    """ Nettoie TOUTES les entêtes Excel """
    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )
    return df

def find_column(df, possible_names):
    """ Trouve une colonne même mal nommée """
    for col in df.columns:
        for name in possible_names:
            if name.lower() in col.lower():
                return col
    return None

# ==============================
# UI – IMPORT
# ==============================
st.title("📚 Bibliothèque personnelle")
st.markdown("## 📥 Import Excel (tolérant & robuste)")

uploaded = st.file_uploader(
    "Uploader un fichier Excel (.xlsx)",
    type=["xlsx"]
)

if uploaded:
    xls = pd.ExcelFile(uploaded)
    sheet = st.selectbox("Choisir l’onglet", xls.sheet_names)
    wipe = st.checkbox("🗑️ Vider la base avant import")

    if st.button("🚀 Importer"):
        df = pd.read_excel(xls, sheet_name=sheet)
        df = normalize_columns(df)

        # 🔍 Détection intelligente des colonnes
        col_owner = find_column(df, ["proprio", "owner"])
        col_author = find_column(df, ["auteur", "author"])
        col_title = find_column(df, ["titre", "title"])
        col_lang = find_column(df, ["eng", "fr", "lang"])
        col_read = find_column(df, ["lu", "read"])
        col_kept = find_column(df, ["gardé", "garde", "kept"])
        col_pub = find_column(df, ["edition", "éditeur"])

        if not col_owner or not col_author or not col_title:
            st.error(
                "❌ Colonnes indispensables introuvables\n\n"
                f"Colonnes détectées : {list(df.columns)}"
            )
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

            if not owner or not author or not title:
                continue

            cur.execute("""
                INSERT INTO books
                (owner, category, author, title, language, read, kept, publisher)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                owner,
                "Livre",
                author,
                title,
                clean(r[col_lang]) if col_lang else "",
                to_bool(r[col_read]) if col_read else False,
                to_bool(r[col_kept]) if col_kept else False,
                clean(r[col_pub]) if col_pub else ""
            ))

            inserted += 1

        conn.commit()
        conn.close()

        st.success(f"✅ Import réussi : {inserted} livres")

# ==============================
# RECHERCHE / AFFICHAGE
# ==============================
st.divider()
st.markdown("## 🔍 Recherche")

c1, c2 = st.columns(2)

with c1:
    search = st.text_input("Titre ou Auteur")

with c2:
    owner = st.selectbox("Propriétaire", ["TOUS", "Axel", "Carole", "Nils"])

query = """
SELECT owner, author, title, language
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

query += " ORDER BY owner, author, title"

conn = get_conn()
rows = conn.execute(query, params).fetchall()
conn.close()

if rows:
    df = pd.DataFrame(rows, columns=["Proprio", "Auteur", "Titre", "Langue"])
    st.dataframe(df, use_container_width=True, height=650)
else:
    st.info("📭 Aucun livre trouvé")
