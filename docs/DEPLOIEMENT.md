# Mise en ligne

Architecture en ligne proposée (3 services gratuits ou quasi gratuits — **vérifier les offres
et leurs limites au moment du déploiement**, elles changent régulièrement) :

```
Streamlit Community Cloud (interface)  ──►  Render (API FastAPI, Docker)  ──►  PostgreSQL + pgvector hébergé
                                                     │                          (Neon ou Supabase)
                                                     └──►  API Mistral
```

## 1. Base de données hébergée

1. Crée une base PostgreSQL sur **Neon** ou **Supabase** (les deux proposent l'extension pgvector).
2. Exécute le schéma : `psql "<URL_DE_LA_BASE>" -f sql/init/01_schema.sql`
3. Indexe les contrats **depuis ton ordinateur**, en pointant vers la base en ligne :
   ```bash
   DATABASE_URL="<URL_DE_LA_BASE>" python -m ingestion.index
   ```
   (les PDF et le découpage restent en local : seule la base est en ligne)

## 2. API sur Render

1. Nouveau **Web Service** → connecte le repo GitHub → environnement **Docker** (le `Dockerfile` lance l'API).
2. Variables d'environnement : `MISTRAL_API_KEY`, `DATABASE_URL` (URL de la base hébergée),
   `PRIX_ENTREE_PAR_MILLION`, `PRIX_SORTIE_PAR_MILLION`.
3. Vérifie : `https://<ton-api>.onrender.com/docs` doit afficher le Swagger.

> Sur une offre gratuite, le service peut « s'endormir » après une période d'inactivité :
> la première requête est alors lente. À mentionner dans le README.

## 3. Interface sur Streamlit Community Cloud

1. Nouvelle app → repo GitHub → fichier principal `app/Accueil.py`.
2. Dans **Secrets / variables**, ajoute `API_URL = "https://<ton-api>.onrender.com"`.

## 4. Protéger ton budget

L'API est publique : n'importe qui peut déclencher des appels payants à Mistral.
- Fixe une **limite de dépense mensuelle** dans la console Mistral.
- Le journal (`/stats`, page « Suivi ») permet de surveiller le coût réel.
