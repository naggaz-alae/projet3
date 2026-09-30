"""Page d'accueil : poser une question sur UN contrat.

Lancement :  streamlit run app/Accueil.py
"""

import streamlit as st

from api_client import ErreurAPI, contrats, libelle_verdict, poser_question

st.set_page_config(page_title="Suis-je couvert ?", page_icon="🛡️", layout="centered")

st.title("🛡️ Suis-je couvert ?")
st.caption("Posez votre question : l'assistant répond à partir des conditions générales de votre "
           "assurance habitation, en citant l'article exact. Projet indépendant, non affilié aux assureurs.")

try:
    liste = contrats()
except ErreurAPI as err:
    st.error(str(err))
    st.stop()

libelles = {f"{c['assureur']} — {c['produit']}": c["id"] for c in liste}
choix = st.selectbox("Votre contrat", list(libelles))

EXEMPLES = [
    "Une fuite de ma machine à laver a abîmé le plafond du voisin du dessous : suis-je couvert ?",
    "Mon vélo a été volé dans le local commun de l'immeuble : suis-je couvert ?",
    "La grêle a endommagé ma véranda : est-ce garanti ?",
]
exemple = st.selectbox("Exemples de questions", ["(écrire ma propre question)"] + EXEMPLES)
question = st.text_area("Votre question", value="" if exemple.startswith("(") else exemple, height=100)

if st.button("Analyser mon contrat", type="primary", disabled=len(question.strip()) < 8):
    with st.spinner("Recherche dans le contrat…"):
        try:
            r = poser_question(question, libelles[choix])
        except ErreurAPI as err:
            st.error(str(err))
            st.stop()

    st.subheader(libelle_verdict(r["verdict"]))
    st.write(r["resume"])

    if r["conditions"]:
        st.markdown("**Conditions à connaître**")
        for condition in r["conditions"]:
            st.markdown(f"- {condition}")

    if r["citations"]:
        st.markdown("**Ce que dit le contrat**")
        for c in r["citations"]:
            pages = f"p. {c['page_debut']}" if c["page_debut"] == c["page_fin"] else f"p. {c['page_debut']}-{c['page_fin']}"
            with st.expander(f"{c['section']} — {pages}"):
                st.markdown(f"> {c['extrait']}")

    for avertissement in r["avertissements"]:
        st.caption(f"ℹ️ {avertissement}")

    m = r["metriques"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Temps de réponse", f"{m['latence_ms'] / 1000:.1f} s")
    col2.metric("Tokens", f"{m['tokens_entree'] + m['tokens_sortie']:,}".replace(",", " "))
    col3.metric("Coût", f"{m['cout'] * 100:.3f} ct")
