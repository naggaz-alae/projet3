"""Réglages du moteur RAG, lus depuis le fichier .env."""

import os

from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
MODELE_CHAT = os.getenv("MODELE_CHAT", "mistral-small-latest")
MODELE_EMBEDDING = os.getenv("MODELE_EMBEDDING", "mistral-embed")
DIMENSION_EMBEDDING = int(os.getenv("DIMENSION_EMBEDDING", "1024"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag:rag_password@localhost:5432/assurance")

TOP_K = int(os.getenv("TOP_K", "5"))
SEUIL_SIMILARITE = float(os.getenv("SEUIL_SIMILARITE", "0"))

PRIX_ENTREE_PAR_MILLION = float(os.getenv("PRIX_ENTREE_PAR_MILLION", "0.1"))
PRIX_SORTIE_PAR_MILLION = float(os.getenv("PRIX_SORTIE_PAR_MILLION", "0.3"))
