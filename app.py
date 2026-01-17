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


# ==============================
# INIT DB (SAFE)
# ==============================

init_schema()

# ==============================
# UI – HEADER
# ==============================

st.title("📚 Bibliothèque personnelle")

# ==============================
# IMPORT EXCEL (CLOUD SAFE)
# ==============================

st.markdown("## 📥 Importer la bibliothèque")

uploaded_file = st.file_uploader(
    "Importer le fichier Excel (livre.xlsx)",
    type=["xlsx"]
)

force_import = st.checkbox("🔁 Forcer la réimportation (vider la base avant)")

if uploaded_file and st.button("🚀 Lancer l'import"):
    with st.spinner("Import en cours..."):
        conn = get_conn()
        cur = conn.cursor()

        if force_import:
            cur.execute("DELETE FROM books")
            conn.commit()

        # ⚠️ structure RÉELLE de ton fichier
        df = pd.read_excel(uploaded_file, sheet_name=0, header=0)

        # blocs colonnes : CAROLE / NILS / AXEL
        BLOCKS = {
            "CAROLE": (0, 7),
            "NILS":   (7, 14),
            "AXEL":   (14, 21)
        }

        inserted = 0

        for owner, (start, end) in BLOCKS.items():
            sub = df.iloc[:, start:end].copy()
            sub.columns = [
                "Auteur", "Titre", "Langue",
                "Lu", "Garde", "Edition", "_"
            ]

            for _, row in sub.iterrows():
                title = str(row["Titre"]).strip()
                if not title or title.lower() == "nan":
                    continue

                cur.execute("""
                    INSERT OR IGNORE INTO books
                    (owner, author, title, publisher, language, format, read, kept)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    owner,
                    str(row["Auteur"]).strip(),
                    title,
                    str(row["Edition"]).strip(),
                    str(row["Langue"]).strip(),
                    "Livre",
                    str(row["Lu"]).upper() == "TRUE",
                    str(row["Garde"]).upper() == "TRUE"
                ))
                inserted += 1

        conn.commit()
        conn.close()

    st.success(f"✅ Import terminé : {inserted} livres importés")
    st.rerun()

st.divider()

# ==============================
# UI – FILTRES
# ==============================

col1, col2, col3 = st.columns(3)

with col1:
    search = st.text_input("🔍 Recherche (titre / auteur)")

with col2:
    owner = st.selectbox("Propriétaire", ["TOUS", "CAROLE", "NILS", "AXEL"])

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
# EXEC
# ==============================

conn = get_conn()
rows = conn.execute(query, params).fetchall()
conn.close()

if not rows:
    st.info("📭 Aucun livre trouvé.")
else:
    df = pd.DataFrame([dict(r) for r in rows])
    st.success(f"📚 {len(df)} livres trouvés")
    st.dataframe(df, width="stretch", height=600)
