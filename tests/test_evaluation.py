"""Tests du jeu d'évaluation et des indicateurs."""

import pytest

from evaluation.jeu import (Attendu, QuestionEval, charger_questions, mrr, paires_annotees, percentile,
                            rang_section, taux_succes)
from rag.schemas import Verdict


def test_le_jeu_contient_40_questions_bien_reparties():
    questions = charger_questions()
    types = [q.type for q in questions]
    assert len(questions) == 40
    assert (types.count("classique"), types.count("piege"), types.count("hors_sujet")) == (25, 10, 5)


def test_paires_annotees_developpe_la_cle_tous():
    questions = [
        QuestionEval(id="a", type="hors_sujet", question="?", attendus={"tous": Attendu(verdict=Verdict.HORS_SUJET)}),
        QuestionEval(id="b", type="classique", question="?", attendus={"c2": Attendu(verdict=Verdict.COUVERT)}),
        QuestionEval(id="c", type="classique", question="?", attendus={}),
    ]
    paires = paires_annotees(questions, ["c1", "c2"])
    assert [(q.id, cid) for q, cid, _ in paires] == [("a", "c1"), ("b", "c2")]
    assert len(paires_annotees(questions, ["c1", "c2"], tous_sur_un_seul=False)) == 3


def test_rang_section_insensible_a_la_casse():
    sections = ["2 - Incendie", "5 - Garanties > 5.3 DÉGÂTS DES EAUX", "5.3 Dégâts des eaux > Exclusions"]
    assert rang_section(sections, "dégâts des eaux") == 2
    assert rang_section(sections, "vol") is None


def test_indicateurs_de_recherche():
    rangs = [1, 2, None, 5]
    assert taux_succes(rangs, 1) == 0.25
    assert taux_succes(rangs, 5) == 0.75
    assert mrr(rangs) == pytest.approx((1 + 0.5 + 0 + 0.2) / 4)


def test_percentile():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert percentile([10], 95) == 10
    assert percentile([], 50) == 0.0
