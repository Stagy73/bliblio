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

st.set_page_config(page_title="Bibliothèque personnelle", layout="wide")

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

def to_bool(v):
    return str(v).strip().lower() in ("true", "1", "x", "yes", "oui")

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
    xls = pd.ExcelFile(uploaded)
    sheet = st.selectbox("Choisir l’onglet à importer", xls.sheet_names)
    category = st.selectbox("Type de contenu", ["Livre", "BD"])
    wipe = st.checkbox("🗑️ Vider la base avant import")

    if st.button("🚀 Importer cet onglet"):
        df = pd.read_excel(xls, sheet_name=sheet)
        conn = get_conn()
        cur = conn.cursor()

        if wipe:
            cur.execute("DELETE FROM books")
            conn.commit()

        inserted = 0

        # ==============================
        # BD
        # ==============================
        if category == "BD":
            for _, r in df.iterrows():
                auteur = str(r.iloc[0]).strip()
                titre = str(r.iloc[1]).strip()
                if not auteur or not titre:
                    continue

                cur.execute("""
                    INSERT INTO books (owner, category, author, title)
                    VALUES (?, ?, ?, ?)
                """, ("BD", "BD", auteur, titre))
                inserted += 1

        # ==============================
        # LIVRES
        # ==============================
        else:
            blocks = {
                "CAROLE": (0, 6),
                "NILS":   (7, 10),
                "AXEL":   (11, 14)
            }

            for owner, (start, end) in blocks.items():
                sub = df.iloc[:, start:end].copy()

                if owner == "CAROLE":
                    sub.columns = ["Auteur", "Titre", "Langue", "Lu", "Garde", "Edition"]
                else:
                    sub.columns = ["Auteur", "Titre", "Langue"]

                for _, r in sub.iterrows():
                    titre = str(r["Titre"]).strip()
                    auteur = str(r["Auteur"]).strip()
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
                        r.get("Langue", ""),
                        to_bool(r.get("Lu", False)),
                        to_bool(r.get("Garde", False)),
                        r.get("Edition", "")
                    ))
                    inserted += 1

        conn.commit()
        conn.close()

        st.success(f"✅ Import terminé : {inserted} lignes importées")

st.divider()

# ==============================
# AFFICHAGE
# ==============================

conn = get_conn()
rows = conn.execute("""
    SELECT owner, category, author, title, language, read, kept, publisher
    FROM books
    ORDER BY owner, category, author
""").fetchall()
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
    st.info("📭 Base vide")
