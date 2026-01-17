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
# DB
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


init_schema()

# ==============================
# UTILS
# ==============================

def to_bool(val):
    return str(val).strip().lower() in ("true", "1", "yes", "x")

# ==============================
# UI – IMPORT
# ==============================

st.title("📚 Bibliothèque personnelle")
st.markdown("## 📥 Importer la bibliothèque (format propre)")

uploaded = st.file_uploader(
    "Importer le fichier Excel (livre_clean.xlsx)",
    type=["xlsx"]
)

force = st.checkbox("🔁 Forcer la réimportation (vider la base avant)")

if uploaded and st.button("🚀 Lancer l'import"):
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
            st.error("❌ Le fichier n'est pas au bon format (colonnes manquantes)")
            st.stop()

        inserted = 0

        for _, row in df.iterrows():
            title = str(row["titre"]).strip()
            author = str(row["auteur"]).strip()

            if not title or not author:
                continue

            cur.execute("""
                INSERT OR IGNORE INTO books
                (owner, type, author, title, language, read, kept, publisher)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["owner"],
                row["type"],
                author,
                title,
                str(row["langue"]),
                to_bool(row["lu"]),
                to_bool(row["garde"]),
                str(row["edition"])
            ))

            if cur.rowcount > 0:
                inserted += 1

        conn.commit()
        conn.close()

    st.success(f"✅ Import terminé : {inserted} livres ajoutés")
    st.rerun()

st.divider()

# ==============================
# FILTRES
# ==============================

st.markdown("## 🔍 Recherche")

c1, c2, c3 = st.columns(3)

with c1:
    search = st.text_input("Titre / Auteur")

with c2:
    owner = st.selectbox("Propriétaire", ["TOUS", "CAROLE", "NILS", "AXEL"])

with c3:
    type_ = st.selectbox("Type", ["TOUS", "Livre", "BD"])

# ==============================
# QUERY
# ==============================

query = """
SELECT owner, author, title, publisher, language, type, read, kept
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

if type_ != "TOUS":
    query += " AND type = ?"
    params.append(type_)

query += " ORDER BY owner, author, title"

conn = get_conn()
rows = conn.execute(query, params).fetchall()
conn.close()

# ==============================
# DISPLAY
# ==============================

if not rows:
    st.info("📭 Aucun livre trouvé.")
else:
    df = pd.DataFrame([dict(r) for r in rows])

    df["read"] = df["read"].apply(lambda x: "✓" if x else "")
    df["kept"] = df["kept"].apply(lambda x: "✓" if x else "")

    df.columns = [
        "Propriétaire", "Auteur", "Titre",
        "Éditeur", "Langue", "Type",
        "Lu", "Gardé"
    ]

    st.success(f"📚 {len(df)} livre(s)")
    st.dataframe(
        df,
        width="stretch",
        height=650,
        hide_index=True
    )
