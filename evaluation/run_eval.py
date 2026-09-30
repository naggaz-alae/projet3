"""Évaluation COMPLÈTE de l'assistant (recherche + LLM + garde-fous).

Indicateurs : justesse du verdict (dont questions pièges), refus corrects des
questions hors sujet, fidélité des citations, latence (médiane, 95e centile), coût.

Lancement :  python -m evaluation.run_eval
"""

import json
from datetime import datetime
from pathlib import Path

from evaluation.jeu import charger_questions, paires_annotees, percentile
from rag.assistant import Assistant
from rag.schemas import Verdict


def taux(liste: list[bool]) -> str:
    return f"{sum(liste) / len(liste):.0%} ({sum(liste)}/{len(liste)})" if liste else "—"


def run() -> None:
    assistant = Assistant.depuis_config()
    questions = charger_questions()
    paires = [(q, cid, a) for q, cid, a in paires_annotees(questions, list(assistant.contrats)) if a.verdict]
    if not paires:
        raise SystemExit("Aucune question annotée avec un « verdict » dans evaluation/questions.yaml")

    details = []
    for q, cid, attendu in paires:
        r = assistant.repondre(q.question, cid, type_requete="eval")
        details.append({
            "question_id": q.id, "type": q.type, "contrat_id": cid,
            "attendu": attendu.verdict.value, "obtenu": r.verdict.value,
            "correct": r.verdict == attendu.verdict,
            "citations_valides": len(r.citations), "citations_invalides": r.metriques.citations_invalides,
            "latence_ms": r.metriques.latence_ms, "cout": r.metriques.cout, "appel_llm": r.metriques.appel_llm,
        })
        print(f"{'✅' if details[-1]['correct'] else '❌'} {q.id} {cid:<24} attendu={attendu.verdict.value:<20} obtenu={r.verdict.value}")

    fond = [d for d in details if d["type"] != "hors_sujet"]
    valides = sum(d["citations_valides"] for d in details)
    invalides = sum(d["citations_invalides"] for d in details)
    latences = [d["latence_ms"] for d in details if d["appel_llm"]]
    couts = [d["cout"] for d in details]

    lignes = [
        f"# Évaluation de l'assistant — {datetime.now():%Y-%m-%d %H:%M}",
        f"\n{len(details)} réponses évaluées ({len(questions)} questions dans le jeu).\n",
        "| Indicateur | Résultat |", "|---|---|",
        f"| Justesse du verdict (classiques + pièges) | {taux([d['correct'] for d in fond])} |",
        f"| … dont questions pièges | {taux([d['correct'] for d in fond if d['type'] == 'piege'])} |",
        f"| Refus corrects (hors sujet) | {taux([d['correct'] for d in details if d['attendu'] == Verdict.HORS_SUJET.value])} |",
        f"| Fidélité des citations | {taux([True] * valides + [False] * invalides)} |",
        f"| Latence médiane / 95e centile | {percentile(latences, 50) / 1000:.1f} s / {percentile(latences, 95) / 1000:.1f} s |",
        f"| Coût moyen par question | {sum(couts) / len(couts) * 100:.3f} centime(s) |",
        f"| Coût total de l'évaluation | {sum(couts):.4f} |",
    ]
    rapport = "\n".join(lignes)
    print("\n" + rapport)

    dossier = Path("evaluation/resultats")
    dossier.mkdir(parents=True, exist_ok=True)
    horodatage = f"{datetime.now():%Y%m%d_%H%M}"
    (dossier / f"assistant_{horodatage}.md").write_text(rapport, encoding="utf-8")
    (dossier / f"assistant_{horodatage}.json").write_text(json.dumps(details, indent=2, ensure_ascii=False),
                                                          encoding="utf-8")
    print(f"\nRapports enregistrés dans {dossier}/")


if __name__ == "__main__":
    run()
