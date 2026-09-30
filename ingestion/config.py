"""Chemins du projet (surchargeables via le fichier .env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
CATALOGUE_PATH = DATA_DIR / "catalogue.yaml"
CONTRATS_DIR = DATA_DIR / "contrats"      # PDF téléchargés
MANIFEST_PATH = CONTRATS_DIR / "manifest.json"
CHUNKS_DIR = DATA_DIR / "chunks"          # passages découpés (JSONL)
