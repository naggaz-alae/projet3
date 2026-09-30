"""Aide à l'annotation : affiche les passages les plus pertinents pour une question,
afin de vérifier la bonne réponse dans le contrat et de remplir questions.yaml.

Lancement :  python -m evaluation.annoter --question q01 --contrat macif_habitation
"""

import argparse

from evaluation.jeu import charger_questions
from rag import config
from rag.mistral_client import MistralClient
from rag.retriever import Retriever


def run(question_id: str, contrat_id: str, nb: int) -> None:
    question = next((q for q in charger_questions() if q.id == question_id), None)
    if question is None:
        raise SystemExit(f"Question inconnue : {question_id}")

    retriever = Retriever(config.DATABASE_URL, MistralClient())
    print(f"\n{question.id} — {question.question}\nContrat : {contrat_id}\n")
    for rang, p in enumerate(retriever.rechercher(question.question, [contrat_id], nb), start=1):
        print(f"#{rang}  [{p.chunk_id}]  p.{p.page_debut}-{p.page_fin}  {p.section}")
        print("    " + p.texte[:600].replace("\n", "\n    ") + "\n")
    print("Vérifie dans le PDF, puis complète questions.yaml, par exemple :")
    print(f"  {contrat_id}: {{verdict: sous_conditions, section: \"<morceau du titre de section>\"}}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True)
    parser.add_argument("--contrat", required=True)
    parser.add_argument("--nb", type=int, default=8)
    args = parser.parse_args()
    run(args.question, args.contrat, args.nb)
