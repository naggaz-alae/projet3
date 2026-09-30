"""Suivi de production : volume, latence, coût, verdicts."""

import pandas as pd
import streamlit as st

from api_client import ErreurAPI, libelle_verdict, statistiques

st.set_page_config(page_title="Suivi — Suis-je couvert ?", page_icon="📈", layout="wide")
st.title("📈 Suivi de l'assistant")

try:
    s = statistiques()
except ErreurAPI as err:
    st.error(str(err))
    st.stop()

if s["nb_requetes"] == 0:
    st.info("Aucune requête enregistrée pour l'instant.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Requêtes", s["nb_requetes"])
col2.metric("Latence médiane", f"{s['latence_p50_ms'] / 1000:.1f} s")
col3.metric("Latence 95e centile", f"{s['latence_p95_ms'] / 1000:.1f} s")
col4.metric("Coût moyen", f"{s['cout_moyen'] * 100:.3f} ct")

st.caption(f"Coût total : {s['cout_total']:.4f} · Requêtes traitées sans appel au LLM "
           f"(refus, aucun passage pertinent) : {s['nb_sans_appel_llm']}")

st.subheader("Répartition des verdicts")
verdicts = pd.DataFrame(
    [{"Verdict": libelle_verdict(v), "Nombre": n} for v, n in s["repartition_verdicts"].items()]
).set_index("Verdict")
st.bar_chart(verdicts)

st.subheader("Dernières requêtes")
st.dataframe(pd.DataFrame(s["dernieres_requetes"]), hide_index=True, use_container_width=True)
