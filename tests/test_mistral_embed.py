"""Tests du client Mistral (réseau simulé) et du cache d'embeddings."""

from unittest.mock import MagicMock, patch

import pytest

from ingestion.catalogue import Contrat
from ingestion.embed import CacheEmbeddings, texte_a_vectoriser, vectoriser
from rag.mistral_client import LLMError, MistralClient
from rag.monitoring import calculer_cout


def reponse_http(status: int, payload: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload or {}
    r.text = "erreur"
    return r


def test_cle_absente_refusee():
    with pytest.raises(LLMError):
        MistralClient(api_key="")


@patch("rag.mistral_client.requests.post")
def test_embed_par_lots_et_dans_l_ordre(mock_post):
    def fausse_api(url, json, headers, timeout):
        # renvoyé dans le désordre : le client doit retrier par index
        data = [{"index": i, "embedding": [float(len(t))]} for i, t in enumerate(json["input"])]
        return reponse_http(200, {"data": list(reversed(data))})
    mock_post.side_effect = fausse_api

    vecteurs = MistralClient(api_key="test").embed(["a", "bb", "ccc"], taille_lot=2)
    assert vecteurs == [[1.0], [2.0], [3.0]]
    assert mock_post.call_count == 2


@patch("rag.mistral_client.time.sleep")
@patch("rag.mistral_client.requests.post")
def test_reessaie_sur_429_puis_reussit(mock_post, _sleep):
    ok = reponse_http(200, {"choices": [{"message": {"content": "{}"}}],
                            "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
    mock_post.side_effect = [reponse_http(429), ok]
    r = MistralClient(api_key="test").chat_json([{"role": "user", "content": "x"}])
    assert (r.contenu, r.tokens_entree, r.tokens_sortie) == ("{}", 10, 5)


@patch("rag.mistral_client.requests.post")
def test_erreur_401_non_reessayee(mock_post):
    mock_post.return_value = reponse_http(401)
    with pytest.raises(LLMError):
        MistralClient(api_key="mauvaise").chat_json([])
    assert mock_post.call_count == 1


def test_texte_vectorise_contient_le_contexte():
    contrat = Contrat(id="a", assureur="MAIF", produit="Habitation", url="https://exemple.fr/a.pdf")
    texte = texte_a_vectoriser({"section": "5.3 Dégâts des eaux", "texte": "Sont exclus..."}, contrat)
    assert "MAIF" in texte and "5.3 Dégâts des eaux" in texte and "Sont exclus" in texte


def test_cache_evite_les_appels_repetes(tmp_path):
    client = MagicMock()
    client.embed.side_effect = lambda textes: [[float(len(t))] for t in textes]
    cache = CacheEmbeddings(tmp_path / "cache.json")

    assert vectoriser(["abc", "de"], client, cache) == [[3.0], [2.0]]
    assert vectoriser(["abc", "de", "f"], client, CacheEmbeddings(tmp_path / "cache.json")) == [[3.0], [2.0], [1.0]]
    assert client.embed.call_args_list[1].args[0] == ["f"]   # seul le nouveau texte est envoyé


def test_calcul_du_cout():
    assert calculer_cout(1_000_000, 500_000, prix_entree=0.1, prix_sortie=0.3) == pytest.approx(0.25)
