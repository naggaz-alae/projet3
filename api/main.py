"""API REST de l'assistant. Documentation interactive : http://localhost:8000/docs

Lancement :  uvicorn api.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request

from api.schemas import ComparaisonIn, ComparaisonOut, ContratOut, QuestionIn
from rag.assistant import Assistant, ContratInconnu
from rag.mistral_client import LLMError
from rag.schemas import Reponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # L'assistant (clients Mistral, base, catalogue) est créé UNE fois au démarrage
    app.state.assistant = Assistant.depuis_config()
    yield


app = FastAPI(
    title="Suis-je couvert ? — API",
    version="1.0.0",
    description="Assistant RAG qui répond à « suis-je couvert ? » à partir des conditions générales "
                "d'assurance habitation, avec citations vérifiées. Réponses indicatives : "
                "seul le contrat fait foi.",
    lifespan=lifespan,
)


def get_assistant(request: Request) -> Assistant:
    return request.app.state.assistant


@app.get("/health", tags=["Supervision"])
def health() -> dict:
    return {"statut": "ok"}


@app.get("/contrats", response_model=list[ContratOut], tags=["Contrats"])
def lister_contrats(assistant: Assistant = Depends(get_assistant)):
    return [ContratOut(id=c.id, assureur=c.assureur, produit=c.produit, version=c.version, url=str(c.url))
            for c in assistant.contrats.values()]


@app.post("/ask", response_model=Reponse, tags=["Assistant"])
def poser_question(corps: QuestionIn, assistant: Assistant = Depends(get_assistant)):
    """Répond à une question sur UN contrat : verdict, conditions, citations vérifiées, coût."""
    try:
        return assistant.repondre(corps.question, corps.contrat_id)
    except ContratInconnu as err:
        raise HTTPException(status_code=404, detail=str(err))
    except LLMError as err:
        raise HTTPException(status_code=503, detail=f"Service IA indisponible : {err}")


@app.post("/compare", response_model=ComparaisonOut, tags=["Assistant"])
def comparer(corps: ComparaisonIn, assistant: Assistant = Depends(get_assistant)):
    """Pose la même question sur plusieurs contrats (2 à 6)."""
    try:
        return ComparaisonOut(question=corps.question, reponses=assistant.comparer(corps.question, corps.contrat_ids))
    except ContratInconnu as err:
        raise HTTPException(status_code=404, detail=str(err))
    except LLMError as err:
        raise HTTPException(status_code=503, detail=f"Service IA indisponible : {err}")


@app.get("/stats", tags=["Supervision"])
def statistiques(assistant: Assistant = Depends(get_assistant)) -> dict:
    """Volume, latence (médiane et 95e centile), coût, répartition des verdicts."""
    if assistant.journal is None:
        raise HTTPException(status_code=503, detail="Journal des requêtes non configuré")
    return assistant.journal.statistiques()
