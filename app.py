import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import requests
import json

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
            year INTEGER,
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
        # Nettoyer l'ISBN
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
                    "year": book.get("publishedDate", "")[:4] if book.get("publishedDate") else "",
                    "language": book.get("language", "").upper()[:2],
                    "isbn": isbn_clean
                }
        
        # Essayer OpenLibrary comme fallback
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
                    "year": book2.get("publish_date", "")[:4] if book2.get("publish_date") else "",
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

# Tabs pour différentes fonctionnalités
tab1, tab2, tab3, tab4 = st.tabs(["➕ Ajout manuel", "📱 Scanner EAN", "🔍 Recherche", "📊 Liste complète"])

# ==============================
# TAB 1 - AJOUT MANUEL
# ==============================
with tab1:
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
        
        col3, col4 = st.columns(2)
        with col3:
            year = st.number_input("Année (optionnel)", 1900, 2030, 2024, key="manual_year")
        with col4:
            isbn = st.text_input("ISBN/EAN (optionnel)", key="manual_isbn")
        
        submitted = st.form_submit_button("➕ Ajouter le livre", type="primary", use_container_width=True)
        
        if submitted:
            if not title or not author:
                st.error("❌ Le titre et l'auteur sont obligatoires !")
            else:
                try:
                    conn = get_conn()
                    conn.execute("""
                        INSERT INTO books (owner, format, author, title, language, isbn, publisher, year)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (owner, format_type, author, title, language, isbn or None, publisher or None, year if year > 1900 else None))
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ Livre ajouté : {title} par {author}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

# ==============================
# TAB 2 - SCANNER EAN
# ==============================
with tab2:
    st.markdown("## 📱 Scanner un code-barres EAN/ISBN")
    
    st.info("💡 **Instructions :** Saisissez le code-barres manuellement ou scannez-le avec votre téléphone")
    
    # Interface de saisie
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ean_input = st.text_input(
            "Code EAN / ISBN",
            placeholder="Exemple: 9782070612758",
            key="ean_input",
            help="Scannez le code-barres avec votre téléphone ou tapez-le"
        )
    
    with col2:
        search_button = st.button("🔍 Rechercher", type="primary", use_container_width=True)
    
    # Affichage du HTML pour la caméra (optionnel, sur mobile)
    with st.expander("📷 Scanner avec la caméra (mobile)", expanded=False):
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <p>Pour scanner avec votre téléphone :</p>
            <ol style="text-align: left;">
                <li>Utilisez une application de scan de code-barres</li>
                <li>Scannez le code EAN/ISBN du livre</li>
                <li>Copiez le code et collez-le dans le champ ci-dessus</li>
            </ol>
            <p><strong>Ou utilisez ces applications :</strong></p>
            <ul style="text-align: left;">
                <li>Google Lens (Android/iOS)</li>
                <li>Appareil photo iPhone (natif)</li>
                <li>Barcode Scanner (Android)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Si un code a été saisi
    if ean_input and search_button:
        with st.spinner("🔍 Recherche en cours..."):
            book_info = search_book_by_isbn(ean_input)
            
            if book_info:
                st.success("✅ Livre trouvé !")
                
                # Afficher les informations
                st.markdown("### 📖 Informations détectées")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.text_input("Titre", value=book_info["title"], key="found_title", disabled=True)
                    st.text_input("Auteur", value=book_info["authors"], key="found_author", disabled=True)
                with col_b:
                    st.text_input("Éditeur", value=book_info["publisher"], key="found_pub", disabled=True)
                    st.text_input("Année", value=book_info["year"], key="found_year", disabled=True)
                
                # Formulaire pour ajouter à la base
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
                                INSERT INTO books (owner, format, author, title, language, isbn, publisher, year)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                owner_scan,
                                format_scan,
                                book_info["authors"],
                                book_info["title"],
                                lang_scan,
                                book_info["isbn"],
                                book_info["publisher"],
                                int(book_info["year"]) if book_info["year"].isdigit() else None
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
# TAB 3 - RECHERCHE
# ==============================
with tab3:
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
        
        query = "SELECT owner, format, author, title, language, year, publisher FROM books WHERE 1=1"
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
            df = pd.DataFrame(rows, columns=["Proprio", "Format", "Auteur", "Titre", "Langue", "Année", "Éditeur"])
            st.success(f"📚 {len(df)} résultat(s)")
            st.dataframe(df, use_container_width=True, height=500, hide_index=True)
        else:
            st.info("📭 Aucun résultat")
            
    except Exception as e:
        st.error(f"❌ Erreur : {e}")

# ==============================
# TAB 4 - LISTE COMPLÈTE
# ==============================
with tab4:
    st.markdown("## 📊 Liste complète")
    
    try:
        conn = get_conn()
        rows = conn.execute("""
            SELECT owner, format, author, title, language, year, publisher, created_at
            FROM books
            ORDER BY created_at DESC
        """).fetchall()
        conn.close()
        
        if rows:
            df = pd.DataFrame(rows, columns=[
                "Proprio", "Format", "Auteur", "Titre", "Langue", "Année", "Éditeur", "Ajouté le"
            ])
            
            st.success(f"📚 {len(df)} livre(s) dans la bibliothèque")
            
            # Option d'export
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