"""Extraction du texte des PDF, page par page, puis nettoyage.

On garde le numéro de page de chaque ligne : c'est lui qui permettra de citer
« page 23 » dans les réponses.
"""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pdfplumber


@dataclass
class Page:
    numero: int
    texte: str


def extraire_pages(chemin_pdf: Path) -> list[Page]:
    """Lit le PDF et renvoie ses pages nettoyées."""
    pages = []
    with pdfplumber.open(chemin_pdf) as pdf:
        for numero, page in enumerate(pdf.pages, start=1):
            pages.append(Page(numero, page.extract_text() or ""))
    return nettoyer_pages(pages)


def _cle_ligne(ligne: str) -> str:
    """Forme normalisée d'une ligne : les chiffres sont neutralisés pour que
    « Page 3 / 40 » et « Page 4 / 40 » soient reconnues comme la même ligne."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", ligne)).strip().lower()


def detecter_lignes_repetees(pages: list[Page], seuil: float = 0.5) -> set[str]:
    """En-têtes et pieds de page : lignes présentes sur plus de `seuil` des pages."""
    if len(pages) < 3:
        return set()
    compteur: Counter[str] = Counter()
    for page in pages:
        compteur.update({_cle_ligne(l) for l in page.texte.splitlines() if l.strip()})
    return {cle for cle, nb in compteur.items() if nb / len(pages) > seuil}


def nettoyer_pages(pages: list[Page]) -> list[Page]:
    repetees = detecter_lignes_repetees(pages)
    propres = []
    for page in pages:
        lignes = [
            re.sub(r"[ \t]+", " ", ligne).strip()
            for ligne in page.texte.splitlines()
            if ligne.strip() and _cle_ligne(ligne) not in repetees
        ]
        texte = "\n".join(lignes)
        # Recoller les mots coupés en fin de ligne : « garan-\ntie » -> « garantie »
        texte = re.sub(r"([a-zà-ÿ])-\n([a-zà-ÿ])", r"\1\2", texte)
        propres.append(Page(page.numero, texte))
    return propres
