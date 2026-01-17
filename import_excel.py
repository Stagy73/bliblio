import pandas as pd
import sqlite3
from pathlib import Path

# ==============================
# CONFIG
# ==============================
DB_PATH = Path("data") / "books.sqlite"
SCHEMA_FILE = "schema.sql"
EXCEL_FILE = "Solde compte.xlsx"

SHEET_LIVRES = "Livres"
SHEET_BD = "BD"

# ==============================
# DB
# ==============================
def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(conn):
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()

# ==============================
# UTILS
# ==============================
def norm(x):
    return str(x).strip().lower()

def s(x):
    """safe string"""
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

# ==============================
# IMPORT LIVRES (NILS + CAROLE)
# ==============================
def import_livres(cur):
    raw = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_LIVRES, header=None)
    header_row = find_header_row(raw, needle="titre")
    if header_row is None:
        print("⚠️ Onglet Livres: en-tête introuvable")
        return (0, 0)

    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_LIVRES, header=header_row)
    df.columns = [norm(c) for c in df.columns]

    # ----- CAROLE (bloc gauche) -----
    c_author = next((c for c in df.columns if c == "auteur"), None)
    c_title  = next((c for c in df.columns if c == "titre"), None)
    c_lang   = next((c for c in df.columns if "eng" in c or "fr" in c or "lang" in c), None)
    c_read   = next((c for c in df.columns if c == "lu"), None)
    c_keep   = next((c for c in df.columns if "gard" in c), None)
    c_pub    = next((c for c in df.columns if "edition" in c or "éditeur" in c or "editeur" in c), None)

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
    else:
        print("⚠️ Bloc CAROLE non détecté")

    # ----- NILS (bloc droit : auteur.1 / titre.1 etc.) -----
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
    else:
        print("⚠️ Bloc NILS non détecté")

    return (nils_added, carole_added)

# ==============================
# IMPORT BD (NILS)
# ==============================
def import_bd(cur):
    raw = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_BD, header=None)
    header_row = find_header_row(raw, needle="bd")
    if header_row is None:
        header_row = find_header_row(raw, needle="titre")

    if header_row is None:
        print("⚠️ Onglet BD: en-tête introuvable")
        return 0

    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_BD, header=header_row)
    df.columns = [norm(c) for c in df.columns]

    c_author = next((c for c in df.columns if "bd auteur" in c or c == "auteur"), None)
    c_title  = next((c for c in df.columns if "bd titre" in c or c == "titre"), None)

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

# ==============================
# MAIN
# ==============================
def main():
    if not Path(EXCEL_FILE).exists():
        raise FileNotFoundError(f"❌ Fichier introuvable : {EXCEL_FILE}")

    conn = connect()
    init_db(conn)
    cur = conn.cursor()

    print("📚 IMPORT EXCEL → SQLITE (MODE EXCEL RÉEL)")
    print(f"📄 {EXCEL_FILE}")
    print("----------------------------------------")

    nils_livres, carole_livres = import_livres(cur)
    print(f"✅ Livres importés: NILS={nils_livres} | CAROLE={carole_livres}")

    bd_nils = import_bd(cur)
    print(f"✅ BD importées (NILS): {bd_nils}")

    conn.commit()
    conn.close()

    print("----------------------------------------")
    print("🎉 Import terminé sans erreurs (doublons ignorés)")

if __name__ == "__main__":
    main()
