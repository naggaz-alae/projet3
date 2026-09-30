"""Lecture et validation du catalogue des contrats (data/catalogue.yaml)."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, HttpUrl


class Contrat(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$", description="Identifiant unique, sert de nom de fichier")
    assureur: str
    produit: str
    version: str | None = None
    url: HttpUrl


class CatalogueInvalide(ValueError):
    pass


def charger_catalogue(chemin: Path) -> list[Contrat]:
    """Charge le catalogue et vérifie chaque entrée (Pydantic lève une erreur claire si un champ manque)."""
    contenu = yaml.safe_load(Path(chemin).read_text(encoding="utf-8")) or {}
    contrats = [Contrat(**entree) for entree in contenu.get("contrats", [])]

    ids = [c.id for c in contrats]
    doublons = {i for i in ids if ids.count(i) > 1}
    if doublons:
        raise CatalogueInvalide(f"Identifiants en double dans le catalogue : {sorted(doublons)}")
    if not contrats:
        raise CatalogueInvalide("Le catalogue ne contient aucun contrat")
    return contrats
