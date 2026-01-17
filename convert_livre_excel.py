import pandas as pd
import math
from pathlib import Path

# =========================
# CONFIG
# =========================

INPUT_FILE = Path("livre.xlsx")          # ton fichier actuel
OUTPUT_FILE = Path("livre_clean.xlsx")   # fichier propre généré

# Colonnes par bloc (comme vu sur ta capture)
BLOCKS = {
    "CAROLE": {
        "start": 0,
        "columns": ["Auteur", "Titre", "Langue", "Lu", "Garde", "Edition"]
    },
    "NILS": {
        "start": 7,
        "columns": ["Auteur", "Titre", "Langue"]
    },
    "AXEL": {
        "start": 14,
        "columns": ["Auteur", "Titre", "Langue"]
    }
}

# =========================
# UTILS
# =========================

def to_bool(val):
    if val is True:
        return True
    if val is False:
        return False
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return False
    return str(val).strip().lower() in ("true", "1", "yes", "x")

def clean(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    return str(val).strip()

# =========================
# MAIN
# =========================

def main():
    print("📘 Conversion du fichier Excel en format propre")
    print(f"📂 Source : {INPUT_FILE}")
    print(f"📄 Sortie : {OUTPUT_FILE}")
    print("-" * 50)

    df = pd.read_excel(INPUT_FILE, header=0)

    rows = []

    for owner, cfg in BLOCKS.items():
        start = cfg["start"]
        cols = cfg["columns"]
        end = start + len(cols)

        if df.shape[1] < end:
            print(f"⚠️ {owner} ignoré (colonnes insuffisantes)")
            continue

        sub = df.iloc[:, start:end].copy()
        sub.columns = cols

        for _, r in sub.iterrows():
            titre = clean(r.get("Titre"))
            if not titre:
                continue

            rows.append({
                "owner": owner,
                "type": "Livre",
                "auteur": clean(r.get("Auteur")),
                "titre": titre,
                "langue": clean(r.get("Langue")),
                "lu": to_bool(r.get("Lu")),
                "garde": to_bool(r.get("Garde")),
                "edition": clean(r.get("Edition"))
            })

    clean_df = pd.DataFrame(rows)

    clean_df.to_excel(
        OUTPUT_FILE,
        index=False,
        sheet_name="bibliotheque"
    )

    print(f"✅ Terminé : {len(clean_df)} livres exportés")
    print("🎉 Tu peux maintenant importer ce fichier sans AUCUNE bidouille")

if __name__ == "__main__":
    main()