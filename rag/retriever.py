"""Recherche des passages pertinents : par le sens, par mots-clés, ou hybride.

- Sens (vecteurs pgvector) : trouve « dégât des eaux » quand on écrit « fuite ».
- Mots-clés (plein texte PostgreSQL en français) : excelle sur les termes exacts
  (« franchise », « vétusté », « catastrophe naturelle »).
- Hybride : fusion des deux classements par Reciprocal Rank Fusion (RRF).
"""

from dataclasses import dataclass, replace

import psycopg

COLONNES = "chunk_id, contrat_id, assureur, section, page_debut, page_fin, texte"

SQL_SENS = f"""
    SELECT {COLONNES}, 1 - (embedding <=> %(vecteur)s::vector) AS score
    FROM passages
    WHERE contrat_id = ANY(%(contrats)s)
    ORDER BY embedding <=> %(vecteur)s::vector
    LIMIT %(k)s
"""

# plainto_tsquery relie les mots par ET (&) : une question en langage naturel ne
# contient presque jamais TOUS ses mots dans un passage. On les relie par OU (|)
# et le classement ts_rank_cd favorise les passages qui en contiennent le plus.
SQL_MOTS_CLES = f"""
    WITH requete AS (
        SELECT replace(plainto_tsquery('french', %(question)s)::text, '&', '|')::tsquery AS q
    )
    SELECT {COLONNES}, ts_rank_cd(recherche, requete.q) AS score
    FROM passages, requete
    WHERE contrat_id = ANY(%(contrats)s) AND recherche @@ requete.q
    ORDER BY score DESC
    LIMIT %(k)s
"""


@dataclass
class Passage:
    chunk_id: str
    contrat_id: str
    assureur: str
    section: str
    page_debut: int
    page_fin: int
    texte: str
    score: float = 0.0
    similarite: float | None = None   # similarité cosinus (recherche par le sens)


def fusion_rrf(classements: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion : chaque liste donne 1 / (k + rang) points à ses éléments.
    Un passage bien classé dans plusieurs listes passe devant. k=60 est la valeur
    standard : elle atténue l'écart entre la 1re et la 2e place."""
    scores: dict[str, float] = {}
    for classement in classements:
        for rang, element in enumerate(classement, start=1):
            scores[element] = scores.get(element, 0.0) + 1.0 / (k + rang)
    return sorted(scores.items(), key=lambda paire: paire[1], reverse=True)


def vecteur_sql(vecteur: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in vecteur) + "]"


class Retriever:
    def __init__(self, database_url: str, client_embedding):
        self.database_url = database_url
        self.client = client_embedding

    def _requete(self, sql: str, params: dict) -> list[Passage]:
        with psycopg.connect(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return [Passage(*ligne[:7], score=float(ligne[7])) for ligne in cur.fetchall()]

    def par_sens(self, question: str, contrat_ids: list[str], k: int) -> list[Passage]:
        vecteur = self.client.embed([question])[0]
        passages = self._requete(SQL_SENS, {"vecteur": vecteur_sql(vecteur), "contrats": contrat_ids, "k": k})
        return [replace(p, similarite=p.score) for p in passages]

    def par_mots_cles(self, question: str, contrat_ids: list[str], k: int) -> list[Passage]:
        return self._requete(SQL_MOTS_CLES, {"question": question, "contrats": contrat_ids, "k": k})

    def hybride(self, question: str, contrat_ids: list[str], k: int, profondeur: int = 20) -> list[Passage]:
        sens = self.par_sens(question, contrat_ids, profondeur)
        mots = self.par_mots_cles(question, contrat_ids, profondeur)
        return fusionner(sens, mots, k)

    def rechercher(self, question: str, contrat_ids: list[str], k: int, mode: str = "hybride") -> list[Passage]:
        if mode == "sens":
            return self.par_sens(question, contrat_ids, k)
        if mode == "mots_cles":
            return self.par_mots_cles(question, contrat_ids, k)
        if mode == "hybride":
            return self.hybride(question, contrat_ids, k)
        raise ValueError(f"Mode de recherche inconnu : {mode}")


def fusionner(sens: list[Passage], mots: list[Passage], k: int) -> list[Passage]:
    """Fusionne deux listes de passages par RRF et garde les k meilleurs.
    La similarité cosinus (utile au seuil de pertinence) est conservée."""
    par_id = {p.chunk_id: p for p in mots}
    par_id.update({p.chunk_id: p for p in sens})  # priorité aux passages porteurs de la similarité
    classement = fusion_rrf([[p.chunk_id for p in sens], [p.chunk_id for p in mots]])
    return [replace(par_id[cid], score=score) for cid, score in classement[:k]]
