#!/bin/bash
echo "=== Installation Book Catalog ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Installation terminée."
echo "Lancer avec: streamlit run app.py"
