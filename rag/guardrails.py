"""Garde-fous en entrée (avant le LLM) et en sortie (après)."""

import re

from rag.schemas import VERDICTS_AFFIRMATIFS, Verdict

AVERTISSEMENT_GENERAL = (
    "Réponse indicative générée par IA à partir des conditions générales. "
    "Seuls votre contrat (conditions particulières incluses) et votre assureur font foi."
)

LONGUEUR_MIN, LONGUEUR_MAX = 8, 1000

# Tentatives de détourner l'assistant de ses consignes (« prompt injection »)
MOTIFS_INJECTION = [
    r"ignore[rz]? (toutes |tes |les )?(pr[ée]c[ée]dentes )?(instructions|consignes|r[èe]gles)",
    r"oublie[rz]? (toutes |tes |les )?(instructions|consignes|r[èe]gles)",
    r"(prompt|message) syst[èe]me",
    r"system prompt",
    r"tu es (maintenant|désormais)",
]


def verifier_question(question: str) -> str | None:
    """Renvoie le motif de refus, ou None si la question peut être traitée."""
    q = question.strip()
    if len(q) < LONGUEUR_MIN:
        return "Question trop courte : décrivez votre situation."
    if len(q) > LONGUEUR_MAX:
        return f"Question trop longue (maximum {LONGUEUR_MAX} caractères)."
    if any(re.search(motif, q, re.IGNORECASE) for motif in MOTIFS_INJECTION):
        return "Question refusée : elle tente de modifier les consignes de l'assistant."
    return None


def controler_sortie(verdict: Verdict, nb_citations_valides: int) -> tuple[Verdict, list[str]]:
    """Un verdict affirmatif sans aucune citation valide n'est pas étayé par le contrat :
    on le remplace par « information absente » plutôt que de risquer une erreur."""
    if verdict in VERDICTS_AFFIRMATIFS and nb_citations_valides == 0:
        return Verdict.INFORMATION_ABSENTE, [
            "Verdict non étayé par une citation vérifiable du contrat : remplacé par « information absente »."
        ]
    return verdict, []
