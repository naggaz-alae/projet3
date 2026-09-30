"""Tests du découpage : détection des titres, fil d'Ariane, pages, sections longues."""

from ingestion.chunking import PREAMBULE, decouper, niveau_titre
from ingestion.parse_pdf import Page


def test_titres_reconnus_dans_les_differents_formats():
    assert niveau_titre("Article 12 - Vol et vandalisme") == 4
    assert niveau_titre("TITRE II GARANTIES PROPOSÉES") == 1
    assert niveau_titre("Section I - GARANTIE DE RESPONSABILITÉ CIVILE") == 3
    assert niveau_titre("1 - Présentation des formules de garanties") == 4
    assert niveau_titre("2.1 Biens immobiliers assurés") == 5
    assert niveau_titre("5.14.2 Responsabilité civile vie privée") == 6
    assert niveau_titre("4. INCENDIE ET ÉVÉNEMENTS ASSIMILÉS") == 4


def test_lignes_de_texte_non_reconnues_comme_titres():
    assert niveau_titre("3 000 € de franchise par sinistre") is None
    assert niveau_titre("Article L. 113-2 du Code des assurances") is None
    assert niveau_titre("les dommages causés par l'eau, notamment :") is None
    assert niveau_titre("2 ans à compter de la date du sinistre") is None
    assert niveau_titre("A" * 150) is None


def test_fil_d_ariane_et_pages():
    pages = [
        Page(1, "Conditions générales\n5 - Vos garanties\nIntroduction des garanties"),
        Page(2, "5.1 Dégâts des eaux\nNous garantissons les dommages causés par l'eau."),
        Page(3, "Exclusions : les infiltrations par les murs.\n5.2 Vol\nLe vol est garanti après effraction."),
    ]
    chunks = decouper(pages, "test")
    sections = [c.section for c in chunks]

    assert sections[0] == PREAMBULE
    assert "5 - Vos garanties > 5.1 Dégâts des eaux" in sections
    assert "5 - Vos garanties > 5.2 Vol" in sections  # 5.1 remplacé par 5.2, 5 conservé

    degats = next(c for c in chunks if c.section.endswith("Dégâts des eaux"))
    # La section s'étend sur 2 pages et l'exclusion reste avec sa garantie
    assert (degats.page_debut, degats.page_fin) == (2, 3)
    assert "infiltrations" in degats.texte


def test_lignes_de_sommaire_ignorees():
    pages = [Page(1, "2.1 Biens assurés ........ 12\n2.1 Biens assurés\nLe mobilier est assuré.")]
    chunks = decouper(pages, "test")
    assert len(chunks) == 1
    assert chunks[0].section == "2.1 Biens assurés"


def test_section_longue_coupee_avec_le_meme_fil_d_ariane():
    lignes = "\n".join(f"Ligne de texte numéro {i} du contrat." for i in range(200))
    pages = [Page(1, "Article 3 - Incendie\n" + lignes)]
    chunks = decouper(pages, "test", taille_max=1000)
    assert len(chunks) > 1
    assert all(c.section == "Article 3 - Incendie" for c in chunks)
    assert all(len(c.texte) <= 1000 for c in chunks)
    assert len({c.chunk_id for c in chunks}) == len(chunks)  # identifiants uniques
