"""Mesure et journalisation : latence, tokens, coût de chaque requête."""

import logging
import time

import psycopg

logger = logging.getLogger(__name__)


def calculer_cout(tokens_entree: int, tokens_sortie: int, prix_entree: float, prix_sortie: float) -> float:
    """Coût d'un appel, avec des prix exprimés par million de tokens."""
    return (tokens_entree * prix_entree + tokens_sortie * prix_sortie) / 1_000_000


class Chrono:
    """with Chrono() as c: ...  puis c.ms"""

    def __enter__(self):
        self._debut = time.perf_counter()
        self.ms = 0
        return self

    def __exit__(self, *exc):
        self.ms = int((time.perf_counter() - self._debut) * 1000)
        return False


SQL_INSERT = """
    INSERT INTO requetes (type_requete, contrat_id, question, verdict, latence_ms,
                          tokens_entree, tokens_sortie, cout, appel_llm)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

SQL_RESUME = """
    SELECT count(*),
           percentile_cont(0.5)  WITHIN GROUP (ORDER BY latence_ms),
           percentile_cont(0.95) WITHIN GROUP (ORDER BY latence_ms),
           coalesce(sum(cout), 0), coalesce(avg(cout), 0),
           count(*) FILTER (WHERE NOT appel_llm)
    FROM requetes
"""


class JournalRequetes:
    """Enregistre chaque réponse dans la table `requetes`.
    Une panne du journal ne doit JAMAIS empêcher de répondre : les erreurs sont loguées."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def enregistrer(self, type_requete: str, reponse) -> None:
        m = reponse.metriques
        try:
            with psycopg.connect(self.database_url) as conn:
                conn.execute(SQL_INSERT, (type_requete, reponse.contrat_id, reponse.question,
                                          reponse.verdict.value, m.latence_ms, m.tokens_entree,
                                          m.tokens_sortie, m.cout, m.appel_llm))
        except psycopg.Error as err:
            logger.warning("Journalisation impossible : %s", err)

    def statistiques(self) -> dict:
        with psycopg.connect(self.database_url) as conn:
            total, p50, p95, cout_total, cout_moyen, sans_llm = conn.execute(SQL_RESUME).fetchone()
            verdicts = conn.execute(
                "SELECT verdict, count(*) FROM requetes GROUP BY verdict ORDER BY 2 DESC").fetchall()
            dernieres = conn.execute("""
                SELECT horodatage, type_requete, contrat_id, question, verdict, latence_ms, cout
                FROM requetes ORDER BY id DESC LIMIT 20""").fetchall()
        return {
            "nb_requetes": total,
            "latence_p50_ms": round(p50 or 0),
            "latence_p95_ms": round(p95 or 0),
            "cout_total": float(cout_total),
            "cout_moyen": float(cout_moyen),
            "nb_sans_appel_llm": sans_llm,
            "repartition_verdicts": {v: n for v, n in verdicts},
            "dernieres_requetes": [
                {"horodatage": h.isoformat(), "type": t, "contrat_id": c, "question": q,
                 "verdict": v, "latence_ms": l, "cout": float(co or 0)}
                for h, t, c, q, v, l, co in dernieres
            ],
        }
