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
            type TEXT,
            author TEXT,
            title TEXT,
            language TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==============================
# UTILS
# ==============================
def clean(v):
    """Nettoie une valeur Excel"""
    if pd.isna(v):
        return ""
    return str(v).replace("\n", " ").strip()

def normalize_columns(df):
    """Normalise les noms de colonnes"""
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )
    return df

def find_col(df, keywords):
    """Trouve une colonne par mots-clés"""
    for c in df.columns:
        for k in keywords:
            if k.lower() in c.lower():
                return c
    return None

# ==============================
# IMPORT
# ==============================
st.title("📚 Bibliothèque personnelle")
st.markdown("## 📥 Import Excel")

uploaded = st.file_uploader("Fichier Excel", type=["xlsx", "xls"])

if uploaded:
    try:
        xls = pd.ExcelFile(uploaded)
        sheet = st.selectbox("Onglet", xls.sheet_names)
        type_ = st.selectbox("Type", ["Livre", "BD"])
        wipe = st.checkbox("🗑️ Vider la base avant import")

        if st.button("🚀 Importer"):
            with st.spinner("Import en cours..."):
                # Lire le fichier Excel
                df = pd.read_excel(xls, sheet_name=sheet)
                df = normalize_columns(df)

                # Afficher les colonnes pour debug
                with st.expander("🔍 Colonnes détectées"):
                    st.write(df.columns.tolist())
                    st.dataframe(df.head(3))

                # Trouver les colonnes
                col_owner = find_col(df, ["proprio", "owner", "propriétaire"])
                col_author = find_col(df, ["auteur", "author"])
                col_title = find_col(df, ["titre", "title"])
                col_lang = find_col(df, ["eng", "fr", "lang", "langue"])

                if not col_owner or not col_author or not col_title:
                    st.error("❌ Colonnes minimales requises : Proprio / Auteur / Titre")
                    st.write("Colonnes trouvées :", {
                        "Proprio": col_owner,
                        "Auteur": col_author,
                        "Titre": col_title,
                        "Langue": col_lang
                    })
                    st.stop()

                # Connexion DB
                conn = get_conn()
                cur = conn.cursor()

                if wipe:
                    cur.execute("DELETE FROM books")
                    conn.commit()
                    st.info("🗑️ Base vidée")

                inserted = 0
                skipped = 0

                # Insertion
                for idx, r in df.iterrows():
                    try:
                        owner = clean(r[col_owner])
                        author = clean(r[col_author])
                        title = clean(r[col_title])
                        lang = clean(r[col_lang]) if col_lang else ""

                        # Vérifier que les champs essentiels sont présents
                        if not owner or owner.lower() == "nan":
                            skipped += 1
                            continue
                        if not author or author.lower() == "nan":
                            skipped += 1
                            continue
                        if not title or title.lower() == "nan":
                            skipped += 1
                            continue

                        # Insertion
                        cur.execute("""
                            INSERT INTO books (owner, type, author, title, language)
                            VALUES (?, ?, ?, ?, ?)
                        """, (owner, type_, author, title, lang))
                        inserted += 1

                    except Exception as e:
                        st.error(f"Erreur ligne {idx}: {e}")
                        skipped += 1

                conn.commit()
                conn.close()
                
                # Résultats
                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"✅ {inserted} livres importés")
                with col2:
                    if skipped > 0:
                        st.warning(f"⚠️ {skipped} lignes ignorées")
                
                st.rerun()
                
    except Exception as e:
        st.error(f"❌ Erreur : {e}")
        import traceback
        with st.expander("Détails"):
            st.code(traceback.format_exc())

# ==============================
# RECHERCHE
# ==============================
st.divider()
st.markdown("## 🔍 Recherche")

c1, c2, c3 = st.columns(3)

with c1:
    search = st.text_input("Titre ou Auteur")

with c2:
    owner_f = st.selectbox("Propriétaire", ["TOUS", "Axel", "Carole", "Nils"])

with c3:
    type_f = st.selectbox("Type", ["TOUS", "Livre", "BD"])

# Construction de la requête
try:
    query = """
    SELECT owner, type, author, title, language
    FROM books
    WHERE 1=1
    """
    params = []

    if search:
        query += " AND (title LIKE ? OR author LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]

    if owner_f != "TOUS":
        query += " AND owner = ?"
        params.append(owner_f)

    if type_f != "TOUS":
        query += " AND type = ?"
        params.append(type_f)

    query += " ORDER BY owner, type, author, title"

    # Exécution
    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if rows:
        df_result = pd.DataFrame(rows, columns=[
            "Propriétaire", "Type", "Auteur", "Titre", "Langue"
        ])
        st.success(f"📚 {len(df_result)} résultat(s)")
        st.dataframe(df_result, use_container_width=True, height=650, hide_index=True)
    else:
        st.info("📭 Aucun résultat")
        
except Exception as e:
    st.error(f"❌ Erreur de recherche : {e}")
    import traceback
    with st.expander("Détails"):
        st.code(traceback.format_exc())