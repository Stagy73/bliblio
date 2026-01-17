import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import requests
import io

# ==============================
# CONFIG
# ==============================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "books.sqlite"

st.set_page_config(
    page_title="📚 Ma Bibliothèque",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
            owner TEXT NOT NULL,
            format TEXT,
            author TEXT NOT NULL,
            title TEXT NOT NULL,
            language TEXT,
            isbn TEXT,
            publisher TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==============================
# API - Recherche par ISBN/EAN
# ==============================
def search_book_by_isbn(isbn):
    """Recherche un livre par ISBN via Google Books API"""
    try:
        isbn_clean = isbn.replace("-", "").replace(" ", "").strip()
        
        # Google Books API
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_clean}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("totalItems", 0) > 0:
                book = data["items"][0]["volumeInfo"]
                return {
                    "title": book.get("title", ""),
                    "authors": ", ".join(book.get("authors", [])),
                    "publisher": book.get("publisher", ""),
                    "language": book.get("language", "").upper()[:2],
                    "isbn": isbn_clean
                }
        
        # OpenLibrary fallback
        url2 = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn_clean}&format=json&jscmd=data"
        response2 = requests.get(url2, timeout=5)
        
        if response2.status_code == 200:
            data2 = response2.json()
            key = f"ISBN:{isbn_clean}"
            if key in data2:
                book2 = data2[key]
                return {
                    "title": book2.get("title", ""),
                    "authors": ", ".join([a.get("name", "") for a in book2.get("authors", [])]),
                    "publisher": ", ".join([p.get("name", "") for p in book2.get("publishers", [])]),
                    "language": "",
                    "isbn": isbn_clean
                }
        
        return None
        
    except Exception as e:
        st.error(f"Erreur lors de la recherche : {e}")
        return None

# ==============================
# SIDEBAR - STATS
# ==============================
with st.sidebar:
    st.markdown("### 📊 Statistiques")
    
    try:
        conn = get_conn()
        total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        by_owner = conn.execute("""
            SELECT owner, COUNT(*) as count 
            FROM books 
            GROUP BY owner 
            ORDER BY count DESC
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
    
    st.markdown("### ⚙️ Actions")
    if st.button("🔄 Réinitialiser la base"):
        if st.session_state.get('confirm_reset'):
            if DB_PATH.exists():
                DB_PATH.unlink()
            init_db()
            st.session_state.confirm_reset = False
            st.success("✅ Base réinitialisée")
            st.rerun()
        else:
            st.session_state.confirm_reset = True
            st.warning("⚠️ Cliquez encore pour confirmer")

# ==============================
# MAIN
# ==============================
st.title("📚 Ma Bibliothèque")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 Import CSV", "➕ Ajout manuel", "📱 Scanner EAN", "🔍 Recherche", "📊 Liste"])

# ==============================
# TAB 1 - IMPORT CSV
# ==============================
with tab1:
    st.markdown("## 📥 Importer depuis un fichier CSV")
    
    st.info("""
    **Format du CSV attendu :**
    - Colonnes : `Proprio`, `Format`, `Auteur`, `Titre`, `Langue`, `Editeur`
    - Séparateur : virgule (`,`)
    - Encodage : UTF-8
    """)
    
    # Télécharger le template
    st.markdown("### 📥 Télécharger un modèle CSV")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        template_csv = """Proprio,Format,Auteur,Titre,Langue,Editeur
Nils,Livre,Victor Hugo,Les Misérables,Fr,Gallimard
Axel,BD,Hergé,Tintin au Tibet,Fr,Casterman
Carole,Livre,Jane Austen,Pride and Prejudice,Eng,Penguin"""
        
        st.download_button(
            label="📥 Modèle complet (avec Format)",
            data=template_csv.encode('utf-8'),
            file_name="template_bibliotheque.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_t2:
        template_simple = """Proprio,Auteur,Titre,Langue
Axel,Hergé,Tintin au Tibet,Fr
Carole,Uderzo & Goscinny,Astérix en Corse,Fr
Nils,Peyo,Les Schtroumpfs,Fr"""
        
        st.download_button(
            label="📥 Modèle simple (sans Format)",
            data=template_simple.encode('utf-8'),
            file_name="template_simple.csv",
            mime="text/csv",
            use_container_width=True,
            help="Utilisez l'option 'Forcer le format' lors de l'import"
        )
    
    st.divider()
    
    # Upload du fichier
    uploaded_csv = st.file_uploader("Choisissez votre fichier CSV", type=["csv"])
    
    if uploaded_csv:
        try:
            # Lire le CSV
            df = pd.read_csv(uploaded_csv)
            
            # Afficher aperçu
            st.markdown("### 📊 Aperçu des données")
            st.dataframe(df.head(20), use_container_width=True)
            st.info(f"📐 {len(df)} lignes détectées")
            
            # Vérifier les colonnes
            required_cols = ["Proprio", "Auteur", "Titre"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Colonnes manquantes : {', '.join(missing_cols)}")
                st.write("Colonnes détectées :", list(df.columns))
            else:
                st.success("✅ Toutes les colonnes obligatoires sont présentes")
                
                # Options d'import
                col1, col2, col3 = st.columns(3)
                with col1:
                    wipe_before = st.checkbox("🗑️ Vider la base avant l'import")
                with col2:
                    skip_duplicates = st.checkbox("⏭️ Ignorer les doublons", value=True)
                with col3:
                    force_format = st.selectbox("📚 Forcer le format", ["Utiliser le CSV", "Livre", "BD", "Manga", "Comics"])
                
                # Bouton d'import
                if st.button("🚀 Importer les données", type="primary", use_container_width=True):
                    with st.spinner("Import en cours..."):
                        conn = get_conn()
                        cur = conn.cursor()
                        
                        if wipe_before:
                            cur.execute("DELETE FROM books")
                            conn.commit()
                            st.info("🗑️ Base vidée")
                        
                        inserted = 0
                        skipped = 0
                        errors = []
                        
                        for idx, row in df.iterrows():
                            try:
                                # Extraire les valeurs
                                owner = str(row.get("Proprio", "")).strip()
                                
                                # Utiliser le format forcé ou celui du CSV
                                if force_format == "Utiliser le CSV":
                                    format_type = str(row.get("Format", "Livre")).strip()
                                else:
                                    format_type = force_format
                                
                                author = str(row.get("Auteur", "")).strip()
                                title = str(row.get("Titre", "")).strip()
                                language = str(row.get("Langue", "")).strip()
                                publisher = str(row.get("Editeur", "")).strip()
                                isbn = str(row.get("ISBN", "")).strip() if "ISBN" in df.columns else ""
                                
                                # Validation
                                if not owner or owner == "nan":
                                    skipped += 1
                                    errors.append(f"Ligne {idx+2}: Propriétaire vide")
                                    continue
                                if not author or author == "nan":
                                    skipped += 1
                                    errors.append(f"Ligne {idx+2}: Auteur vide")
                                    continue
                                if not title or title == "nan":
                                    skipped += 1
                                    errors.append(f"Ligne {idx+2}: Titre vide")
                                    continue
                                
                                # Vérifier les doublons si demandé
                                if skip_duplicates:
                                    exists = cur.execute("""
                                        SELECT COUNT(*) FROM books 
                                        WHERE owner = ? AND author = ? AND title = ?
                                    """, (owner, author, title)).fetchone()[0]
                                    
                                    if exists > 0:
                                        skipped += 1
                                        continue
                                
                                # Insertion
                                cur.execute("""
                                    INSERT INTO books (owner, format, author, title, language, isbn, publisher)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    owner,
                                    format_type if format_type != "nan" else "Livre",
                                    author,
                                    title,
                                    language if language != "nan" else "",
                                    isbn if isbn != "nan" else None,
                                    publisher if publisher != "nan" else None
                                ))
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
                        
                        if errors:
                            with st.expander(f"📋 Détails des erreurs ({len(errors)})"):
                                for err in errors[:50]:
                                    st.text(err)
                        
                        st.rerun()
        
        except Exception as e:
            st.error(f"❌ Erreur lors de la lecture du fichier : {e}")
            st.info("💡 Assurez-vous que le fichier est au format CSV UTF-8")

# ==============================
# TAB 2 - AJOUT MANUEL
# ==============================
with tab2:
    st.markdown("## ✍️ Ajouter un livre manuellement")
    
    with st.form("add_book_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            owner = st.selectbox("Propriétaire *", ["Axel", "Carole", "Nils"], key="manual_owner")
            title = st.text_input("Titre *", key="manual_title")
            author = st.text_input("Auteur *", key="manual_author")
        
        with col2:
            format_type = st.selectbox("Format", ["Livre", "BD", "Manga", "Comics"], key="manual_format")
            language = st.selectbox("Langue", ["Fr", "Eng", "Esp", "Deu", "Autre"], key="manual_lang")
            publisher = st.text_input("Éditeur (optionnel)", key="manual_publisher")
        
        isbn = st.text_input("ISBN/EAN (optionnel)", key="manual_isbn")
        
        submitted = st.form_submit_button("➕ Ajouter le livre", type="primary", use_container_width=True)
        
        if submitted:
            if not title or not author:
                st.error("❌ Le titre et l'auteur sont obligatoires !")
            else:
                try:
                    conn = get_conn()
                    conn.execute("""
                        INSERT INTO books (owner, format, author, title, language, isbn, publisher)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (owner, format_type, author, title, language, isbn or None, publisher or None))
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ Livre ajouté : {title} par {author}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

# ==============================
# TAB 3 - SCANNER EAN
# ==============================
with tab3:
    st.markdown("## 📱 Scanner un code-barres EAN/ISBN")
    
    with st.expander("ℹ️ Comment scanner avec ton téléphone ?", expanded=True):
        st.markdown("""
        ### 📱 Pourquoi pas de scan direct dans l'app ?
        
        **Streamlit ne peut pas accéder directement à ta caméra** pour des raisons de sécurité du navigateur.
        Il faudrait du JavaScript complexe et ce n'est pas natif dans Streamlit.
        
        ### ✅ Solution simple et rapide :
        
        1. **Ouvre Google Lens** sur ton téléphone (ou l'appareil photo iPhone)
        2. **Scanne le code-barres** du livre
        3. **Copie le code EAN** (les 13 chiffres)
        4. **Colle-le dans le champ ci-dessous** 👇
        5. Clique sur "Rechercher"
        
        ### 📲 Applications recommandées :
        - **Google Lens** (Android/iOS) - Gratuit et très bien
        - **Appareil photo iPhone** (natif, scan automatique)
        - **Barcode Scanner** (Android)
        
        **C'est ultra-rapide** : scan → copie → colle → recherche → ajout ! ⚡
        """)
    
    # Interface de saisie
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ean_input = st.text_input(
            "Code EAN / ISBN",
            placeholder="Exemple: 9782070612758",
            key="ean_input",
            help="Scannez le code avec Google Lens puis collez-le ici"
        )
    
    with col2:
        search_button = st.button("🔍 Rechercher", type="primary", use_container_width=True)
    
    # Si un code a été saisi
    if ean_input and search_button:
        with st.spinner("🔍 Recherche en cours..."):
            book_info = search_book_by_isbn(ean_input)
            
            if book_info:
                st.success("✅ Livre trouvé !")
                
                st.markdown("### 📖 Informations détectées")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.text_input("Titre", value=book_info["title"], key="found_title", disabled=True)
                    st.text_input("Auteur", value=book_info["authors"], key="found_author", disabled=True)
                with col_b:
                    st.text_input("Éditeur", value=book_info["publisher"], key="found_pub", disabled=True)
                    st.text_input("Langue", value=book_info["language"], key="found_lang", disabled=True)
                
                # Formulaire pour ajouter
                with st.form("add_scanned_book"):
                    st.markdown("### ➕ Ajouter à ma bibliothèque")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        owner_scan = st.selectbox("Propriétaire", ["Axel", "Carole", "Nils"], key="scan_owner")
                    with col2:
                        format_scan = st.selectbox("Format", ["Livre", "BD", "Manga", "Comics"], key="scan_format")
                    with col3:
                        lang_scan = st.text_input("Langue", value=book_info["language"], key="scan_lang")
                    
                    add_scan = st.form_submit_button("➕ Ajouter ce livre", type="primary", use_container_width=True)
                    
                    if add_scan:
                        try:
                            conn = get_conn()
                            conn.execute("""
                                INSERT INTO books (owner, format, author, title, language, isbn, publisher)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                owner_scan,
                                format_scan,
                                book_info["authors"],
                                book_info["title"],
                                lang_scan,
                                book_info["isbn"],
                                book_info["publisher"]
                            ))
                            conn.commit()
                            conn.close()
                            
                            st.success(f"✅ Livre ajouté : {book_info['title']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur : {e}")
            else:
                st.warning("⚠️ Livre non trouvé dans les bases de données")
                st.info("💡 Vous pouvez l'ajouter manuellement dans l'onglet 'Ajout manuel'")

# ==============================
# TAB 4 - RECHERCHE
# ==============================
with tab4:
    st.markdown("## 🔍 Rechercher dans la bibliothèque")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        search_text = st.text_input("🔎 Recherche", placeholder="Titre ou auteur...")
    with c2:
        filter_owner = st.selectbox("Propriétaire", ["TOUS", "Axel", "Carole", "Nils"])
    with c3:
        filter_format = st.selectbox("Format", ["TOUS", "Livre", "BD", "Manga", "Comics"])
    
    try:
        conn = get_conn()
        
        query = "SELECT owner, format, author, title, language, publisher FROM books WHERE 1=1"
        params = []
        
        if search_text:
            query += " AND (title LIKE ? OR author LIKE ?)"
            params += [f"%{search_text}%", f"%{search_text}%"]
        
        if filter_owner != "TOUS":
            query += " AND owner = ?"
            params.append(filter_owner)
        
        if filter_format != "TOUS":
            query += " AND format = ?"
            params.append(filter_format)
        
        query += " ORDER BY owner, author, title"
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        if rows:
            df = pd.DataFrame(rows, columns=["Proprio", "Format", "Auteur", "Titre", "Langue", "Éditeur"])
            st.success(f"📚 {len(df)} résultat(s)")
            st.dataframe(df, use_container_width=True, height=500, hide_index=True)
        else:
            st.info("📭 Aucun résultat")
            
    except Exception as e:
        st.error(f"❌ Erreur : {e}")

# ==============================
# TAB 5 - LISTE COMPLÈTE
# ==============================
with tab5:
    st.markdown("## 📊 Liste complète")
    
    try:
        conn = get_conn()
        rows = conn.execute("""
            SELECT owner, format, author, title, language, publisher, created_at
            FROM books
            ORDER BY created_at DESC
        """).fetchall()
        conn.close()
        
        if rows:
            df = pd.DataFrame(rows, columns=[
                "Proprio", "Format", "Auteur", "Titre", "Langue", "Éditeur", "Ajouté le"
            ])
            
            st.success(f"📚 {len(df)} livre(s) dans la bibliothèque")
            
            # Export CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Télécharger en CSV",
                data=csv,
                file_name="ma_bibliotheque.csv",
                mime="text/csv"
            )
            
            st.dataframe(df, use_container_width=True, height=600, hide_index=True)
        else:
            st.info("📭 La bibliothèque est vide")
            
    except Exception as e:
        st.error(f"❌ Erreur : {e}")