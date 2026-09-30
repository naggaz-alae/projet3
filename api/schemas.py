"""Formats des requêtes et réponses de l'API (affichés automatiquement dans Swagger)."""

from pydantic import BaseModel, Field

from rag.schemas import Reponse


class QuestionIn(BaseModel):
    question: str = Field(min_length=8, max_length=1000,
                          examples=["Une fuite chez moi a abîmé le plafond du voisin du dessous, suis-je couvert ?"])
    contrat_id: str = Field(examples=["macif_habitation"])


class ComparaisonIn(BaseModel):
    question: str = Field(min_length=8, max_length=1000,
                          examples=["Mon vélo a été volé dans le local commun de l'immeuble, suis-je couvert ?"])
    contrat_ids: list[str] = Field(min_length=2, max_length=6,
                                   examples=[["maif_habitation", "macif_habitation", "maaf_tempo_habitation"]])


class ComparaisonOut(BaseModel):
    question: str
    reponses: list[Reponse]


class ContratOut(BaseModel):
    id: str
    assureur: str
    produit: str
    version: str | None = None
    url: str
