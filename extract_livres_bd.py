import pandas as pd
from pathlib import Path

# ==============================
# CONFIG
# ==============================

INPUT_FILE = Path("Solde compte.xlsx")      # fichier source
OUTPUT_FILE = Path("Livres_BD_extrait.xlsx")  # fichier généré

SHEETS_TO_EXTRACT = {
    "Livres": "Livres",
    "BD": "BD"
}

# ==============================
# MAIN
# ==============================

def main():
    print("📘 Extraction des onglets Livres et BD")
    print(f"📂 Source : {INPUT_FILE}")
    print(f"📄 Destination : {OUTPUT_FILE}")
    print("-" * 40)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Fichier introuvable : {INPUT_FILE}")

    # Charger le fichier Excel
    xls = pd.ExcelFile(INPUT_FILE)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        for sheet_name, new_name in SHEETS_TO_EXTRACT.items():
            if sheet_name not in xls.sheet_names:
                print(f"⚠️ Onglet absent : {sheet_name}")
                continue

            print(f"✅ Extraction onglet : {sheet_name}")
            df = pd.read_excel(xls, sheet_name=sheet_name)

            # Écrire dans le nouveau fichier
            df.to_excel(writer, sheet_name=new_name, index=False)

    print("-" * 40)
    print("🎉 Fichier créé avec succès !")

if __name__ == "__main__":
    main()
