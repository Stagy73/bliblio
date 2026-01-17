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

st.set_page_config(page_title="📚 Bibliothèque personnelle", layout="wide")

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
        # BD  (onglet BD)
        # Colonnes attendues :
        # A = Auteur | B = Titre
        # ==============================
        if category == "BD":
            for _, r in df.iterrows():
                auteur = clean(r.iloc[0])
                titre = clean(r.iloc[1])

                if not auteur or not titre:
                    continue

                cur.execute("""
                    INSERT OR IGNORE INTO books
                    (owner, category, author, title)
                    VALUES (?, ?, ?, ?)
                """, ("BD", "BD", auteur, titre))

                inserted += cur.rowcount

        # ==============================
        # LIVRES (onglet Livres)
        # STRUCTURE EXACTE :
        # CAROLE : Auteur | Titre | Eng,Fr | Lu | Gardé | Edition
        # NILS   : Auteur | Titre | Eng,Fr
        # AXEL   : Auteur | Titre | Eng,Fr
        # ==============================
        else:
            blocks = {
                "CAROLE": (0, 6),
                "NILS":   (6, 9),
                "AXEL":   (9, 12)
            }

            for owner, (start, end) in blocks.items():
                sub = df.iloc[:, start:end].copy()

                if owner == "CAROLE":
                    sub.columns = ["Auteur", "Titre", "Langue", "Lu", "Garde", "Edition"]
                else:
                    sub.columns = ["Auteur", "Titre", "Langue"]

                for _, r in sub.iterrows():
                    auteur = clean(r["Auteur"])
                    titre = clean(r["Titre"])

                    if not auteur or not titre:
                        continue

                    cur.execute("""
                        INSERT OR IGNORE INTO books
                        (owner, category, author, title, language, read, kept, publisher)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        owner,
                        "Livre",
                        auteur,
                        titre,
                        clean(r.get("Langue", "")),
                        to_bool(r.get("Lu", False)),
                        to_bool(r.get("Garde", False)),
                        clean(r.get("Edition", ""))
                    ))

                    inserted += cur.rowcount

        conn.commit()
        conn.close()

        st.success(f"✅ Import terminé : {inserted} entrées ajoutées")

st.divider()

# ==============================
# AFFICHAGE
# ==============================
conn = get_conn()
rows = conn.execute("""
    SELECT owner, category, author, title, language, read, kept, publisher
    FROM books
    ORDER BY owner, category, author, title
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
