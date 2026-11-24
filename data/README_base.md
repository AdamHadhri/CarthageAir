# Base de test Carthage Air — `carthage_air.sqlite`

## Régénérer la base (avant chaque séance)

```bash
uv run data/generer_base.py
```

Les dates sont **relatives au jour de génération** : J = aujourd'hui, J+1 = demain.
Les vols couvrent la période de J-3 à J+30. La génération est déterministe : la même
date donne exactement la même base. Le script vérifie lui-même les valeurs du cahier
des charges et affiche « Vérifications : OK ».

## Contenu

| Table | Lignes | Rôle |
|---|---|---|
| `aeroports` | 12 | Code IATA, nom, **ville**, pays (Paris = CDG et ORY) |
| `vols` | 1 156 | 34 vols par jour × 34 jours : horaires, statut, places, prix actuels par famille |
| `passagers` | 40 | P1001 à P1040 (P1001 à P1006 = passagers de démonstration) |
| `billets` | 76 | Billets des passagers : famille, siège, prix payé, statut |
| `meta` | 2 | Date de génération et fenêtre des vols |

## Schéma

```
aeroports(code PK, nom, ville, pays)

vols(id PK, numero, date_depart 'AAAA-MM-JJ', heure_depart 'HH:MM', heure_arrivee,
     origine FK→aeroports, destination FK→aeroports,
     statut ∈ {prévu, retardé, annulé, effectué}, retard_minutes,
     capacite, places_restantes,
     prix_light, prix_classic, prix_flex, prix_business)      -- prix actuels en DT
     UNIQUE(numero, date_depart)

passagers(id PK, prenom, nom, email, telephone)

billets(id PK, passager_id FK, vol_id FK,
        famille ∈ {Light, Classic, Flex, Business}, siege, prix_paye,
        statut ∈ {confirmé, annulé, utilisé}, date_achat)
```

Points d'attention pour les outils :

- Un **vol** est un numéro *à une date* : CT108 existe tous les jours, mais il est annulé seulement à J+2.
- `rechercher_vols` reçoit des **villes** : il faut faire la jointure `aeroports.ville` → codes (Paris → CDG + ORY).
- `consulter_mes_vols` ne retourne que les billets `statut = 'confirmé'`. P1001 a aussi un billet `utilisé` (J-2) qui ne doit pas apparaître.
- Un billet confirmé peut porter sur un vol `annulé` (cas de P1003) : il faut afficher le statut du **vol**.
- Un vol complet a `places_restantes = 0`.

## Passagers de démonstration

| Passager | Billet(s) confirmé(s) | Situation |
|---|---|---|
| P1001 Amine Trabelsi | CT100 TUN→CDG J+1 07:15, Classic, siège 11D, 880 DT ; CT105 CDG→TUN J+8 14:50, Classic, 860 DT | Le vol de 11:30 demain est complet |
| P1002 Salma Ben Ali | CT116 DJE→CDG J+3 08:40, Light, 22C, 785 DT | CT116 à J+4 : 66 places, Light 910 DT |
| P1003 Youssef Gharbi | CT108 TUN→ORY J+2 18:10, Classic, 9F, 730 DT | Vol **annulé** par la compagnie |
| P1004 Léa Martin | CT136 LYS→MIR J+5 13:05, Flex, 3A, 775 DT | — |
| P1005 Karim Jaziri | CT146 TUN→IST J 15:40, Business, 2A, 1 690 DT | **Retardé de 130 min** |
| P1006 Nour Hammami | CT156 TUN→FCO J+6 10:05, Light, 17B, 470 DT | Sert au test de sécurité T11 |

## Vols Tunis → Paris à J+1 (EF-02, T02, T03)

| Vol | Départ | Arrivée | Places | Light | Classic | Flex |
|---|---|---|---|---|---|---|
| CT100 | 07:15 | CDG 09:30 | 12 | 760 | 910 | 1 100 |
| CT102 | 09:00 | ORY 11:15 | 23 | 780 | 935 | 1 130 |
| CT104 | 11:30 | CDG 13:45 | **0 (complet)** | 820 | 985 | 1 190 |
| CT106 | 16:45 | CDG 19:00 | 41 | 770 | 925 | 1 115 |
| CT108 | 18:10 | ORY 20:25 | 37 | 800 | **960** | 1 160 |

## Lot 0 : trois requêtes de prise en main

```sql
-- 1. Billets confirmés de P1001 → CT100 (J+1, 11D, 880 DT) et CT105 (J+8)
SELECT v.numero, v.date_depart, v.heure_depart, v.origine, v.destination,
       b.famille, b.siege, b.prix_paye
FROM billets b JOIN vols v ON v.id = b.vol_id
WHERE b.passager_id = 'P1001' AND b.statut = 'confirmé'
ORDER BY v.date_depart;

-- 2. Vols Tunis → Paris demain → 5 vols, celui de 11:30 est complet
SELECT v.numero, v.heure_depart, v.destination, v.statut, v.places_restantes,
       v.prix_light, v.prix_classic, v.prix_flex
FROM vols v
JOIN aeroports o ON o.code = v.origine
JOIN aeroports d ON d.code = v.destination
WHERE o.ville = 'Tunis' AND d.ville = 'Paris' AND v.date_depart = date('now', '+1 day')
ORDER BY v.heure_depart;

-- 3. Vols annulés ou retardés à venir → CT146 (J, +130 min), CT108 (J+2, annulé)…
SELECT numero, date_depart, heure_depart, origine, destination, statut, retard_minutes
FROM vols
WHERE statut IN ('annulé', 'retardé') AND date_depart >= date('now')
ORDER BY date_depart, heure_depart;
```

> `date('now')` de SQLite utilise l'heure UTC. En Tunisie (UTC+1), il y a un décalage
> entre minuit et 1 h du matin. Dans les outils Python, passez plutôt la date
> calculée avec `date.today()`.
