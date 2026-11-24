from datetime import date
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq

from outils import (
    set_passager,
    rechercher_politique,
    consulter_mes_vols,
    rechercher_vols,
    meteo_destination,
    calculer_cout_modification,
)

load_dotenv()

OUTILS = [
    rechercher_politique,
    consulter_mes_vols,
    rechercher_vols,
    meteo_destination,
    calculer_cout_modification,
]

PROMPT_SYSTEME = """Tu es l'assistant client de Carthage Air. Réponds en français, brièvement.
Nous sommes le {date}. Le passager connecté a l'identifiant {passager}.

Règles :
1. Pour une question sur les billets du passager, utilise consulter_mes_vols.
2. Pour chercher d'autres vols, utilise rechercher_vols (dates au format AAAA-MM-JJ).
3. Pour toute règle (frais, remboursement, bagages, retard...), utilise rechercher_politique et cite la section.
4. Pour la météo à destination, utilise meteo_destination.
5. Ne calcule jamais un montant toi-même : utilise calculer_cout_modification.
6. Combine les outils si nécessaire.
7. Ne réponds jamais sur un autre passager. Hors domaine : dis que ce n'est pas ton rôle.
8. Si l'information n'est ni dans les outils ni dans la politique, dis que tu ne sais pas."""


def creer_agent_carthage(passager_id: str):
    """Configure le passager connecté et crée l'agent ReAct."""
    set_passager(passager_id)

    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0,
    )

    prompt = PROMPT_SYSTEME.format(
        date=date.today().isoformat(),
        passager=passager_id,
    )

    return create_agent(
        model=llm,
        tools=OUTILS,
        system_prompt=prompt,
    )


def poser_question(passager_id: str, question: str, historique: list | None = None):
    """Envoie une question à l'agent avec une limite de 12 étapes (recursion_limit)."""
    agent = creer_agent_carthage(passager_id)

    messages = list(historique) if historique else []
    messages.append({"role": "user", "content": question})

    try:
        resultat = agent.invoke(
            {"messages": messages},
            config={"recursion_limit": 12},
        )
        return resultat["messages"]
    except Exception as e:
        return [
            {"role": "assistant", "content": f"Désolé, je n'ai pas pu traiter la demande ({e})."}
        ]