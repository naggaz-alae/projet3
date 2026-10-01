# Suis-je couvert ?

Un petit assistant qui répond à une question simple : « est-ce que mon assurance habitation me couvre pour ça ? »

Les conditions générales d'assurance font souvent 60 à 100 pages et presque personne ne les lit. L'idée du projet : on pose une question (« mon voisin du dessus a inondé ma salle de bain, je suis couvert ? »), et l'appli va chercher les articles concernés dans le contrat, donne une réponse (couvert, pas couvert, sous conditions…) et montre le passage exact du contrat avec la page. On peut aussi poser la même question sur plusieurs assureurs pour comparer.

Pour l'instant j'ai intégré les conditions générales habitation de la MAIF, de la Macif, de la MAAF et de la Matmut (liste dans `data/catalogue.yaml`).

> Projet perso fait dans le cadre de mes études, sans lien avec les assureurs. Les réponses sont indicatives, seul le contrat fait foi.

## Comment ça marche

1. Je télécharge les PDF des contrats, j'en extrais le texte et je le découpe article par article (pas par blocs de N caractères, sinon une exclusion se retrouve séparée de la garantie qu'elle concerne).
2. Chaque morceau est transformé en vecteur avec l'API de Mistral, puis stocké dans PostgreSQL avec l'extension pgvector.
3. Quand une question arrive, je fais une recherche « hybride » : par le sens (vecteurs) et par mots-clés (recherche plein texte de Postgres), puis je fusionne les deux classements.
4. Les meilleurs passages sont envoyés à Mistral, qui doit répondre dans un format JSON précis.
5. Avant d'afficher la réponse, je vérifie que les citations renvoyées existent vraiment dans le contrat. Si le modèle dit « couvert » sans citation valable, la réponse devient « information absente ». Je préfère ne pas répondre plutôt que répondre faux.

Il y a aussi quelques garde-fous : les questions hors sujet sont refusées sans appeler le modèle, et les embeddings sont mis en cache pour ne pas payer deux fois.

Côté technique : Python, FastAPI pour l'API, Streamlit pour l'interface, PostgreSQL + pgvector, Mistral pour les embeddings et la génération, Docker pour tout lancer.

## Lancer le projet

Il faut Docker et une clé API Mistral (https://console.mistral.ai).

```bash
cp .env.example .env          # mettre sa clé MISTRAL_API_KEY dedans
docker compose up -d db

# à faire une seule fois : récupérer et indexer les contrats
docker compose run --rm api python -m ingestion.download
docker compose run --rm api python -m ingestion.build_chunks
docker compose run --rm api python -m ingestion.index

docker compose up -d
```

Ensuite :
- l'interface : http://localhost:8501
- l'API (avec la doc Swagger) : http://localhost:8000/docs

Sans Docker, ça marche aussi avec un environnement virtuel : `pip install -r requirements.txt`, puis les mêmes commandes Python, et `uvicorn api.main:app --reload` / `streamlit run app/Accueil.py`. Il faut quand même une base Postgres avec pgvector.

## Évaluation

J'ai préparé 40 questions dans `evaluation/questions.yaml` : des questions classiques, des questions pièges (exclusions, franchises, défaut d'entretien…) et quelques questions hors sujet. Les bonnes réponses sont vérifiées à la main dans les PDF.

```bash
python -m evaluation.eval_recherche   # qualité de la recherche seule
python -m evaluation.run_eval         # l'assistant complet (verdicts, citations, coût, temps de réponse)
```

## Tests

```bash
pytest
```

Les tests n'appellent ni Mistral ni la base de données (j'utilise des faux objets et des PDF générés), donc ils tournent sans clé API. Ils sont aussi lancés automatiquement par GitHub Actions à chaque push.

## Organisation du code

```
ingestion/    téléchargement des PDF, extraction, découpage, embeddings, indexation
rag/          recherche, prompts, appel au modèle, vérification des citations
api/          l'API FastAPI (/ask, /compare, /contrats, /stats, /health)
app/          l'interface Streamlit
evaluation/   les questions de test et les scripts d'évaluation
sql/init/     le schéma de la base
tests/        les tests
```

Les PDF ne sont pas dans le dépôt (ils appartiennent aux assureurs), le script `ingestion.download` les récupère.

## Ce qui reste à améliorer

- Seules les conditions générales sont prises en compte. Dans la vraie vie, les conditions particulières (formule, options) changent souvent la réponse.
- Les tableaux des PDF (plafonds, franchises) sont lus comme du texte brut, ce qui n'aide pas pour les questions sur les montants.
- Ajouter une étape de reclassement des passages avant d'appeler le modèle.
- Mettre l'appli en ligne (les notes sont dans `docs/DEPLOIEMENT.md`).
