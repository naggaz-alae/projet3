"""Calcul des vecteurs (embeddings) des passages, avec cache disque.

Le cache évite de payer deux fois le même calcul : un passage dont le texte
n'a pas changé réutilise son vecteur au prochain lancement.
"""

import hashlib
import json
from pathlib import Path

from ingestion.catalogue import Contrat


def texte_a_vectoriser(chunk: dict, contrat: Contrat) -> str:
    """On vectorise le passage AVEC son contexte : sans le titre de section,
    « sont exclus : les infiltrations… » ne dit pas de quelle garantie il s'agit."""
    return f"{contrat.assureur} — {contrat.produit}\n{chunk['section']}\n\n{chunk['texte']}"


def empreinte(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


class CacheEmbeddings:
    def __init__(self, chemin: Path):
        self.chemin = chemin
        self.donnees: dict[str, list[float]] = (
            json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else {}
        )

    def sauvegarder(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.chemin.write_text(json.dumps(self.donnees), encoding="utf-8")


def vectoriser(textes: list[str], client, cache: CacheEmbeddings) -> list[list[float]]:
    """Renvoie un vecteur par texte ; seuls les textes absents du cache sont envoyés à l'API."""
    cles = [empreinte(t) for t in textes]
    a_calculer = [(cle, t) for cle, t in zip(cles, textes) if cle not in cache.donnees]
    if a_calculer:
        nouveaux = client.embed([t for _, t in a_calculer])
        for (cle, _), vecteur in zip(a_calculer, nouveaux):
            cache.donnees[cle] = vecteur
        cache.sauvegarder()
    return [cache.donnees[cle] for cle in cles]
