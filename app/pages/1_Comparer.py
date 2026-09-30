"""Comparer plusieurs assureurs sur la même question."""

import pandas as pd
import streamlit as st

from api_client import ErreurAPI, comparer, contrats, libelle_verdict

st.set_page_config(page_title="Comparer — Suis-je couvert ?", page_icon="⚖️", layout="wide")
st.title("⚖️ Comparer les contrats")

try:
    liste = contrats()
except ErreurAPI as err:
    st.error(str(err))
    st.stop()

libelles = {f"{c['assureur']} — {c['produit']}": c["id"] for c in liste}
choix = st.multiselect("Contrats à comparer (2 à 6)", list(libelles), default=list(libelles)[:4])
question = st.text_area("Question", "Mon vélo a été volé dans le local commun de l'immeuble : suis-je couvert ?")

if st.button("Comparer", type="primary", disabled=not (2 <= len(choix) <= 6) or len(question.strip()) < 8):
    with st.spinner("Analyse des contrats en parallèle…"):
        try:
            resultat = comparer(question, [libelles[c] for c in choix])
        except ErreurAPI as err:
            st.error(str(err))
            st.stop()

    reponses = resultat["reponses"]
    tableau = pd.DataFrame([{
        "Assureur": r["assureur"],
        "Verdict": libelle_verdict(r["verdict"]),
        "Conditions": " · ".join(r["conditions"]) or "—",
        "Sources": ", ".join(f"p. {c['page_debut']}" for c in r["citations"]) or "—",
    } for r in reponses])
    st.dataframe(tableau, hide_index=True, use_container_width=True)

    st.markdown("### Détail par assureur")
    for r in reponses:
        with st.expander(f"{r['assureur']} — {libelle_verdict(r['verdict'])}"):
            st.write(r["resume"])
            for c in r["citations"]:
                st.markdown(f"> {c['extrait']}  \n*{c['section']} — p. {c['page_debut']}*")

    cout = sum(r["metriques"]["cout"] for r in reponses)
    st.caption(f"Coût total de la comparaison : {cout * 100:.3f} centime(s). Réponses indicatives : seuls les contrats font foi.")
