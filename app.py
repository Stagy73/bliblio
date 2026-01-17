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
    return str(val).strip().upper() in ("TRUE", "1", "YES", "X", "OUI")

def safe_str(val):
    """Convertit en string de manière sûre"""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    return str(val).strip()

def detect_owner_blocks(df):
    """Détecte automatiquement les blocs de colonnes pour chaque propriétaire"""
    # Chercher les colonnes qui contiennent les noms des propriétaires
    owners = ["CAROLE", "NILS", "AXEL"]
    blocks = {}
    
    # Regarder la première ligne des noms de colonnes
    cols = [str(c).upper() for c in df.columns]
    
    for owner in owners:
        # Trouver l'indice de la colonne qui contient le nom du propriétaire
        for i, col in enumerate(cols):
            if owner in col:
                # Le bloc commence à cette colonne
                # On prend les 6 prochaines colonnes (Auteur, Titre, Langue, Lu, Garde, Edition)
                blocks[owner] = (i, i + 6)
                st.info(f"✓ {owner} détecté : colonnes {i} à {i+6}")
                break
    
    return blocks

# ==============================
# UI
# ==============================

st.title("📚 Bibliothèque personnelle")

st.markdown("## 📥 Importer la bibliothèque")

uploaded = st.file_uploader(
    "Importer le fichier Excel (livre.xlsx)",
    type=["xlsx", "xls"]
)

force = st.checkbox("🔁 Forcer la réimportation (vider la base avant)")
debug = st.checkbox("🔍 Mode debug (afficher la structure)")

if uploaded and st.button("🚀 Lancer l'import"):
    with st.spinner("Import en cours…"):
        try:
            conn = get_conn()
            cur = conn.cursor()

            if force:
                cur.execute("DELETE FROM books")
                conn.commit()
                st.info("🗑️ Base de données vidée")

            # Lire toutes les données
            df = pd.read_excel(uploaded, header=0)
            
            st.info(f"📊 Fichier chargé : {len(df.columns)} colonnes, {len(df)} lignes")
            
            if debug:
                # Afficher les premières colonnes pour debug
                with st.expander("🔍 Structure du fichier"):
                    st.write("**Colonnes détectées :**")
                    for i, col in enumerate(df.columns):
                        st.text(f"Col {i}: {col}")
                    st.write("**Premières lignes :**")
                    st.dataframe(df.head(5))
            
            # Détecter automatiquement les blocs ou utiliser la config manuelle
            try:
                blocks = detect_owner_blocks(df)
            except:
                st.warning("⚠️ Détection automatique échouée, utilisation de la configuration manuelle")
                # Configuration manuelle par défaut
                blocks = {
                    "CAROLE": (1, 7),
                    "NILS":   (8, 14),
                    "AXEL":   (15, 21)
                }

            if not blocks:
                st.error("❌ Impossible de détecter les propriétaires dans le fichier")
                st.stop()

            inserted = 0
            skipped = 0
            errors = []

            for owner, (start, end) in blocks.items():
                st.write(f"📖 Traitement des livres de {owner}...")
                
                try:
                    # Extraire les colonnes pour ce propriétaire
                    sub = df.iloc[:, start:end].copy()
                    
                    # Vérifier qu'on a au moins 6 colonnes
                    num_cols = sub.shape[1]
                    if num_cols < 6:
                        st.warning(f"⚠️ {owner} : nombre de colonnes insuffisant ({num_cols} < 6)")
                        continue
                    
                    # Renommer les colonnes
                    col_names = ["Auteur", "Titre", "Langue", "Lu", "Garde", "Edition"]
                    if num_cols > 6:
                        col_names += [f"Extra_{i}" for i in range(num_cols - 6)]
                    
                    sub.columns = col_names[:num_cols]

                    # Traiter chaque ligne
                    for idx, row in sub.iterrows():
                        try:
                            # Vérifier que la ligne contient des données valides
                            title = safe_str(row["Titre"])
                            author = safe_str(row["Auteur"])
                            
                            if not title or title.lower() in ("nan", ""):
                                skipped += 1
                                continue
                            
                            if not author or author.lower() in ("nan", ""):
                                skipped += 1
                                continue

                            # Préparer les valeurs
                            publisher = safe_str(row.get("Edition", ""))
                            language = safe_str(row.get("Langue", ""))
                            read = to_bool(row.get("Lu", False))
                            kept = to_bool(row.get("Garde", False))

                            # Insérer dans la base
                            cur.execute("""
                                INSERT OR IGNORE INTO books
                                (owner, author, title, publisher, language, format, read, kept)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                owner,
                                author,
                                title,
                                publisher,
                                language,
                                "Livre",
                                read,
                                kept
                            ))
                            
                            if cur.rowcount > 0:
                                inserted += 1
                            
                        except Exception as e:
                            errors.append(f"Ligne {idx+2} ({owner}): {str(e)}")

                except Exception as e:
                    errors.append(f"Bloc {owner}: {str(e)}")
                    st.error(f"❌ Erreur sur {owner}: {str(e)}")

            conn.commit()
            conn.close()

            # Afficher les résultats
            st.success(f"✅ Import terminé !")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Livres importés", inserted)
            with col2:
                st.metric("Lignes ignorées", skipped)
            with col3:
                st.metric("Erreurs", len(errors))

            if errors and debug:
                with st.expander(f"⚠️ Détails des erreurs ({len(errors)})"):
                    for err in errors[:50]:  # Afficher max 50 erreurs
                        st.text(err)
            
        except Exception as e:
            st.error(f"❌ Erreur globale : {str(e)}")
            import traceback
            with st.expander("📋 Détails de l'erreur"):
                st.code(traceback.format_exc())
    
    if inserted > 0:
        st.rerun()

st.divider()

# ==============================
# STATISTIQUES
# ==============================

conn = get_conn()
stats = conn.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN read = 1 THEN 1 ELSE 0 END) as read_count,
        SUM(CASE WHEN kept = 1 THEN 1 ELSE 0 END) as kept_count
    FROM books
""").fetchone()

if stats and stats["total"] > 0:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 Total", stats["total"])
    with col2:
        st.metric("✅ Lus", stats["read_count"])
    with col3:
        st.metric("⭐ Gardés", stats["kept_count"])

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
    format_ = st.selectbox("Type", ["TOUS", "Livre", "BD"])

# ==============================
# QUERY
# ==============================

query = """
SELECT owner, author, title, publisher, language, format, read, kept
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

rows = conn.execute(query, params).fetchall()
conn.close()

if not rows:
    st.info("📭 Aucun livre trouvé.")
else:
    df_result = pd.DataFrame([dict(r) for r in rows])
    
    # Convertir les booléens en texte plus lisible
    df_result["read"] = df_result["read"].apply(lambda x: "✓" if x else "")
    df_result["kept"] = df_result["kept"].apply(lambda x: "✓" if x else "")
    
    # Renommer les colonnes pour l'affichage
    df_result.columns = ["Propriétaire", "Auteur", "Titre", "Éditeur", "Langue", "Type", "Lu", "Gardé"]
    
    st.success(f"📚 {len(df_result)} livre(s) trouvé(s)")
    st.dataframe(
        df_result, 
        use_container_width=True, 
        height=600,
        hide_index=True
    )