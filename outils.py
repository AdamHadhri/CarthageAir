import json
import sqlite3
import urllib.parse
import urllib.request

from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings

# ==========================================
# CONFIGURATION GLOBALE
# ==========================================

DB_PATH = "file:data/carthage_air.sqlite?mode=ro"
PASSAGER_CONNECTE = "P1001"


def set_passager(passager_id: str) -> None:
    """Fixe l'identifiant du passager connecté côté application (jamais par le LLM)."""
    global PASSAGER_CONNECTE
    PASSAGER_CONNECTE = passager_id


# 1. Initialize embeddings (same model used during indexing)
embeddings = HuggingFaceEmbeddings(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# 2. Load persisted ChromaDB
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
)

# ==========================================
# LOT 1 : OUTIL DOCUMENT (RAG)
# ==========================================

@tool
def rechercher_politique(question: str) -> str:
    """Recherche une règle dans la politique de Carthage Air (familles tarifaires,
    frais de modification, remboursement, vol annulé ou retardé, bagages).
    Renvoie les 3 sections les plus proches avec leur titre."""
    try:
        results = vectorstore.similarity_search(question, k=3)

        if not results:
            return "Aucune section pertinente trouvée dans la politique Carthage Air."

        response = "Voici les sections les plus pertinentes :\n\n"

        for i, doc in enumerate(results, start=1):
            section = doc.metadata.get("Header 1", "")
            subsection = doc.metadata.get("Header 2", "")
            titre = subsection or section or "Section politique"

            response += f"--- Résultat {i} ({titre}) ---\n"
            if section:
                response += f"Section : {section}\n"
            if subsection:
                response += f"Sous-section : {subsection}\n"
            response += f"Contenu :\n{doc.page_content}\n\n"

        return response

    except Exception as e:
        return f"Erreur lors de la recherche dans la politique : {e}"


# ==========================================
# LOT 2 : OUTILS BASE DE DONNÉES (SQL)
# ==========================================

@tool
def consulter_mes_vols() -> str:
    """Consulte les billets confirmés du passager connecté (numéro de vol, trajet,
    date, heure, statut, retard, famille tarifaire, siège et prix payé)."""
    try:
        conn = sqlite3.connect(DB_PATH, uri=True)
        cursor = conn.cursor()

        query = """
            SELECT v.numero, o.ville, v.origine, d.ville, v.destination,
                   v.date_depart, v.heure_depart, v.statut, v.retard_minutes,
                   b.famille, b.siege, b.prix_paye
            FROM billets b
            JOIN vols v ON v.id = b.vol_id
            JOIN aeroports o ON o.code = v.origine
            JOIN aeroports d ON d.code = v.destination
            WHERE b.passager_id = ? AND b.statut = 'confirmé'
            ORDER BY v.date_depart, v.heure_depart
        """
        cursor.execute(query, (PASSAGER_CONNECTE,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "Aucun billet confirmé trouvé pour ce passager."

        lignes = []
        for r in rows:
            num, v_dep, c_dep, v_arr, c_arr, date_d, heure_d, statut, retard, fam, siege, prix = r
            info_statut = statut
            if statut == "retardé" and retard:
                info_statut += f" de {retard} min"
            lignes.append(
                f"Vol {num} : {v_dep} ({c_dep}) -> {v_arr} ({c_arr}) le {date_d} à {heure_d} | "
                f"Statut : {info_statut} | Famille : {fam} | Siège : {siege} | Payé : {prix:g} DT"
            )
        return "\n".join(lignes)

    except Exception as e:
        return f"Erreur lors de la consultation des billets : {e}"


@tool
def rechercher_vols(ville_depart: str, ville_arrivee: str, date: str) -> str:
    """Recherche les vols disponibles entre deux villes à une date donnée (format AAAA-MM-JJ).
    Retourne les horaires, aéroports, statut, places restantes et prix (Light, Classic, Flex)."""
    try:
        conn = sqlite3.connect(DB_PATH, uri=True)
        cursor = conn.cursor()

        query = """
            SELECT v.numero, v.origine, v.destination, v.heure_depart, v.heure_arrivee,
                   v.statut, v.places_restantes, v.prix_light, v.prix_classic, v.prix_flex
            FROM vols v
            JOIN aeroports o ON o.code = v.origine
            JOIN aeroports d ON d.code = v.destination
            WHERE LOWER(o.ville) = LOWER(?)
              AND LOWER(d.ville) = LOWER(?)
              AND v.date_depart = ?
            ORDER BY v.heure_depart
        """
        cursor.execute(query, (ville_depart.strip(), ville_arrivee.strip(), date.strip()))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"Aucun vol trouvé de {ville_depart} vers {ville_arrivee} le {date}."

        lignes = []
        for r in rows:
            num, orig, dest, h_dep, h_arr, statut, places, p_light, p_classic, p_flex = r
            dispo = "COMPLET (0 place)" if places == 0 else f"{places} places"
            lignes.append(
                f"Vol {num} ({orig}->{dest}) : départ {h_dep}, arrivée {h_arr} | "
                f"Statut : {statut} | {dispo} | "
                f"Prix : Light {p_light:g} DT, Classic {p_classic:g} DT, Flex {p_flex:g} DT"
            )
        return "\n".join(lignes)

    except Exception as e:
        return f"Erreur lors de la recherche de vols : {e}"


# ==========================================
# LOT 3 : OUTILS API MÉTÉO ET CALCUL
# ==========================================

@tool
def meteo_destination(ville: str, date: str) -> str:
    """Donne la météo prévue (températures minimale et maximale, risque de pluie)
    pour une ville de destination à une date donnée (format AAAA-MM-JJ)."""
    try:
        # 1. Géocodage de la ville via Open-Meteo
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urllib.parse.urlencode({"name": ville, "count": 1, "language": "fr"})
        )
        with urllib.request.urlopen(geo_url, timeout=10) as resp:
            geo_data = json.loads(resp.read().decode("utf-8"))

        if not geo_data.get("results"):
            return f"Ville '{ville}' introuvable pour la météo."

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        # 2. Prévisions météo à la date demandée
        meteo_url = (
            "https://api.open-meteo.com/v1/forecast?"
            + urllib.parse.urlencode({
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_min,temperature_2m_max,precipitation_probability_max",
                "timezone": "auto",
                "start_date": date,
                "end_date": date,
            })
        )
        with urllib.request.urlopen(meteo_url, timeout=10) as resp:
            meteo_data = json.loads(resp.read().decode("utf-8"))

        daily = meteo_data.get("daily", {})
        if not daily.get("time"):
            return f"Aucune prévision météo disponible pour {ville} le {date}."

        t_min = daily["temperature_2m_min"][0]
        t_max = daily["temperature_2m_max"][0]
        pluie = daily["precipitation_probability_max"][0]

        return (
            f"Météo à {ville} le {date} : "
            f"température min {t_min}°C, max {t_max}°C, risque de pluie {pluie}%."
        )

    except Exception:
        return f"Service météo temporairement indisponible pour {ville} le {date}."


@tool
def calculer_cout_modification(
    famille: str,
    prix_paye: float,
    nouveau_prix: float,
    vol_annule_par_compagnie: bool = False,
) -> str:
    """Calcule le coût exact d'un changement de vol : frais selon la famille tarifaire
    (Light, Classic, Flex, Business) + différence tarifaire si le nouveau vol est plus cher.
    Si le vol a été annulé par la compagnie, le changement est gratuit."""
    frais_par_famille = {
        "light": ("Light", 80),
        "classic": ("Classic", 40),
        "flex": ("Flex", 0),
        "business": ("Business", 0),
    }

    cle = famille.strip().lower()
    if cle not in frais_par_famille:
        return f"Erreur : famille tarifaire '{famille}' inconnue. Choisir Light, Classic, Flex ou Business."

    nom_famille, frais = frais_par_famille[cle]

    if vol_annule_par_compagnie:
        return (
            "Vol annulé par la compagnie : changement gratuit "
            "(Frais : 0 DT ; différence tarifaire : 0 DT ; total à payer : 0 DT)."
        )

    difference = max(0.0, float(nouveau_prix) - float(prix_paye))
    total = frais + difference

    return (
        f"Frais de modification {nom_famille} : {frais:g} DT ; "
        f"différence tarifaire : {difference:g} DT ; "
        f"total à payer : {total:g} DT."
    )