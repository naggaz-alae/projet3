"""Appel au LLM et validation de sa réponse.

Si le JSON renvoyé ne respecte pas le format (champ manquant, verdict inconnu…),
on renvoie l'erreur au modèle et on lui laisse UNE seconde chance.
"""

from dataclasses import dataclass

from pydantic import ValidationError

from rag.mistral_client import LLMError
from rag.prompts import construire_messages
from rag.retriever import Passage
from rag.schemas import ReponseLLM


class GenerationError(LLMError):
    pass


@dataclass
class ResultatGeneration:
    reponse: ReponseLLM
    tokens_entree: int
    tokens_sortie: int


class Generateur:
    def __init__(self, llm, tentatives: int = 2):
        self.llm = llm
        self.tentatives = tentatives

    def generer(self, question: str, passages: list[Passage]) -> ResultatGeneration:
        messages = construire_messages(question, passages)
        tokens_entree = tokens_sortie = 0
        derniere_erreur = ""
        for _ in range(self.tentatives):
            brut = self.llm.chat_json(messages)
            tokens_entree += brut.tokens_entree
            tokens_sortie += brut.tokens_sortie
            try:
                reponse = ReponseLLM.model_validate_json(brut.contenu)
                return ResultatGeneration(reponse, tokens_entree, tokens_sortie)
            except ValidationError as err:
                derniere_erreur = str(err)
                messages = messages + [
                    {"role": "assistant", "content": brut.contenu},
                    {"role": "user", "content": "Ta réponse ne respecte pas le format demandé : "
                                                f"{derniere_erreur[:500]}\nRéponds uniquement avec le JSON demandé."},
                ]
        raise GenerationError(f"Réponse du LLM invalide après {self.tentatives} tentatives : {derniere_erreur[:300]}")
