"""Charge les passages et leurs vecteurs dans PostgreSQL + pgvector.

Pour chaque contrat, tout se fait dans UNE transaction : on supprime ses anciens
passages et on insère les nouveaux. Relancer le script donne toujours le même état
(idempotence), et une erreur au milieu ne laisse jamais un contrat à moitié indexé.

Lancement :  python -m ingestion.index
"""

import json
import logging

import psycopg

from ingestion import config
from ingestion.catalogue import charger_catalogue
from ingestion.embed import CacheEmbeddings, texte_a_vectoriser, vectoriser
from rag import config as rag_config
from rag.mistral_client import MistralClient
from rag.retriever import vecteur_sql

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("index")

INSERT = """
    INSERT INTO passages (chunk_id, contrat_id, assureur, produit, section,
                          page_debut, page_fin, texte, embedding)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
"""


def lire_chunks(contrat_id: str) -> list[dict]:
    chemin = config.CHUNKS_DIR / f"{contrat_id}.jsonl"
    if not chemin.exists():
        return []
    return [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]


def run() -> None:
    client = MistralClient()
    cache = CacheEmbeddings(config.DATA_DIR / "embeddings_cache.json")

    with psycopg.connect(rag_config.DATABASE_URL) as conn:
        for contrat in charger_catalogue(config.CATALOGUE_PATH):
            chunks = lire_chunks(contrat.id)
            if not chunks:
                logger.warning("%s : aucun passage, lancer d'abord `python -m ingestion.build_chunks`", contrat.id)
                continue

            vecteurs = vectoriser([texte_a_vectoriser(c, contrat) for c in chunks], client, cache)
            with conn.transaction(), conn.cursor() as cur:
                cur.execute("DELETE FROM passages WHERE contrat_id = %s", (contrat.id,))
                cur.executemany(INSERT, [
                    (c["chunk_id"], contrat.id, contrat.assureur, contrat.produit, c["section"],
                     c["page_debut"], c["page_fin"], c["texte"], vecteur_sql(v))
                    for c, v in zip(chunks, vecteurs)
                ])
            logger.info("%s : %s passages indexés", contrat.id, len(chunks))


if __name__ == "__main__":
    run()
