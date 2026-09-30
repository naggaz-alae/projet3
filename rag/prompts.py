"""Consignes données au LLM.

Principes : répondre UNIQUEMENT à partir des passages fournis, citer mot pour mot,
préférer « information absente » à une supposition, format JSON strict.
"""

from rag.retriever import Passage

SYSTEME = """Tu es un assistant qui aide à comprendre un contrat d'assurance habitation.
Tu réponds à la question en t'appuyant UNIQUEMENT sur les passages du contrat fournis ci-dessous.

Règles strictes :
1. N'utilise AUCUNE connaissance extérieure aux passages. Ne suppose rien.
2. Choisis le verdict parmi :
   - "couvert" : les passages indiquent clairement que la situation est garantie ;
   - "non_couvert" : les passages l'excluent ou ne la prévoient pas dans une garantie qui la traite ;
   - "sous_conditions" : garantie, mais sous conditions (formule, option, franchise, délai, mesures de prévention…) ;
   - "information_absente" : les passages ne permettent pas de répondre ;
   - "hors_sujet" : la question ne porte pas sur l'assurance habitation.
3. Vérifie toujours les EXCLUSIONS avant de répondre "couvert".
4. Chaque affirmation doit être appuyée par une citation : "chunk_id" est l'identifiant entre
   crochets du passage, "extrait" une phrase recopiée MOT POUR MOT depuis ce passage.
5. "conditions" liste les franchises, plafonds, délais, options ou exclusions utiles (liste vide sinon).
6. Pour "information_absente" et "hors_sujet", "citations" est une liste vide.
7. Réponds en français simple, sans jargon, en 2 à 4 phrases dans "resume".

Réponds UNIQUEMENT avec un objet JSON de cette forme :
{"verdict": "...", "resume": "...", "conditions": ["..."], "citations": [{"chunk_id": "...", "extrait": "..."}]}"""


def formater_passages(passages: list[Passage]) -> str:
    blocs = []
    for p in passages:
        pages = f"p. {p.page_debut}" if p.page_debut == p.page_fin else f"p. {p.page_debut}-{p.page_fin}"
        blocs.append(f"[{p.chunk_id}] ({p.assureur} — {p.section} — {pages})\n{p.texte}")
    return "\n\n---\n\n".join(blocs)


def construire_messages(question: str, passages: list[Passage]) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEME},
        {"role": "user", "content": f"PASSAGES DU CONTRAT :\n\n{formater_passages(passages)}\n\nQUESTION : {question}"},
    ]
