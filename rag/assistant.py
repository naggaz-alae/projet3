"""L'assistant : assemble recherche, génération, garde-fous et mesures.

    garde-fou d'entrée -> recherche hybride -> (seuil de pertinence) -> LLM
    -> vérification des citations -> garde-fou de sortie -> réponse + métriques
"""

from concurrent.futures import ThreadPoolExecutor

from ingestion.catalogue import Contrat
from rag import config
from rag.citations import verifier_citations
from rag.generator import Generateur
from rag.guardrails import AVERTISSEMENT_GENERAL, controler_sortie, verifier_question
from rag.monitoring import Chrono, calculer_cout
from rag.schemas import Metriques, Reponse, Verdict


class ContratInconnu(ValueError):
    pass


class Assistant:
    def __init__(self, retriever, generateur: Generateur, contrats: list[Contrat], journal=None,
                 top_k: int = config.TOP_K, seuil_similarite: float = config.SEUIL_SIMILARITE,
                 prix_entree: float = config.PRIX_ENTREE_PAR_MILLION,
                 prix_sortie: float = config.PRIX_SORTIE_PAR_MILLION):
        self.retriever = retriever
        self.generateur = generateur
        self.contrats = {c.id: c for c in contrats}
        self.journal = journal
        self.top_k = top_k
        self.seuil_similarite = seuil_similarite
        self.prix = (prix_entree, prix_sortie)

    @classmethod
    def depuis_config(cls) -> "Assistant":
        """Construit l'assistant « de production » (Mistral + PostgreSQL)."""
        from ingestion import config as ingestion_config
        from ingestion.catalogue import charger_catalogue
        from rag.mistral_client import MistralClient
        from rag.monitoring import JournalRequetes
        from rag.retriever import Retriever

        client = MistralClient()
        return cls(
            retriever=Retriever(config.DATABASE_URL, client),
            generateur=Generateur(client),
            contrats=charger_catalogue(ingestion_config.CATALOGUE_PATH),
            journal=JournalRequetes(config.DATABASE_URL),
        )

    def repondre(self, question: str, contrat_id: str, type_requete: str = "ask") -> Reponse:
        contrat = self.contrats.get(contrat_id)
        if contrat is None:
            raise ContratInconnu(f"Contrat inconnu : {contrat_id}")

        with Chrono() as chrono:
            champs, mesures = self._traiter(question, contrat)

        reponse = Reponse(question=question, contrat_id=contrat.id, assureur=contrat.assureur,
                          produit=contrat.produit, metriques=Metriques(latence_ms=chrono.ms, **mesures),
                          **champs)
        if self.journal is not None:
            self.journal.enregistrer(type_requete, reponse)
        return reponse

    def _traiter(self, question: str, contrat: Contrat) -> tuple[dict, dict]:
        """Renvoie (champs de la réponse, mesures de coût)."""
        # 1. Garde-fou d'entrée : aucun appel payant pour une question refusée
        motif = verifier_question(question)
        if motif:
            return {"verdict": Verdict.HORS_SUJET, "resume": motif}, {"appel_llm": False}

        # 2. Recherche des passages pertinents dans CE contrat
        passages = self.retriever.rechercher(question, [contrat.id], self.top_k)
        consultes = [p.chunk_id for p in passages]
        meilleure = max((p.similarite for p in passages if p.similarite is not None), default=None)
        if not passages or (meilleure is not None and meilleure < self.seuil_similarite):
            # Rien d'assez proche : inutile (et coûteux) d'interroger le LLM
            return {
                "verdict": Verdict.INFORMATION_ABSENTE,
                "resume": "Aucun passage de ce contrat ne semble traiter de cette situation.",
                "passages_consultes": consultes,
                "avertissements": [AVERTISSEMENT_GENERAL],
            }, {"appel_llm": False}

        # 3. Génération
        gen = self.generateur.generer(question, passages)
        # 4. Vérification des citations
        citations, invalides = verifier_citations(gen.reponse.citations, passages)
        # 5. Garde-fou de sortie
        verdict, avertissements = controler_sortie(gen.reponse.verdict, len(citations))
        if invalides:
            avertissements.append(f"{invalides} citation(s) introuvable(s) dans le contrat écartée(s).")
        if verdict in (Verdict.HORS_SUJET, Verdict.INFORMATION_ABSENTE):
            citations = []

        return {
            "verdict": verdict,
            "resume": gen.reponse.resume,
            "conditions": [] if verdict == Verdict.HORS_SUJET else gen.reponse.conditions,
            "citations": citations,
            "avertissements": avertissements + [AVERTISSEMENT_GENERAL],
            "passages_consultes": consultes,
        }, {
            "tokens_entree": gen.tokens_entree,
            "tokens_sortie": gen.tokens_sortie,
            "cout": calculer_cout(gen.tokens_entree, gen.tokens_sortie, *self.prix),
            "citations_invalides": invalides,
        }

    def comparer(self, question: str, contrat_ids: list[str]) -> list[Reponse]:
        """Même question sur plusieurs contrats, traitée en parallèle (appels réseau)."""
        for cid in contrat_ids:
            if cid not in self.contrats:
                raise ContratInconnu(f"Contrat inconnu : {cid}")
        with ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(lambda cid: self.repondre(question, cid, "compare"), contrat_ids))
