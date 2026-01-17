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

st.set_page_config(page_title="📚 Bibliothèque personnelle", layout="wide")

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
            publisher TEXT,
            UNIQUE(owner, category, author, title)
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

def col(df, name):
    """Retourne le nom de colonne s’il existe, sinon None"""
    return name if name in df.columns else None

# ==============================
# UI – IMPORT
# ==============================
st.title("📚 Bibliothèque personnelle")
st.markdown("## 📥 Import du fichier Excel")

uploaded = st.file_uploader(
    "Uploader le fichier Solde compte.xls / xlsx",
    type=["xls", "xlsx"]
)

if uploaded:
    try:
        xls = pd.ExcelFile(uploaded)
    except Exception as e:
        st.error(f"❌ Impossible de lire le fichier Excel : {e}")
        st.stop()

    sheet = st.selectbox("Choisir l’onglet à importer", xls.sheet_names)
    category = st.selectbox("Type de contenu", ["Livre"])
    wipe = st.checkbox("🗑️ Vider la base avant import")

    if st.button("🚀 Importer cet onglet"):
        df = pd.read_excel(xls, sheet_name=sheet)

        # colonnes possibles (toutes optionnelles sauf 3)
        c_owner = col(df, "Proprio")
        c_author = col(df, "Auteur")
        c_title = col(df, "Titre")
        c_lang = col(df, "Eng, Fr")
        c_read = col(df, "Lu")
        c_kept = col(df, "Gardé après lecture")
        c_edit = col(df, "Edition (scolaires)")

        if not all([c_owner, c_author, c_title]):
            st.error("❌ Colonnes minimales requises : Proprio / Auteur / Titre")
            st.stop()

        conn = get_conn()
        cur = conn.cursor()

        if wipe:
            cur.execute("DELETE FROM books")
            conn.commit()

        inserted = 0

        for _, r in df.iterrows():
            owner = clean(r[c_owner])
            author = clean(r[c_author])
            title = clean(r[c_title])

            if not owner or not author or not title:
                continue

            cur.execute("""
                INSERT OR IGNORE INTO books
                (owner, category, author, title, language, read, kept, publisher)
                VALUES (?, 'Livre', ?, ?, ?, ?, ?, ?)
            """, (
                owner,
                author,
                title,
                clean(r[c_lang]) if c_lang else "",
                to_bool(r[c_read]) if c_read else 0,
                to_bool(r[c_kept]) if c_kept else 0,
                clean(r[c_edit]) if c_edit else ""
            ))

            inserted += cur.rowcount

        conn.commit()
        conn.close()

        st.success(f"✅ Import terminé : {inserted} livre(s) ajoutés")

# ==============================
# RECHERCHE & AFFICHAGE
# ==============================
st.divider()
st.markdown("## 🔍 Recherche")

c1, c2, c3 = st.columns(3)

with c1:
    search = st.text_input("Titre ou Auteur")

with c2:
    owner = st.selectbox("Propriétaire", ["TOUS", "Carole", "Nils", "Axel"])

with c3:
    category = st.selectbox("Type", ["TOUS", "Livre"])

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
