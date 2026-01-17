import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

# ==================================================
# CONFIG
# ==================================================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "books.sqlite"
SCHEMA_PATH = BASE_DIR / "schema.sql"
EXCEL_FILE = BASE_DIR / "Solde compte.xlsx"

SHEET_LIVRES = "Livres"
SHEET_BD = "BD"

st.set_page_config(
    page_title="Bibliothèque personnelle",
    layout="wide"
)

# ==================================================
# DB
# ==================================================

def connect():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(conn):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()

def count_books(conn):
    return conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]

# ==================================================
# IMPORT EXCEL (TON CODE, ADAPTÉ STREAMLIT)
# ==================================================

def norm(x):
    return str(x).strip().lower()

def s(x):
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x).strip()

def to_bool(v):
    return 1 if str(v).strip().lower() in ("1", "x", "oui", "true", "vrai") else 0

def find_header_row(raw_df, needle="titre", max_scan=60):
    for i in range(min(max_scan, len(raw_df))):
        row_vals = [norm(v) for v in raw_df.iloc[i].values]
        if any(needle in cell for cell in row_vals if cell):
            return i
    return None

def insert_book(cur, owner, author, title, publisher="", language="", fmt="Livre", read=0, kept=1):
    title = s(title)
    author = s(author)
    publisher = s(publisher)
    language = s(language)

    if not title:
        return 0

    cur.execute(
        """
        INSERT OR IGNORE INTO books
        (owner, author, title, publisher, language, format, read, kept_after_reading)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (owner, author, title, publisher, language, fmt, int(read), int(kept)),
    )
    return 1 if cur.rowcount > 0 else 0

def import_livres(cur):
    raw = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_LIVRES, header=None)
    header_row = find_header_row(raw, needle="titre")
    if header_row is None:
        return (0, 0)

    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_LIVRES, header=header_row)
    df.columns = [norm(c) for c in df.columns]

    # CAROLE
    c_author = next((c for c in df.columns if c == "auteur"), None)
    c_title  = next((c for c in df.columns if c == "titre"), None)
    c_lang   = next((c for c in df.columns if "lang" in c), None)
    c_read   = next((c for c in df.columns if c == "lu"), None)
    c_keep   = next((c for c in df.columns if "gard" in c), None)
    c_pub    = next((c for c in df.columns if "edition" in c or "éditeur" in c), None)

    carole_added = 0
    if c_title and c_author:
        for _, r in df.iterrows():
            carole_added += insert_book(
                cur,
                "CAROLE",
                r.get(c_author),
                r.get(c_title),
                publisher=r.get(c_pub),
                language=r.get(c_lang),
                fmt="Livre",
                read=to_bool(r.get(c_read)) if c_read else 0,
                kept=to_bool(r.get(c_keep)) if c_keep else 1,
            )

    # NILS
    n_author = next((c for c in df.columns if c.startswith("auteur") and c != "auteur"), None)
    n_title  = next((c for c in df.columns if c.startswith("titre") and c != "titre"), None)

    nils_added = 0
    if n_author and n_title:
        for _, r in df.iterrows():
            nils_added += insert_book(
                cur,
                "NILS",
                r.get(n_author),
                r.get(n_title),
                fmt="Livre",
            )

    return (nils_added, carole_added)

def import_bd(cur):
    raw = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_BD, header=None)
    header_row = find_header_row(raw, needle="titre")
    if header_row is None:
        return 0

    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_BD, header=header_row)
    df.columns = [norm(c) for c in df.columns]

    c_author = next((c for c in df.columns if "auteur" in c), None)
    c_title  = next((c for c in df.columns if "titre" in c), None)

    added = 0
    for _, r in df.iterrows():
        added += insert_book(
            cur,
            "NILS",
            r.get(c_author),
            r.get(c_title),
            fmt="BD",
        )
    return added

def auto_import_if_empty(conn):
    if count_books(conn) > 0:
        return

    if not EXCEL_FILE.exists():
        st.error(f"❌ Fichier Excel introuvable : {EXCEL_FILE}")
        return

    cur = conn.cursor()
    n_nils, n_carole = import_livres(cur)
    n_bd = import_bd(cur)
    conn.commit()

    st.success(
        f"📥 Import automatique effectué : "
        f"Livres NILS={n_nils} | CAROLE={n_carole} | BD={n_bd}"
    )

# ==================================================
# INIT AU DÉMARRAGE
# ==================================================

conn = connect()
init_db(conn)
auto_import_if_empty(conn)

# ==================================================
# UI
# ==================================================

st.title("📚 Bibliothèque personnelle")

col1, col2, col3 = st.columns(3)

with col1:
    search = st.text_input("🔍 Recherche (titre / auteur)")

with col2:
    owner = st.selectbox("Propriétaire", ["TOUS", "NILS", "CAROLE"])

with col3:
    format_ = st.selectbox("Type", ["TOUS", "Livre", "BD"])

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

rows = conn.execute(query, params).fetchall()

if not rows:
    st.warning("Aucun livre trouvé.")
else:
    df = pd.DataFrame([dict(r) for r in rows])
    st.success(f"{len(df)} livres trouvés")
    st.dataframe(df, use_container_width=True, height=600)
