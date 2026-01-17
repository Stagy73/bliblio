import pandas as pd
from pathlib import Path

INPUT_FILE = Path("new.xls")
OUTPUT_FILE = INPUT_FILE.with_suffix(".xlsx")

# Lire tous les onglets
xls = pd.ExcelFile(INPUT_FILE)

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df.to_excel(writer, sheet_name=sheet, index=False)

print(f"✅ Conversion terminée : {OUTPUT_FILE}")
