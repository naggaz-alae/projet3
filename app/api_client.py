"""Appels à l'API depuis l'interface (l'interface ne parle jamais directement à la base ni au LLM)."""

import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

VERDICTS = {
    "couvert": ("✅", "Couvert"),
    "non_couvert": ("❌", "Non couvert"),
    "sous_conditions": ("⚠️", "Sous conditions"),
    "information_absente": ("❓", "Information absente du contrat"),
    "hors_sujet": ("🚫", "Hors sujet"),
}


def libelle_verdict(verdict: str) -> str:
    icone, texte = VERDICTS.get(verdict, ("", verdict))
    return f"{icone} {texte}"


class ErreurAPI(Exception):
    pass


def _appel(methode: str, chemin: str, **kwargs):
    try:
        reponse = requests.request(methode, f"{API_URL}{chemin}", timeout=120, **kwargs)
    except requests.RequestException as err:
        raise ErreurAPI(f"API injoignable ({API_URL}) : {err}")
    if reponse.status_code >= 400:
        try:
            detail = reponse.json().get("detail")
        except ValueError:
            detail = reponse.text
        raise ErreurAPI(f"Erreur {reponse.status_code} : {detail}")
    return reponse.json()


@st.cache_data(ttl=300)
def contrats() -> list[dict]:
    return _appel("GET", "/contrats")


def poser_question(question: str, contrat_id: str) -> dict:
    return _appel("POST", "/ask", json={"question": question, "contrat_id": contrat_id})


def comparer(question: str, contrat_ids: list[str]) -> dict:
    return _appel("POST", "/compare", json={"question": question, "contrat_ids": contrat_ids})


def statistiques() -> dict:
    return _appel("GET", "/stats")
