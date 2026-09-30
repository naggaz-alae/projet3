"""Formats de données du moteur : ce que le LLM doit produire, et ce que l'assistant renvoie."""

from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    COUVERT = "couvert"
    NON_COUVERT = "non_couvert"
    SOUS_CONDITIONS = "sous_conditions"
    INFORMATION_ABSENTE = "information_absente"
    HORS_SUJET = "hors_sujet"


VERDICTS_AFFIRMATIFS = {Verdict.COUVERT, Verdict.NON_COUVERT, Verdict.SOUS_CONDITIONS}


# ---- Format IMPOSÉ au LLM (validé à chaque réponse) ----

class CitationLLM(BaseModel):
    chunk_id: str = Field(description="Identifiant du passage cité, ex. macif_habitation-0042")
    extrait: str = Field(description="Phrase recopiée MOT POUR MOT depuis le passage")


class ReponseLLM(BaseModel):
    verdict: Verdict
    resume: str = Field(description="Réponse en 2 à 4 phrases, en français simple")
    conditions: list[str] = Field(default_factory=list, description="Franchises, plafonds, délais, exclusions")
    citations: list[CitationLLM] = Field(default_factory=list)


# ---- Ce que l'assistant renvoie à l'API et à l'interface ----

class Citation(BaseModel):
    chunk_id: str
    extrait: str
    section: str
    page_debut: int
    page_fin: int


class Metriques(BaseModel):
    latence_ms: int
    tokens_entree: int = 0
    tokens_sortie: int = 0
    cout: float = 0.0
    appel_llm: bool = True
    citations_invalides: int = 0


class Reponse(BaseModel):
    question: str
    contrat_id: str
    assureur: str
    produit: str
    verdict: Verdict
    resume: str
    conditions: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    avertissements: list[str] = Field(default_factory=list)
    passages_consultes: list[str] = Field(default_factory=list)
    metriques: Metriques
