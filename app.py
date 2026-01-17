import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import math

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
    """Convertit proprement Excel → bool"""
    if val is True:
        return True
    if val is False:
        return False
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return False
    return str(val).strip().lower() in ("true", "1", "yes", "x")

# ==============================
# UI
# ==============================

st.title("📚 Bibliothèque personnelle")

st.markdown("## 📥 Importer la bibliothèque")

uploaded = st.file_uploader(
    "Importer le fichier Excel (livre.xlsx)",
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

        df = pd.read_excel(uploaded, header=0)

        # blocs colonnes EXACTS du fichier réel
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
                    to_bool(row["Lu"]),
                    to_bool(row["Garde"])
                ))
                inserted += 1

        conn.commit()
        conn.close()

    st.success(f"✅ Import terminé : {inserted} livres importés")
    st.rerun()

st.divider()

# ==============================
# FILTRES
# ==============================

c1, c2, c3 = st.columns(3)

with c1:
    search = st.text_input("🔍 Recherche (titre / auteur)")

with c2:
    owner = st.selectbox("Propriétaire", ["TOUS", "CAROLE", "NILS", "AXEL"])

with c3:
    format_ = st.selectbox("Type", ["TOUS", "Livre", "BD"])

# ==============================
# QUERY
# ==============================

query = """
SELECT owner, author, title, publisher, language, format
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

query += " ORDER BY owner, author, title"

conn = get_conn()
rows = conn.execute(query, params).fetchall()
conn.close()

if not rows:
    st.info("📭 Aucun livre trouvé.")
else:
    df = pd.DataFrame([dict(r) for r in rows])
    st.success(f"📚 {len(df)} livres trouvés")
    st.dataframe(df, width="stretch", height=600)
