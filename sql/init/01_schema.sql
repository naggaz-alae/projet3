-- Exécuté automatiquement au PREMIER démarrage du conteneur PostgreSQL.

CREATE EXTENSION IF NOT EXISTS vector;

-- Un passage de contrat = une ligne (texte + vecteur + index plein texte)
CREATE TABLE IF NOT EXISTS passages (
    chunk_id     TEXT PRIMARY KEY,
    contrat_id   TEXT NOT NULL,
    assureur     TEXT NOT NULL,
    produit      TEXT NOT NULL,
    section      TEXT NOT NULL,
    page_debut   INT  NOT NULL,
    page_fin     INT  NOT NULL,
    texte        TEXT NOT NULL,
    embedding    vector(1024) NOT NULL,        -- dimension de mistral-embed
    -- Colonne calculée automatiquement : texte analysé en français
    -- (« garanties » et « garantie » deviennent le même mot)
    recherche    tsvector GENERATED ALWAYS AS (
                     to_tsvector('french', section || ' ' || texte)
                 ) STORED
);

-- Index HNSW : recherche des plus proches voisins rapide (similarité cosinus)
CREATE INDEX IF NOT EXISTS idx_passages_embedding ON passages USING hnsw (embedding vector_cosine_ops);
-- Index GIN : recherche plein texte rapide
CREATE INDEX IF NOT EXISTS idx_passages_recherche ON passages USING gin (recherche);
CREATE INDEX IF NOT EXISTS idx_passages_contrat ON passages (contrat_id);

-- Journal des requêtes : latence, tokens, coût (page « Suivi » et évaluation)
CREATE TABLE IF NOT EXISTS requetes (
    id             BIGSERIAL PRIMARY KEY,
    horodatage     TIMESTAMPTZ NOT NULL DEFAULT now(),
    type_requete   TEXT NOT NULL,              -- ask | compare | eval
    contrat_id     TEXT,
    question       TEXT NOT NULL,
    verdict        TEXT,
    latence_ms     INT,
    tokens_entree  INT,
    tokens_sortie  INT,
    cout           NUMERIC(12, 6),
    appel_llm      BOOLEAN NOT NULL DEFAULT TRUE
);
