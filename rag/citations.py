"""Vérification des citations : le garde-fou principal contre les hallucinations.

Une citation est valide si :
1. son chunk_id fait partie des passages RÉELLEMENT fournis au LLM ;
2. son extrait se retrouve dans le texte de ce passage (au mot près, ou à 80 %
   des mots près pour tolérer une ponctuation ou une coupure de ligne différente).
"""

import re
import unicodedata

from rag.retriever import Passage
from rag.schemas import Citation, CitationLLM


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKC", texte).lower()
    texte = texte.replace("’", "'").replace("«", '"').replace("»", '"')
    return re.sub(r"\s+", " ", texte).strip()


def _mots(texte: str) -> list[str]:
    return [m for m in re.findall(r"\w+", normaliser(texte)) if len(m) >= 3]


def extrait_present(extrait: str, texte: str, seuil: float = 0.8) -> bool:
    extrait_n, texte_n = normaliser(extrait).strip(' ".…'), normaliser(texte)
    if len(extrait_n) < 10:
        return False  # trop court pour prouver quoi que ce soit
    if extrait_n in texte_n:
        return True
    mots_extrait = _mots(extrait)
    mots_texte = set(_mots(texte))
    if not mots_extrait:
        return False
    return sum(m in mots_texte for m in mots_extrait) / len(mots_extrait) >= seuil


def verifier_citations(citations: list[CitationLLM], passages: list[Passage]) -> tuple[list[Citation], int]:
    """Renvoie (citations valides enrichies de la section et des pages, nombre de citations écartées)."""
    par_id = {p.chunk_id: p for p in passages}
    valides: list[Citation] = []
    invalides = 0
    for c in citations:
        passage = par_id.get(c.chunk_id)
        if passage is None or not extrait_present(c.extrait, passage.texte):
            invalides += 1
            continue
        valides.append(Citation(chunk_id=c.chunk_id, extrait=c.extrait, section=passage.section,
                                page_debut=passage.page_debut, page_fin=passage.page_fin))
    return valides, invalides
