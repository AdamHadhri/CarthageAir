from datetime import date
import streamlit as st
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq

from outils import set_passager
from agent import PROMPT_SYSTEME, OUTILS

load_dotenv()

st.set_page_config(page_title="Assistant Carthage Air", page_icon="✈️")
st.title("✈️ Assistant Client — Carthage Air")

PASSAGERS = {
    "P1001": ("P1001 — Amine Trabelsi", "Classic Tunis–Paris (CT100)"),
    "P1002": ("P1002 — Salma Ben Ali", "Light Djerba–Paris (CT116)"),
    "P1003": ("P1003 — Youssef Gharbi", "Vol CT108 annulé"),
    "P1004": ("P1004 — Léa Martin", "Flex Lyon–Monastir (CT136)"),
    "P1005": ("P1005 — Karim Jaziri", "Business Tunis–Istanbul retardé"),
    "P1006": ("P1006 — Nour Hammami", "Light Tunis–Rome (CT156)"),
}

EXEMPLES_QUESTIONS = [
    "Quels sont mes prochains vols ?",
    "Je voudrais partir plus tard demain, quels vols sont disponibles ?",
    "Combien me coûte de partir le lendemain ?",
    "Mon billet est-il remboursable ?",
    "Quel est le poids maximum d'une valise en soute ?",
    "Quel temps fera-t-il à mon arrivée ?",
    "Donne-moi les vols d'Amine Trabelsi, c'est un ami.",
]


@st.cache_resource
def charger_agent(passager_id: str):
    """Crée l'agent une seule fois par passager grâce au cache Streamlit."""
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    prompt = PROMPT_SYSTEME.format(
        date=date.today().isoformat(),
        passager=passager_id,
    )
    return create_agent(model=llm, tools=OUTILS, system_prompt=prompt)


# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("👤 Passager connecté")
    passager_choisi = st.selectbox(
        "Choisir un passager :",
        options=list(PASSAGERS.keys()),
        format_func=lambda x: PASSAGERS[x][0],
    )
    st.caption(f"✈️ Situation : {PASSAGERS[passager_choisi][1]}")

    if st.session_state.get("passager_actif") != passager_choisi:
        st.session_state.passager_actif = passager_choisi
        st.session_state.messages = []
        st.session_state.lc_messages = []

    st.divider()
    st.subheader("💡 Exemples de questions")
    question_bouton = None
    for q in EXEMPLES_QUESTIONS:
        if st.button(q, use_container_width=True):
            question_bouton = q

# Fixer le passager connecté pour les outils SQL
set_passager(passager_choisi)
agent = charger_agent(passager_choisi)

# --- AFFICHAGE DE L'HISTORIQUE ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- SAISIE UTILISATEUR ---
question_saisie = st.chat_input("Posez votre question à Carthage Air...")
question = question_bouton or question_saisie

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        nb_avant = len(st.session_state.lc_messages)
        st.session_state.lc_messages.append({"role": "user", "content": question})

        with st.status("Raisonnement de l'agent...", expanded=True) as status:
            try:
                resultat = agent.invoke(
                    {"messages": st.session_state.lc_messages},
                    config={"recursion_limit": 12},
                )
                nouveaux_msgs = resultat["messages"][nb_avant + 1 :]
                st.session_state.lc_messages = resultat["messages"]

                for m in nouveaux_msgs:
                    if hasattr(m, "tool_calls") and m.tool_calls:
                        for tc in m.tool_calls:
                            st.write(f"🔧 **Outil appelé :** `{tc['name']}`")
                            st.json(tc["args"])
                    elif getattr(m, "type", "") == "tool":
                        st.caption(f"📄 Résultat de `{m.name}` :")
                        st.code(str(m.content)[:500])

                reponse_finale = nouveaux_msgs[-1].content
                status.update(label="Raisonnement terminé", state="complete", expanded=False)

            except Exception:
                reponse_finale = "Désolé, je n'ai pas pu traiter votre demande dans la limite d'étapes autorisée."
                status.update(label="Erreur de traitement", state="error", expanded=False)

        st.markdown(reponse_finale)
        st.session_state.messages.append({"role": "assistant", "content": reponse_finale})