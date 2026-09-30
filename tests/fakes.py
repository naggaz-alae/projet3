"""Doublures de test : un faux LLM et un faux moteur de recherche, sans réseau ni base."""

import json

from ingestion.catalogue import Contrat
from rag.mistral_client import ReponseChat
from rag.retriever import Passage

CONTRATS = [
    Contrat(id="assureur_a", assureur="Assureur A", produit="Habitation", url="https://exemple.fr/a.pdf"),
    Contrat(id="assureur_b", assureur="Assureur B", produit="Habitation", url="https://exemple.fr/b.pdf"),
]

PASSAGE_DEGATS = Passage(
    chunk_id="assureur_a-0012", contrat_id="assureur_a", assureur="Assureur A",
    section="5 - Garanties > 5.3 Dégâts des eaux", page_debut=14, page_fin=15,
    texte="Nous garantissons les dommages causés par les fuites et débordements d'eau "
          "provenant des conduites non enterrées.\nUne franchise de 150 euros s'applique.",
    score=0.03, similarite=0.82,
)
PASSAGE_EXCLUSIONS = Passage(
    chunk_id="assureur_a-0013", contrat_id="assureur_a", assureur="Assureur A",
    section="5 - Garanties > 5.3 Dégâts des eaux > Exclusions", page_debut=15, page_fin=15,
    texte="Sont exclus les dommages dus à un défaut d'entretien manifeste.",
    score=0.02, similarite=0.74,
)


def json_llm(verdict="couvert", citations=None, resume="Vous êtes couvert.", conditions=None) -> str:
    return json.dumps({
        "verdict": verdict,
        "resume": resume,
        "conditions": conditions or [],
        "citations": citations if citations is not None else [
            {"chunk_id": "assureur_a-0012",
             "extrait": "Nous garantissons les dommages causés par les fuites et débordements d'eau"}
        ],
    })


class FakeLLM:
    def __init__(self, reponses: list[str]):
        self.reponses = list(reponses)
        self.appels: list[list[dict]] = []

    def chat_json(self, messages, temperature=0.0) -> ReponseChat:
        self.appels.append(messages)
        return ReponseChat(contenu=self.reponses.pop(0), tokens_entree=1000, tokens_sortie=200)


class FakeRetriever:
    def __init__(self, passages: list[Passage]):
        self.passages = passages
        self.appels: list[tuple] = []

    def rechercher(self, question, contrat_ids, k, mode="hybride"):
        self.appels.append((question, tuple(contrat_ids), k))
        return [p for p in self.passages if p.contrat_id in contrat_ids][:k]


class FakeJournal:
    def __init__(self):
        self.lignes = []

    def enregistrer(self, type_requete, reponse):
        self.lignes.append((type_requete, reponse))
