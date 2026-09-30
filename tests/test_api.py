"""Tests de l'API avec un assistant factice (aucun appel à Mistral ni à la base)."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app, get_assistant  # noqa: E402
from rag.assistant import Assistant  # noqa: E402
from rag.generator import Generateur  # noqa: E402
from tests.fakes import CONTRATS, PASSAGE_DEGATS, FakeLLM, FakeRetriever, json_llm  # noqa: E402


@pytest.fixture
def client():
    assistant = Assistant(FakeRetriever([PASSAGE_DEGATS]), Generateur(FakeLLM([json_llm()] * 5)), CONTRATS)
    app.dependency_overrides[get_assistant] = lambda: assistant
    # Sans « with », le démarrage (lifespan) n'est pas exécuté : pas de vraie connexion
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"statut": "ok"}


def test_liste_des_contrats(client):
    ids = [c["id"] for c in client.get("/contrats").json()]
    assert ids == ["assureur_a", "assureur_b"]


def test_ask(client):
    r = client.post("/ask", json={"question": "Une fuite a abîmé mon parquet, suis-je couvert ?",
                                  "contrat_id": "assureur_a"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["verdict"] == "couvert"
    assert corps["citations"][0]["page_debut"] == 14


def test_ask_contrat_inconnu(client):
    r = client.post("/ask", json={"question": "Une fuite a abîmé mon parquet, suis-je couvert ?",
                                  "contrat_id": "inconnu"})
    assert r.status_code == 404


def test_ask_question_trop_courte_rejetee_par_la_validation(client):
    assert client.post("/ask", json={"question": "eau", "contrat_id": "assureur_a"}).status_code == 422


def test_compare(client):
    r = client.post("/compare", json={"question": "Une fuite a abîmé mon parquet, suis-je couvert ?",
                                      "contrat_ids": ["assureur_a", "assureur_b"]})
    assert r.status_code == 200
    assert [x["contrat_id"] for x in r.json()["reponses"]] == ["assureur_a", "assureur_b"]
