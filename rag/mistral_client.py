"""Client minimal de l'API Mistral (HTTP direct, sans SDK) : embeddings + chat JSON.

Gère les erreurs temporaires (429 = trop de requêtes, 5xx = serveur) par des
nouvelles tentatives avec attente croissante.
"""

import logging
import time
from dataclasses import dataclass

import requests

from rag import config

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Erreur d'appel au modèle (clé absente, API indisponible, réponse invalide)."""


@dataclass
class ReponseChat:
    contenu: str
    tokens_entree: int
    tokens_sortie: int


class MistralClient:
    def __init__(self, api_key: str = config.MISTRAL_API_KEY, base_url: str = config.MISTRAL_BASE_URL,
                 modele_chat: str = config.MODELE_CHAT, modele_embedding: str = config.MODELE_EMBEDDING,
                 timeout: int = 60):
        if not api_key:
            raise LLMError("MISTRAL_API_KEY manquante : renseigne-la dans le fichier .env")
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.modele_chat = modele_chat
        self.modele_embedding = modele_embedding
        self.timeout = timeout

    def _post(self, chemin: str, payload: dict, retries: int = 4) -> dict:
        url = f"{self.base_url}{chemin}"
        for tentative in range(1, retries + 1):
            try:
                reponse = requests.post(url, json=payload, headers=self.headers, timeout=self.timeout)
            except requests.RequestException as err:
                erreur = str(err)
            else:
                if reponse.status_code == 429 or reponse.status_code >= 500:
                    erreur = f"HTTP {reponse.status_code}"
                elif reponse.status_code >= 400:
                    raise LLMError(f"HTTP {reponse.status_code} sur {chemin} : {reponse.text[:300]}")
                else:
                    return reponse.json()
            logger.warning("Mistral %s : tentative %s/%s échouée (%s)", chemin, tentative, retries, erreur)
            if tentative < retries:
                time.sleep(2**tentative)
        raise LLMError(f"API Mistral indisponible après {retries} tentatives ({erreur})")

    def embed(self, textes: list[str], taille_lot: int = 32) -> list[list[float]]:
        """Un vecteur par texte, envoyés par lots pour limiter le nombre d'appels."""
        vecteurs: list[list[float]] = []
        for debut in range(0, len(textes), taille_lot):
            lot = textes[debut:debut + taille_lot]
            data = self._post("/embeddings", {"model": self.modele_embedding, "input": lot})["data"]
            # L'API renvoie un index par vecteur : on trie pour garantir l'ordre
            vecteurs.extend(item["embedding"] for item in sorted(data, key=lambda d: d["index"]))
        return vecteurs

    def chat_json(self, messages: list[dict], temperature: float = 0.0) -> ReponseChat:
        """Appel au modèle de chat en mode JSON (la réponse est forcément un objet JSON)."""
        data = self._post("/chat/completions", {
            "model": self.modele_chat,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        })
        usage = data.get("usage", {})
        return ReponseChat(
            contenu=data["choices"][0]["message"]["content"],
            tokens_entree=usage.get("prompt_tokens", 0),
            tokens_sortie=usage.get("completion_tokens", 0),
        )
