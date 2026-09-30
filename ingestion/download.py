"""Télécharge les PDF du catalogue dans data/contrats/.

Un manifeste (manifest.json) garde pour chaque PDF son empreinte SHA-256 :
si un assureur publie une nouvelle version de ses conditions générales,
on le détecte au prochain téléchargement.

Lancement :  python -m ingestion.download [--force]
"""

import argparse
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from ingestion import config
from ingestion.catalogue import Contrat, charger_catalogue

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("download")

# Certains sites refusent les requêtes sans navigateur identifié
HEADERS = {"User-Agent": "Mozilla/5.0 (projet portfolio suis-je-couvert)"}


class TelechargementInvalide(Exception):
    pass


def telecharger_pdf(url: str, retries: int = 3, timeout: int = 60) -> bytes:
    """Renvoie le contenu du PDF, après avoir vérifié que c'est bien un PDF."""
    derniere_erreur: Exception | None = None
    for tentative in range(1, retries + 1):
        try:
            reponse = requests.get(url, headers=HEADERS, timeout=timeout)
            reponse.raise_for_status()
            contenu = reponse.content
            # Un PDF commence toujours par "%PDF" : sinon on a reçu une page HTML d'erreur
            if not contenu.startswith(b"%PDF"):
                raise TelechargementInvalide(f"{url} ne renvoie pas un PDF")
            return contenu
        except requests.RequestException as err:
            derniere_erreur = err
            logger.warning("Tentative %s/%s échouée pour %s : %s", tentative, retries, url, err)
            if tentative < retries:
                time.sleep(2**tentative)
    raise TelechargementInvalide(f"Échec après {retries} tentatives : {derniere_erreur}")


def lire_manifeste(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else {}


def traiter_contrat(contrat: Contrat, manifeste: dict, force: bool) -> None:
    chemin = config.CONTRATS_DIR / f"{contrat.id}.pdf"
    if chemin.exists() and not force:
        logger.info("%s : déjà présent (--force pour retélécharger)", contrat.id)
        return

    contenu = telecharger_pdf(str(contrat.url))
    empreinte = hashlib.sha256(contenu).hexdigest()
    ancienne = manifeste.get(contrat.id, {}).get("sha256")
    if ancienne and ancienne != empreinte:
        logger.warning("%s : NOUVELLE VERSION détectée du document", contrat.id)

    chemin.write_bytes(contenu)
    manifeste[contrat.id] = {
        "url": str(contrat.url),
        "sha256": empreinte,
        "octets": len(contenu),
        "telecharge_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    logger.info("%s : %s Ko téléchargés", contrat.id, len(contenu) // 1024)


def run(force: bool = False) -> None:
    config.CONTRATS_DIR.mkdir(parents=True, exist_ok=True)
    manifeste = lire_manifeste(config.MANIFEST_PATH)
    echecs = []
    for contrat in charger_catalogue(config.CATALOGUE_PATH):
        try:
            traiter_contrat(contrat, manifeste, force)
        except TelechargementInvalide as err:
            # Un contrat en échec ne bloque pas les autres
            logger.error("%s : %s", contrat.id, err)
            echecs.append(contrat.id)
    config.MANIFEST_PATH.write_text(json.dumps(manifeste, indent=2, ensure_ascii=False), encoding="utf-8")
    if echecs:
        logger.error("Contrats non téléchargés : %s", echecs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="retélécharger même si le PDF existe")
    run(force=parser.parse_args().force)
