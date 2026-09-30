"""Évaluation de la RECHERCHE seule (sans LLM) : compare les modes sens / mots-clés / hybride.

Pour chaque paire (question, contrat) annotée avec une « section », on regarde à quel
rang arrive le bon passage. Indicateurs : succès à 1, à 5, et MRR.
Affiche aussi la similarité des questions hors sujet, pour calibrer SEUIL_SIMILARITE.

Lancement :  python -m evaluation.eval_recherche
"""

from datetime import datetime
from pathlib import Path

from evaluation.jeu import charger_questions, mrr, paires_annotees, percentile, rang_section, taux_succes
from ingestion import config as ingestion_config
from ingestion.catalogue import charger_catalogue
from rag import config
from rag.mistral_client import MistralClient
from rag.retriever import Retriever

MODES = ["mots_cles", "sens", "hybride"]
PROFONDEUR = 20


def run() -> None:
    contrat_ids = [c.id for c in charger_catalogue(ingestion_config.CATALOGUE_PATH)]
    questions = charger_questions()
    paires = [(q, cid, a) for q, cid, a in paires_annotees(questions, contrat_ids) if a.section]
    if not paires:
        raise SystemExit("Aucune question annotée avec une « section » dans evaluation/questions.yaml")

    retriever = Retriever(config.DATABASE_URL, MistralClient())
    lignes = ["| Mode | Succès à 1 | Succès à 5 | MRR |", "|---|---|---|---|"]
    for mode in MODES:
        rangs = []
        for q, cid, attendu in paires:
            passages = retriever.rechercher(q.question, [cid], PROFONDEUR, mode=mode)
            rangs.append(rang_section([p.section for p in passages], attendu.section))
        lignes.append(f"| {mode} | {taux_succes(rangs, 1):.0%} | {taux_succes(rangs, 5):.0%} | {mrr(rangs):.2f} |")

    # Calibrage du seuil : similarité max des questions pertinentes vs hors sujet
    def meilleure_similarite(question: str, cid: str) -> float:
        passages = retriever.rechercher(question, [cid], 1, mode="sens")
        return passages[0].similarite if passages else 0.0

    pertinentes = [meilleure_similarite(q.question, cid) for q, cid, _ in paires]
    hors_sujet = [meilleure_similarite(q.question, contrat_ids[0]) for q in questions if q.type == "hors_sujet"]

    rapport = "\n".join([
        f"# Évaluation de la recherche — {datetime.now():%Y-%m-%d %H:%M}",
        f"\n{len(paires)} paires (question, contrat) annotées sur {len(questions) * len(contrat_ids)} possibles.\n",
        *lignes,
        "\n## Calibrage du seuil de similarité\n",
        "| Questions | Min | Médiane | Max |", "|---|---|---|---|",
        f"| Pertinentes | {min(pertinentes):.3f} | {percentile(pertinentes, 50):.3f} | {max(pertinentes):.3f} |",
        f"| Hors sujet | {min(hors_sujet):.3f} | {percentile(hors_sujet, 50):.3f} | {max(hors_sujet):.3f} |",
        "\nUn bon seuil se situe entre le max des questions hors sujet et le min des questions pertinentes.",
    ])
    print(rapport)
    sortie = Path("evaluation/resultats") / f"recherche_{datetime.now():%Y%m%d_%H%M}.md"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(rapport, encoding="utf-8")
    print(f"\nRapport enregistré : {sortie}")


if __name__ == "__main__":
    run()
