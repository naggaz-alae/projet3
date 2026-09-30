"""Tests de la fusion des classements (RRF) : logique pure, sans base de données."""

from rag.retriever import Passage, fusion_rrf, fusionner, vecteur_sql


def passage(cid: str, similarite=None) -> Passage:
    return Passage(cid, "c", "A", "s", 1, 1, "texte", similarite=similarite)


def test_rrf_favorise_les_elements_bien_classes_dans_les_deux_listes():
    sens = ["degats_eaux", "resp_civile", "catnat"]
    mots = ["franchises", "degats_eaux", "resp_civile"]
    classement = [cid for cid, _ in fusion_rrf([sens, mots])]
    assert classement[0] == "degats_eaux"          # 1er + 2e
    assert classement[1] == "resp_civile"          # 2e + 3e
    assert set(classement) == {"degats_eaux", "resp_civile", "catnat", "franchises"}


def test_rrf_scores_decroissants():
    scores = [s for _, s in fusion_rrf([["a", "b", "c"], ["c", "b"]])]
    assert scores == sorted(scores, reverse=True)


def test_fusionner_garde_k_passages_et_la_similarite():
    sens = [passage("a", 0.9), passage("b", 0.8)]
    mots = [passage("b"), passage("c")]
    resultat = fusionner(sens, mots, k=2)
    assert [p.chunk_id for p in resultat] == ["b", "a"]
    assert resultat[0].similarite == 0.8   # la similarité cosinus est conservée


def test_format_vecteur_pgvector():
    assert vecteur_sql([0.5, -1.0]) == "[0.5000000,-1.0000000]"
