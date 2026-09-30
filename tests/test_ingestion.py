"""Tests du catalogue et du téléchargement (réseau simulé)."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from ingestion.catalogue import CatalogueInvalide, charger_catalogue
from ingestion.download import TelechargementInvalide, telecharger_pdf


def test_le_catalogue_du_projet_est_valide():
    contrats = charger_catalogue("data/catalogue.yaml")
    assert len(contrats) >= 4
    assert all(str(c.url).endswith(".pdf") for c in contrats)


def test_catalogue_refuse_les_doublons(tmp_path):
    fichier = tmp_path / "catalogue.yaml"
    entree = "  - {id: a, assureur: X, produit: Y, url: 'https://exemple.fr/a.pdf'}\n"
    fichier.write_text("contrats:\n" + entree * 2, encoding="utf-8")
    with pytest.raises(CatalogueInvalide):
        charger_catalogue(fichier)


def test_catalogue_refuse_une_url_invalide(tmp_path):
    fichier = tmp_path / "catalogue.yaml"
    fichier.write_text("contrats:\n  - {id: a, assureur: X, produit: Y, url: pas-une-url}\n",
                       encoding="utf-8")
    with pytest.raises(ValidationError):
        charger_catalogue(fichier)


def fausse_reponse(contenu: bytes) -> MagicMock:
    reponse = MagicMock()
    reponse.content = contenu
    reponse.raise_for_status.return_value = None
    return reponse


@patch("ingestion.download.requests.get")
def test_telechargement_accepte_un_pdf(mock_get):
    mock_get.return_value = fausse_reponse(b"%PDF-1.7 contenu")
    assert telecharger_pdf("https://exemple.fr/cg.pdf").startswith(b"%PDF")


@patch("ingestion.download.requests.get")
def test_telechargement_refuse_une_page_html(mock_get):
    mock_get.return_value = fausse_reponse(b"<html>Page introuvable</html>")
    with pytest.raises(TelechargementInvalide):
        telecharger_pdf("https://exemple.fr/cg.pdf")
