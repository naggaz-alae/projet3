"""Chargement du jeu d'évaluation et calcul des indicateurs (fonctions pures, testées)."""

import math
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from rag.schemas import Verdict

QUESTIONS_PATH = Path("evaluation/questions.yaml")


class Attendu(BaseModel):
    verdict: Verdict | None = None
    section: str | None = None


class QuestionEval(BaseModel):
    id: str
    type: Literal["classique", "piege", "hors_sujet"]
    question: str
    attendus: dict[str, Attendu] = {}


def charger_questions(chemin: Path = QUESTIONS_PATH) -> list[QuestionEval]:
    donnees = yaml.safe_load(Path(chemin).read_text(encoding="utf-8"))
    questions = [QuestionEval(**q) for q in donnees["questions"]]
    ids = [q.id for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Identifiants de questions en double")
    return questions


def paires_annotees(questions: list[QuestionEval], contrat_ids: list[str],
                    tous_sur_un_seul: bool = True) -> list[tuple[QuestionEval, str, Attendu]]:
    """Développe les attendus en paires (question, contrat, attendu).
    La clé « tous » est appliquée au premier contrat seulement (tous_sur_un_seul),
    pour ne pas payer 4 fois le même test de refus."""
    paires = []
    for q in questions:
        for cle, attendu in q.attendus.items():
            if cle == "tous":
                cibles = contrat_ids[:1] if tous_sur_un_seul else contrat_ids
                paires.extend((q, cid, attendu) for cid in cibles)
            elif cle in contrat_ids:
                paires.append((q, cle, attendu))
    return paires


# ----------------------------- Indicateurs -----------------------------

def rang_section(sections: list[str], attendue: str) -> int | None:
    """Rang (à partir de 1) du premier passage dont la section contient `attendue`."""
    for rang, section in enumerate(sections, start=1):
        if attendue.lower() in section.lower():
            return rang
    return None


def taux_succes(rangs: list[int | None], k: int) -> float:
    """Part des questions dont le bon passage est dans les k premiers résultats."""
    return sum(r is not None and r <= k for r in rangs) / len(rangs) if rangs else 0.0


def mrr(rangs: list[int | None]) -> float:
    """Mean Reciprocal Rank : 1 si toujours 1er, 0,5 si toujours 2e, 0 si jamais trouvé."""
    return sum(1 / r for r in rangs if r) / len(rangs) if rangs else 0.0


def percentile(valeurs: list[float], p: float) -> float:
    """Percentile par interpolation linéaire (p entre 0 et 100)."""
    if not valeurs:
        return 0.0
    tri = sorted(valeurs)
    position = (len(tri) - 1) * p / 100
    bas, haut = math.floor(position), math.ceil(position)
    return tri[bas] + (tri[haut] - tri[bas]) * (position - bas)
