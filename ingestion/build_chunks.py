"""PDF -> passages découpés (data/chunks/<contrat>.jsonl) + statistiques de contrôle.

Lancement :
  python -m ingestion.build_chunks                       # tous les contrats
  python -m ingestion.build_chunks --apercu macif_habitation   # affiche 5 passages
"""

import argparse
import json
import logging

from ingestion import config
from ingestion.catalogue import charger_catalogue
from ingestion.chunking import PREAMBULE, Chunk, decouper
from ingestion.parse_pdf import extraire_pages

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("build_chunks")


def statistiques(nb_pages: int, chunks: list[Chunk]) -> dict:
    tailles = [len(c.texte) for c in chunks]
    hors_section = sum(len(c.texte) for c in chunks if c.section == PREAMBULE)
    return {
        "pages": nb_pages,
        "passages": len(chunks),
        "sections": len({c.section for c in chunks}),
        "taille_moyenne": round(sum(tailles) / len(tailles)) if tailles else 0,
        "taille_max": max(tailles, default=0),
        # Si ce pourcentage est élevé, les titres de ce contrat sont mal détectés
        "pct_hors_section": round(100 * hors_section / max(sum(tailles), 1), 1),
    }


def run(apercu: str | None = None) -> None:
    config.CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n{'contrat':<24}{'pages':>6}{'passages':>9}{'sections':>9}{'moy.':>6}{'max':>6}{'% hors sect.':>13}")
    for contrat in charger_catalogue(config.CATALOGUE_PATH):
        pdf = config.CONTRATS_DIR / f"{contrat.id}.pdf"
        if not pdf.exists():
            logger.warning("%s : PDF absent, lancer d'abord `python -m ingestion.download`", contrat.id)
            continue

        pages = extraire_pages(pdf)
        chunks = decouper(pages, contrat.id)
        sortie = config.CHUNKS_DIR / f"{contrat.id}.jsonl"
        with sortie.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")

        s = statistiques(len(pages), chunks)
        print(f"{contrat.id:<24}{s['pages']:>6}{s['passages']:>9}{s['sections']:>9}"
              f"{s['taille_moyenne']:>6}{s['taille_max']:>6}{s['pct_hors_section']:>12}%")

        if apercu == contrat.id:
            for chunk in chunks[:5]:
                print(f"\n--- {chunk.chunk_id} | p.{chunk.page_debut}-{chunk.page_fin} | {chunk.section}")
                print(chunk.texte[:400])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apercu", metavar="CONTRAT_ID", help="affiche les 5 premiers passages")
    run(apercu=parser.parse_args().apercu)
