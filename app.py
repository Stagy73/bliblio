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

st.set_page_config(page_title="Bibliothèque personnelle", layout="wide")

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

def to_bool(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return 0
    return str(val).strip().lower() in ("true", "1", "yes", "x", "oui")

def safe(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    return str(val).strip()

# ==============================
# UI IMPORT
# ==============================

st.title("📚 Bibliothèque personnelle")
st.subheader("📥 Import du fichier Excel")

uploaded = st.file_uploader(
    "Uploader le fichier Solde compte.xls / xlsx",
    type=["xls", "xlsx"]
)

if uploaded:
    xls = pd.ExcelFile(uploaded)
    sheet = st.selectbox("Choisir l’onglet à importer", xls.sheet_names)

    category = st.selectbox("Type de contenu", ["Livre", "BD"])
    wipe = st.checkbox("🗑️ Vider la base avant import")

    if st.button("🚀 Importer cet onglet"):
        with st.spinner("Import en cours…"):
            df = pd.read_excel(uploaded, sheet_name=sheet)

            conn = get_conn()
            cur = conn.cursor()

            if wipe:
                cur.execute("DELETE FROM books")
                conn.commit()

            inserted = 0

            # ==========================
            # CAS BD (simple)
            # ==========================
            if category == "BD":
                for _, row in df.iterrows():
                    auteur = safe(row.get("BD Auteur") or row.get("Auteur"))
                    titre = safe(row.get("BD titre") or row.get("Titre"))

                    if not auteur or not titre:
                        continue

                    cur.execute("""
                        INSERT INTO books
                        (owner, category, author, title)
                        VALUES (?, ?, ?, ?)
                    """, ("BD", "BD", auteur, titre))

                    inserted += 1

            # ==========================
            # CAS LIVRES (CAROLE / NILS / AXEL)
            # ==========================
            else:
                BLOCKS = {
                    "CAROLE": 0,
                    "NILS": 7,
                    "AXEL": 14
                }

                for owner, start in BLOCKS.items():
                    sub = df.iloc[:, start:start+6]
                    sub.columns = [
                        "Auteur", "Titre", "Langue",
                        "Lu", "Garde", "Edition"
                    ]

                    for _, row in sub.iterrows():
                        titre = safe(row["Titre"])
                        auteur = safe(row["Auteur"])

                        if not titre or not auteur:
                            continue

                        cur.execute("""
                            INSERT INTO books
                            (owner, category, author, title, language, read, kept, publisher)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            owner,
                            "Livre",
                            auteur,
                            titre,
                            safe(row["Langue"]),
                            to_bool(row["Lu"]),
                            to_bool(row["Garde"]),
                            safe(row["Edition"])
                        ))
                        inserted += 1

            conn.commit()
            conn.close()

        st.success(f"✅ Import terminé : {inserted} entrées ajoutées")
        st.rerun()

st.divider()

# ==============================
# AFFICHAGE
# ==============================

st.subheader("🔍 Bibliothèque")

search = st.text_input("Recherche titre / auteur")
owner = st.selectbox("Propriétaire", ["TOUS", "CAROLE", "NILS", "AXEL", "BD"])
category = st.selectbox("Type", ["TOUS", "Livre", "BD"])

query = "SELECT owner, author, title, publisher, language, category, read, kept FROM books WHERE 1=1"
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

if not rows:
    st.info("📭 Aucun résultat")
else:
    df = pd.DataFrame(rows, columns=[
        "Propriétaire", "Auteur", "Titre",
        "Éditeur", "Langue", "Type",
        "Lu", "Gardé"
    ])
    df["Lu"] = df["Lu"].apply(lambda x: "✓" if x else "")
    df["Gardé"] = df["Gardé"].apply(lambda x: "✓" if x else "")
    st.dataframe(df, use_container_width=True, height=650)
