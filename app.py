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

def recreate_db():
    """Recrée complètement la base de données"""
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    conn = get_conn()
    conn.execute("""
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            format TEXT,
            author TEXT NOT NULL,
            title TEXT NOT NULL,
            language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def init_db():
    """Initialise la base de données"""
    conn = get_conn()
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='books'
    """)
    if not cursor.fetchone():
        conn.execute("""
            CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                format TEXT,
                author TEXT NOT NULL,
                title TEXT NOT NULL,
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    s = str(v).replace("\n", " ").strip()
    if s.lower() == "nan":
        return ""
    return s

def normalize_columns(df):
    """Normalise les noms de colonnes"""
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.replace("Unnamed:", "Col", regex=False)
        .str.strip()
    )
    return df

def find_col_index(df, keywords):
    """Trouve l'index d'une colonne par mots-clés"""
    for idx, c in enumerate(df.columns):
        col_str = str(c).lower()
        for k in keywords:
            if k.lower() in col_str:
                return idx
    return None

# ==============================
# SIDEBAR
# ==============================
with st.sidebar:
    st.markdown("### ⚙️ Administration")
    
    try:
        conn = get_conn()
        total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        by_owner = conn.execute("""
            SELECT owner, COUNT(*) as count 
            FROM books 
            GROUP BY owner 
            ORDER BY owner
        """).fetchall()
        conn.close()
        
        st.metric("📚 Total", total)
        
        if by_owner:
            st.markdown("**Par propriétaire:**")
            for owner, count in by_owner:
                st.text(f"{owner}: {count}")
    except:
        st.metric("📚 Total", 0)
    
    st.divider()
    
    if st.button("🔄 Réinitialiser la base"):
        if st.session_state.get('confirm_reset'):
            recreate_db()
            st.session_state.confirm_reset = False
            st.success("✅ Base réinitialisée")
            st.rerun()
        else:
            st.session_state.confirm_reset = True
            st.warning("⚠️ Cliquez à nouveau pour confirmer")
    
    if st.session_state.get('confirm_reset') and st.button("❌ Annuler"):
        st.session_state.confirm_reset = False
        st.rerun()

# ==============================
# IMPORT
# ==============================
st.title("📚 Bibliothèque personnelle")
st.markdown("## 📥 Import Excel")

uploaded = st.file_uploader("Fichier Excel", type=["xlsx", "xls"])

if uploaded:
    try:
        xls = pd.ExcelFile(uploaded)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            sheet = st.selectbox("Onglet", xls.sheet_names)
        with col2:
            format_ = st.selectbox("Format", ["Livre", "BD"])
        with col3:
            wipe = st.checkbox("🗑️ Vider avant import")
        
        # Options avancées
        with st.expander("⚙️ Options avancées"):
            skip_rows = st.number_input("Lignes à ignorer au début", 0, 10, 0)
            debug_mode = st.checkbox("🔍 Mode debug détaillé", value=True)
        
        # Charger et afficher les données brutes
        df_raw = pd.read_excel(xls, sheet_name=sheet, header=skip_rows)
        df = normalize_columns(df_raw)
        
        st.markdown("### 📊 Aperçu du fichier")
        st.dataframe(df.head(20), use_container_width=True, height=300)
        
        st.markdown("### 🔧 Détection des colonnes")
        
        # Détection manuelle ou automatique
        detection_mode = st.radio("Mode", ["Automatique", "Manuel"], horizontal=True)
        
        if detection_mode == "Automatique":
            # Détection automatique
            col_owner_idx = find_col_index(df, ["proprio", "owner", "propriétaire"])
            col_author_idx = find_col_index(df, ["auteur", "author"])
            col_title_idx = find_col_index(df, ["titre", "title"])
            col_lang_idx = find_col_index(df, ["eng", "fr", "lang", "langue"])
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.text(f"Proprio: Col {col_owner_idx}")
            with c2:
                st.text(f"Auteur: Col {col_author_idx}")
            with c3:
                st.text(f"Titre: Col {col_title_idx}")
            with c4:
                st.text(f"Langue: Col {col_lang_idx}")
        else:
            # Sélection manuelle
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                col_owner_idx = st.selectbox("Colonne Proprio", range(len(df.columns)), 
                                            format_func=lambda x: f"{x}: {df.columns[x]}")
            with c2:
                col_author_idx = st.selectbox("Colonne Auteur", range(len(df.columns)),
                                             format_func=lambda x: f"{x}: {df.columns[x]}")
            with c3:
                col_title_idx = st.selectbox("Colonne Titre", range(len(df.columns)),
                                            format_func=lambda x: f"{x}: {df.columns[x]}")
            with c4:
                col_lang_idx = st.selectbox("Colonne Langue", [-1] + list(range(len(df.columns))),
                                           format_func=lambda x: "Aucune" if x == -1 else f"{x}: {df.columns[x]}")
                if col_lang_idx == -1:
                    col_lang_idx = None

        if st.button("🚀 Importer", type="primary"):
            if col_owner_idx is None or col_author_idx is None or col_title_idx is None:
                st.error("❌ Veuillez sélectionner au minimum : Proprio, Auteur et Titre")
                st.stop()
            
            with st.spinner("Import en cours..."):
                conn = get_conn()
                cur = conn.cursor()

                if wipe:
                    cur.execute("DELETE FROM books")
                    conn.commit()
                    st.info("🗑️ Base vidée")

                inserted = 0
                skipped = 0
                errors = []

                # Utiliser les indices de colonnes
                for idx, row in df.iterrows():
                    try:
                        owner = clean(row.iloc[col_owner_idx])
                        author = clean(row.iloc[col_author_idx])
                        title = clean(row.iloc[col_title_idx])
                        lang = clean(row.iloc[col_lang_idx]) if col_lang_idx is not None else ""

                        # Validation
                        if not owner:
                            skipped += 1
                            if debug_mode:
                                errors.append(f"Ligne {idx+2}: Proprio vide")
                            continue
                        if not author:
                            skipped += 1
                            if debug_mode:
                                errors.append(f"Ligne {idx+2}: Auteur vide")
                            continue
                        if not title:
                            skipped += 1
                            if debug_mode:
                                errors.append(f"Ligne {idx+2}: Titre vide")
                            continue

                        # Insertion
                        cur.execute("""
                            INSERT INTO books (owner, format, author, title, language)
                            VALUES (?, ?, ?, ?, ?)
                        """, (owner, format_, author, title, lang))
                        inserted += 1

                    except Exception as e:
                        errors.append(f"Ligne {idx+2}: {str(e)}")
                        skipped += 1

                conn.commit()
                conn.close()
                
                # Résultats
                st.success(f"✅ {inserted} livres importés")
                if skipped > 0:
                    st.warning(f"⚠️ {skipped} lignes ignorées")
                
                if errors and debug_mode:
                    with st.expander(f"📋 Détails ({len(errors)} erreurs)"):
                        for err in errors[:50]:
                            st.text(err)
                
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
    format_f = st.selectbox("Format", ["TOUS", "Livre", "BD"])

try:
    conn = get_conn()
    
    query = """
    SELECT owner, format, author, title, language
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

    if format_f != "TOUS":
        query += " AND format = ?"
        params.append(format_f)

    query += " ORDER BY owner, format, author, title"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if rows:
        df_result = pd.DataFrame(rows, columns=[
            "Propriétaire", "Format", "Auteur", "Titre", "Langue"
        ])
        st.success(f"📚 {len(df_result)} résultat(s)")
        st.dataframe(df_result, use_container_width=True, height=500, hide_index=True)
    else:
        st.info("📭 Aucun résultat")
        
except Exception as e:
    st.error(f"❌ Erreur : {e}")