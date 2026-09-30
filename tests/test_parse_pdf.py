"""Tests de l'extraction PDF sur un faux contrat généré avec reportlab."""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ingestion.parse_pdf import Page, extraire_pages, nettoyer_pages


def creer_pdf(chemin, pages_texte: list[list[str]]) -> None:
    pdf = canvas.Canvas(str(chemin), pagesize=A4)
    for numero, lignes in enumerate(pages_texte, start=1):
        y = 800
        pdf.drawString(50, y, "Assureur Fictif - Conditions générales")  # en-tête répété
        for ligne in lignes:
            y -= 20
            pdf.drawString(50, y, ligne)
        pdf.drawString(50, 40, f"Page {numero} / {len(pages_texte)}")    # pied de page
        pdf.showPage()
    pdf.save()


def test_extraction_garde_les_pages_et_retire_en_tetes(tmp_path):
    chemin = tmp_path / "contrat.pdf"
    creer_pdf(chemin, [
        ["1 - Objet du contrat", "Le contrat couvre votre logement."],
        ["2 - Dégâts des eaux", "Les fuites sont garanties."],
        ["3 - Vol", "Le vol est garanti après effraction."],
    ])
    pages = extraire_pages(chemin)

    assert [p.numero for p in pages] == [1, 2, 3]
    assert "Les fuites sont garanties." in pages[1].texte
    assert all("Assureur Fictif" not in p.texte for p in pages)
    assert all("Page" not in p.texte for p in pages)


def test_mots_coupes_en_fin_de_ligne_recolles():
    pages = nettoyer_pages([Page(1, "la garan-\ntie dégâts des eaux")])
    assert pages[0].texte == "la garantie dégâts des eaux"
