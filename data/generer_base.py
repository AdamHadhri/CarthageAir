"""
Carthage Air — génération de la base de test (SQLite).

Usage :  uv run data/generer_base.py      (ou : python data/generer_base.py)

La base est régénérée avec des dates relatives au jour d'exécution :
« J » = aujourd'hui, « J+1 » = demain, etc. Les vols couvrent J-3 à J+30.
Le contenu est déterministe (graine fixe) : deux générations le même jour
donnent exactement la même base.

Contenu : 12 aéroports, 34 vols par jour x 34 jours = 1 156 vols,
40 passagers, des billets. Les 6 passagers de démonstration (P1001 à P1006)
portent les situations décrites dans le cahier des charges.
"""

import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

CHEMIN_BASE = Path(__file__).resolve().parent / "carthage_air.sqlite"
GRAINE = 2026
JOUR_DEBUT, JOUR_FIN = -3, 30  # fenêtre des vols, relative à aujourd'hui

# ---------------------------------------------------------------------------
# Référentiel
# ---------------------------------------------------------------------------
AEROPORTS = [
    # code, nom, ville, pays
    ("TUN", "Tunis-Carthage", "Tunis", "Tunisie"),
    ("DJE", "Djerba-Zarzis", "Djerba", "Tunisie"),
    ("MIR", "Monastir Habib-Bourguiba", "Monastir", "Tunisie"),
    ("SFA", "Sfax-Thyna", "Sfax", "Tunisie"),
    ("NBE", "Enfidha-Hammamet", "Enfidha", "Tunisie"),
    ("TOE", "Tozeur-Nefta", "Tozeur", "Tunisie"),
    ("CDG", "Paris-Charles de Gaulle", "Paris", "France"),
    ("ORY", "Paris-Orly", "Paris", "France"),
    ("LYS", "Lyon-Saint Exupéry", "Lyon", "France"),
    ("MRS", "Marseille-Provence", "Marseille", "France"),
    ("FCO", "Rome-Fiumicino", "Rome", "Italie"),
    ("IST", "Istanbul", "Istanbul", "Turquie"),
]

# Programme quotidien : numéro, origine, destination, heure départ, durée (min),
# prix Light de référence (DT), capacité
PROGRAMME = [
    # Tunis <-> Paris (5 allers, 5 retours)
    ("CT100", "TUN", "CDG", "07:15", 135, 640, 174),
    ("CT102", "TUN", "ORY", "09:00", 135, 620, 174),
    ("CT104", "TUN", "CDG", "11:30", 135, 650, 174),
    ("CT106", "TUN", "CDG", "16:45", 135, 630, 174),
    ("CT108", "TUN", "ORY", "18:10", 135, 610, 174),
    ("CT101", "CDG", "TUN", "10:30", 140, 640, 174),
    ("CT103", "ORY", "TUN", "12:15", 140, 620, 174),
    ("CT105", "CDG", "TUN", "14:50", 140, 650, 174),
    ("CT107", "CDG", "TUN", "19:55", 140, 630, 174),
    ("CT109", "ORY", "TUN", "21:05", 140, 600, 174),
    # Djerba <-> Paris
    ("CT116", "DJE", "CDG", "08:40", 160, 690, 174),
    ("CT117", "CDG", "DJE", "12:30", 165, 690, 174),
    ("CT118", "DJE", "ORY", "14:20", 160, 670, 174),
    ("CT119", "ORY", "DJE", "18:15", 165, 670, 174),
    # Monastir, Enfidha, Sfax <-> Paris
    ("CT120", "MIR", "ORY", "10:10", 150, 600, 174),
    ("CT121", "ORY", "MIR", "14:00", 150, 600, 174),
    ("CT122", "NBE", "CDG", "06:50", 150, 590, 174),
    ("CT123", "CDG", "NBE", "10:40", 150, 590, 174),
    ("CT126", "SFA", "ORY", "07:30", 155, 640, 174),
    ("CT127", "ORY", "SFA", "11:20", 155, 640, 174),
    # Lyon
    ("CT130", "TUN", "LYS", "08:15", 120, 610, 174),
    ("CT131", "LYS", "TUN", "11:30", 125, 610, 174),
    ("CT136", "LYS", "MIR", "13:05", 125, 590, 174),
    ("CT137", "MIR", "LYS", "16:20", 125, 590, 174),
    # Marseille, Istanbul, Rome
    ("CT140", "TUN", "MRS", "09:40", 105, 520, 174),
    ("CT141", "MRS", "TUN", "12:30", 105, 520, 174),
    ("CT146", "TUN", "IST", "15:40", 165, 700, 174),
    ("CT147", "IST", "TUN", "07:30", 170, 700, 174),
    ("CT156", "TUN", "FCO", "10:05", 75, 480, 174),
    ("CT157", "FCO", "TUN", "12:20", 80, 480, 174),
    # Domestique
    ("CT160", "TUN", "DJE", "07:00", 60, 160, 70),
    ("CT161", "DJE", "TUN", "08:45", 60, 160, 70),
    ("CT170", "TUN", "TOE", "13:30", 65, 150, 70),
    ("CT171", "TOE", "TUN", "15:20", 65, 150, 70),
]

PASSAGERS = [
    # Passagers de démonstration (cahier des charges, section 03)
    ("P1001", "Amine", "Trabelsi"),
    ("P1002", "Salma", "Ben Ali"),
    ("P1003", "Youssef", "Gharbi"),
    ("P1004", "Léa", "Martin"),
    ("P1005", "Karim", "Jaziri"),
    ("P1006", "Nour", "Hammami"),
    # Autres passagers
    ("P1007", "Mehdi", "Bouazizi"), ("P1008", "Ines", "Chaabane"),
    ("P1009", "Sami", "Ferchichi"), ("P1010", "Rania", "Mabrouk"),
    ("P1011", "Hatem", "Ayari"), ("P1012", "Olfa", "Kammoun"),
    ("P1013", "Walid", "Dridi"), ("P1014", "Meriem", "Sassi"),
    ("P1015", "Thomas", "Dubois"), ("P1016", "Camille", "Bernard"),
    ("P1017", "Skander", "Mejri"), ("P1018", "Yasmine", "Ellouze"),
    ("P1019", "Nizar", "Baccar"), ("P1020", "Asma", "Zouari"),
    ("P1021", "Marco", "Rossi"), ("P1022", "Giulia", "Bianchi"),
    ("P1023", "Emre", "Yilmaz"), ("P1024", "Ayşe", "Demir"),
    ("P1025", "Hichem", "Khelifi"), ("P1026", "Fatma", "Jebali"),
    ("P1027", "Anis", "Hamdi"), ("P1028", "Sonia", "Masmoudi"),
    ("P1029", "Lucas", "Moreau"), ("P1030", "Chloé", "Laurent"),
    ("P1031", "Bilel", "Toumi"), ("P1032", "Ons", "Karoui"),
    ("P1033", "Fares", "Rekik"), ("P1034", "Mariem", "Feki"),
    ("P1035", "Zied", "Chtourou"), ("P1036", "Hela", "Ben Salah"),
    ("P1037", "Julien", "Petit"), ("P1038", "Sarah", "Garnier"),
    ("P1039", "Khaled", "Mansouri"), ("P1040", "Amira", "Haddad"),
]

FAMILLES = ["Light", "Classic", "Flex", "Business"]
COEF_FAMILLE = {"Light": 1.0, "Classic": 1.2, "Flex": 1.45, "Business": 2.4}


def arrondi5(x: float) -> int:
    return int(round(x / 5.0) * 5)


def heure_plus(heure: str, minutes: int) -> str:
    t = datetime.strptime(heure, "%H:%M") + timedelta(minutes=minutes)
    return t.strftime("%H:%M")


def prix_light(base: int, ecart_jours: int, d: date, rng: random.Random) -> int:
    """Prix plus élevé à l'approche du départ et en fin de semaine."""
    if ecart_jours <= 2:
        f = 1.35
    elif ecart_jours <= 7:
        f = 1.20
    elif ecart_jours <= 14:
        f = 1.08
    else:
        f = 1.0
    if d.weekday() in (4, 5, 6):  # vendredi, samedi, dimanche
        f *= 1.07
    f *= rng.uniform(0.95, 1.05)
    return arrondi5(base * f)


def grille(light: int) -> dict:
    return {fam: arrondi5(light * c) if fam != "Light" else light
            for fam, c in COEF_FAMILLE.items()}


# ---------------------------------------------------------------------------
# Schéma
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE meta (
    cle    TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);

CREATE TABLE aeroports (
    code  TEXT PRIMARY KEY,          -- code IATA
    nom   TEXT NOT NULL,
    ville TEXT NOT NULL,
    pays  TEXT NOT NULL
);

CREATE TABLE vols (
    id               INTEGER PRIMARY KEY,
    numero           TEXT NOT NULL,            -- ex. CT100
    date_depart      TEXT NOT NULL,            -- AAAA-MM-JJ (heure locale)
    heure_depart     TEXT NOT NULL,            -- HH:MM
    heure_arrivee    TEXT NOT NULL,            -- HH:MM (même jour)
    origine          TEXT NOT NULL REFERENCES aeroports(code),
    destination      TEXT NOT NULL REFERENCES aeroports(code),
    statut           TEXT NOT NULL CHECK (statut IN ('prévu','retardé','annulé','effectué')),
    retard_minutes   INTEGER NOT NULL DEFAULT 0,
    capacite         INTEGER NOT NULL,
    places_restantes INTEGER NOT NULL CHECK (places_restantes >= 0),
    prix_light       INTEGER NOT NULL,         -- prix actuels en DT
    prix_classic     INTEGER NOT NULL,
    prix_flex        INTEGER NOT NULL,
    prix_business    INTEGER NOT NULL,
    UNIQUE (numero, date_depart)
);

CREATE TABLE passagers (
    id        TEXT PRIMARY KEY,                -- ex. P1001
    prenom    TEXT NOT NULL,
    nom       TEXT NOT NULL,
    email     TEXT NOT NULL,
    telephone TEXT NOT NULL
);

CREATE TABLE billets (
    id          TEXT PRIMARY KEY,              -- ex. B000001
    passager_id TEXT NOT NULL REFERENCES passagers(id),
    vol_id      INTEGER NOT NULL REFERENCES vols(id),
    famille     TEXT NOT NULL CHECK (famille IN ('Light','Classic','Flex','Business')),
    siege       TEXT NOT NULL,
    prix_paye   INTEGER NOT NULL,              -- DT
    statut      TEXT NOT NULL CHECK (statut IN ('confirmé','annulé','utilisé')),
    date_achat  TEXT NOT NULL,                 -- AAAA-MM-JJ
    UNIQUE (vol_id, siege)
);

CREATE INDEX idx_vols_trajet ON vols(origine, destination, date_depart);
CREATE INDEX idx_billets_passager ON billets(passager_id);
"""


def generer(chemin: Path = CHEMIN_BASE) -> None:
    rng = random.Random(GRAINE)
    j0 = date.today()

    def jour(n: int) -> str:
        return (j0 + timedelta(days=n)).isoformat()

    if chemin.exists():
        chemin.unlink()
    con = sqlite3.connect(chemin)
    con.executescript(SCHEMA)
    con.execute("INSERT INTO meta VALUES ('date_generation', ?)", (j0.isoformat(),))
    con.execute("INSERT INTO meta VALUES ('fenetre_vols', ?)", (f"{jour(JOUR_DEBUT)} -> {jour(JOUR_FIN)}",))
    con.executemany("INSERT INTO aeroports VALUES (?,?,?,?)", AEROPORTS)

    # --- Vols ---------------------------------------------------------------
    vols = {}  # (numero, ecart) -> dict
    vid = 0
    for ecart in range(JOUR_DEBUT, JOUR_FIN + 1):
        d = j0 + timedelta(days=ecart)
        for numero, ori, dst, hdep, duree, base, cap in PROGRAMME:
            vid += 1
            light = prix_light(base, max(ecart, 0), d, rng)
            p = grille(light)
            remplissage = rng.uniform(0.35, 1.0) if ecart >= 0 else 1.0
            places = max(0, int(cap * (1 - remplissage)))
            if ecart >= 0 and rng.random() < 0.04:
                places = 0  # quelques vols complets
            statut = "effectué" if ecart < 0 else "prévu"
            vols[(numero, ecart)] = dict(
                id=vid, numero=numero, date_depart=d.isoformat(), heure_depart=hdep,
                heure_arrivee=heure_plus(hdep, duree), origine=ori, destination=dst,
                statut=statut, retard_minutes=0, capacite=cap, places_restantes=places,
                prix_light=p["Light"], prix_classic=p["Classic"],
                prix_flex=p["Flex"], prix_business=p["Business"],
            )

    def fixer(numero, ecart, light=None, **champs):
        v = vols[(numero, ecart)]
        if light is not None:
            p = grille(light)
            v.update(prix_light=p["Light"], prix_classic=p["Classic"],
                     prix_flex=p["Flex"], prix_business=p["Business"])
        v.update(champs)
        return v

    # Situations imposées par le cahier des charges ------------------------
    # Tunis -> Paris demain (EF-02, T02, T03) : 11:30 complet, les autres ouverts
    fixer("CT100", 1, light=760, places_restantes=12)
    fixer("CT102", 1, light=780, places_restantes=23)
    fixer("CT104", 1, light=820, places_restantes=0)          # complet
    fixer("CT106", 1, light=770, places_restantes=41)
    fixer("CT108", 1, light=800, places_restantes=37)         # Classic = 960 DT
    # Tunis -> Paris après-demain : CT108 annulé (P1003, T06), alternatives ouvertes
    fixer("CT100", 2, light=745, places_restantes=18)
    fixer("CT102", 2, light=760, places_restantes=9)
    fixer("CT104", 2, light=790, places_restantes=27)
    fixer("CT106", 2, light=750, places_restantes=35)
    fixer("CT108", 2, statut="annulé", places_restantes=0)
    # Djerba -> Paris (T05) : vol de J+3 réservé, vol du lendemain J+4 à 910 DT
    fixer("CT116", 3, light=860, places_restantes=14)
    fixer("CT116", 4, light=910, places_restantes=66)
    fixer("CT118", 4, light=940, places_restantes=31)          # plus cher : CT116 reste le bon choix
    # Tunis -> Istanbul aujourd'hui : retard de 130 min (P1005, T07)
    fixer("CT146", 0, statut="retardé", retard_minutes=130, places_restantes=8)
    # Autres vols démo ouverts
    fixer("CT105", 8, places_restantes=52)
    fixer("CT136", 5, places_restantes=47)
    fixer("CT156", 6, places_restantes=58)

    # Quelques retards et une annulation hors scénarios (réalisme)
    proteges = {("CT146", 0), ("CT108", 2), ("CT104", 1)}
    for numero in ("CT131", "CT120", "CT161"):
        if (numero, 0) not in proteges:
            vols[(numero, 0)].update(statut="retardé", retard_minutes=rng.choice([25, 40, 55]))
    vols[("CT141", 1)].update(statut="retardé", retard_minutes=35)
    vols[("CT170", 11)].update(statut="annulé", places_restantes=0)

    con.executemany(
        """INSERT INTO vols VALUES (:id,:numero,:date_depart,:heure_depart,:heure_arrivee,
           :origine,:destination,:statut,:retard_minutes,:capacite,:places_restantes,
           :prix_light,:prix_classic,:prix_flex,:prix_business)""",
        sorted(vols.values(), key=lambda v: v["id"]),
    )

    # --- Passagers ----------------------------------------------------------
    def email(prenom, nom):
        norm = lambda s: (s.lower().replace(" ", "").replace("é", "e")
                          .replace("ş", "s").replace("è", "e"))
        return f"{norm(prenom)}.{norm(nom)}@exemple.tn"

    lignes_pass = []
    for i, (pid, prenom, nom) in enumerate(PASSAGERS):
        tel = f"+216 {20 + i % 80:02d} {rng.randint(100, 999)} {rng.randint(100, 999)}"
        lignes_pass.append((pid, prenom, nom, email(prenom, nom), tel))
    con.executemany("INSERT INTO passagers VALUES (?,?,?,?,?)", lignes_pass)

    # --- Billets ------------------------------------------------------------
    billets = []
    sieges_pris = set()

    def ajouter(pid, numero, ecart, famille, siege, prix, statut="confirmé", achat=-20):
        v = vols[(numero, ecart)]
        sieges_pris.add((v["id"], siege))
        billets.append([pid, v["id"], famille, siege, prix, statut, jour(achat)])

    # Passagers de démonstration (cahier des charges, section 03 et EF-01)
    ajouter("P1001", "CT101", -2, "Classic", "14C", 820, "utilisé", -30)  # historique
    ajouter("P1001", "CT100", 1, "Classic", "11D", 880, achat=-25)
    ajouter("P1001", "CT105", 8, "Classic", "11D", 860, achat=-25)
    ajouter("P1002", "CT116", 3, "Light", "22C", 785, achat=-18)
    ajouter("P1003", "CT108", 2, "Classic", "9F", 730, achat=-21)          # vol annulé
    ajouter("P1004", "CT136", 5, "Flex", "3A", 775, achat=-15)
    ajouter("P1005", "CT146", 0, "Business", "2A", 1690, achat=-12)        # retard 130 min
    ajouter("P1006", "CT156", 6, "Light", "17B", 470, achat=-10)

    # Autres passagers : 1 à 3 billets aléatoires
    candidats = [k for k, v in vols.items() if v["statut"] != "annulé"]
    for pid, _, _ in PASSAGERS[6:]:
        for _ in range(rng.randint(1, 3)):
            numero, ecart = rng.choice(candidats)
            v = vols[(numero, ecart)]
            famille = rng.choices(FAMILLES, weights=[40, 35, 15, 10])[0]
            while True:
                rang = rng.randint(1, 4) if famille == "Business" else rng.randint(5, 30)
                siege = f"{rang}{rng.choice('ABCDEF')}"
                if (v["id"], siege) not in sieges_pris:
                    break
            prix_actuel = v[f"prix_{famille.lower()}"]
            prix = arrondi5(prix_actuel * rng.uniform(0.80, 1.0))
            if ecart < 0:
                statut = "utilisé"
            else:
                statut = "annulé" if rng.random() < 0.1 else "confirmé"
            ajouter(pid, numero, ecart, famille, siege, prix, statut,
                    achat=min(ecart, 0) - rng.randint(5, 45))

    con.executemany(
        "INSERT INTO billets VALUES (?,?,?,?,?,?,?,?)",
        [[f"B{i:06d}"] + b for i, b in enumerate(billets, start=1)],
    )
    con.commit()

    verifier(con, jour)
    con.close()


# ---------------------------------------------------------------------------
# Vérifications : la base doit reproduire les valeurs du cahier des charges
# ---------------------------------------------------------------------------
def verifier(con: sqlite3.Connection, jour) -> None:
    q = lambda sql, *a: con.execute(sql, a).fetchall()
    assert q("SELECT COUNT(*) FROM aeroports")[0][0] == 12
    assert q("SELECT COUNT(*) FROM vols")[0][0] == 1156
    assert q("SELECT COUNT(*) FROM passagers")[0][0] == 40

    # EF-01 : billets confirmés de P1001
    r = q("""SELECT v.numero, v.date_depart, v.heure_depart, b.famille, b.siege, b.prix_paye
             FROM billets b JOIN vols v ON v.id = b.vol_id
             WHERE b.passager_id = 'P1001' AND b.statut = 'confirmé'
             ORDER BY v.date_depart""")
    assert r == [("CT100", jour(1), "07:15", "Classic", "11D", 880),
                 ("CT105", jour(8), "14:50", "Classic", "11D", 860)], r

    # EF-02 : Tunis -> Paris demain
    r = q("""SELECT v.heure_depart, v.destination, v.places_restantes
             FROM vols v JOIN aeroports o ON o.code = v.origine
                         JOIN aeroports d ON d.code = v.destination
             WHERE o.ville = 'Tunis' AND d.ville = 'Paris' AND v.date_depart = ?
             ORDER BY v.heure_depart""", jour(1))
    assert [(h, a) for h, a, _ in r] == [("07:15", "CDG"), ("09:00", "ORY"), ("11:30", "CDG"),
                                          ("16:45", "CDG"), ("18:10", "ORY")], r
    assert r[2][2] == 0 and all(p > 0 for h, _, p in r if h != "11:30"), r

    # T03 : Classic du 18:10 demain = 960 DT ; T05 : CT116 J+4 Light 910, 66 places
    assert q("SELECT prix_classic FROM vols WHERE numero='CT108' AND date_depart=?", jour(1))[0][0] == 960
    assert q("SELECT prix_light, places_restantes FROM vols WHERE numero='CT116' AND date_depart=?",
             jour(4))[0] == (910, 66)
    assert q("SELECT statut FROM vols WHERE numero='CT108' AND date_depart=?", jour(2))[0][0] == "annulé"
    assert q("SELECT statut, retard_minutes FROM vols WHERE numero='CT146' AND date_depart=?",
             jour(0))[0] == ("retardé", 130)

    nb_billets = q("SELECT COUNT(*) FROM billets")[0][0]
    print(f"Base générée : {CHEMIN_BASE.name}")
    print(f"  date de génération (J) : {jour(0)}")
    print(f"  12 aéroports, 1156 vols ({jour(JOUR_DEBUT)} -> {jour(JOUR_FIN)}), "
          f"40 passagers, {nb_billets} billets")
    print("  Vérifications du cahier des charges : OK")


if __name__ == "__main__":
    generer()
