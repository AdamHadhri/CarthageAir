from datetime import date, timedelta
from outils import (
    set_passager,
    rechercher_politique,
    consulter_mes_vols,
    rechercher_vols,
    meteo_destination,
    calculer_cout_modification,
)

# --- CHECKPOINT 1 : RAG ---
question = "poids valise soute"
resultat = rechercher_politique.invoke({"question": question})

print("=== Checkpoint 1 : rechercher_politique ===")
print(resultat)
assert "32 kg" in resultat, "Checkpoint 1 failed: 32 kg not found."
assert "5. Bagages" in resultat, "Checkpoint 1 failed: Section 5 not found."
print("Checkpoint 1: PASSED\n")

# --- CHECKPOINT 2 : SQL ---
demain = (date.today() + timedelta(days=1)).isoformat()
set_passager("P1001")

print("=== Checkpoint 2 : consulter_mes_vols (P1001) ===")
mes_vols = consulter_mes_vols.invoke({})
print(mes_vols)
assert "CT100" in mes_vols and "880 DT" in mes_vols, "Checkpoint 2 failed on P1001 tickets."

print(f"\n=== Checkpoint 2 : rechercher_vols (Tunis -> Paris le {demain}) ===")
vols_demain = rechercher_vols.invoke({
    "ville_depart": "Tunis",
    "ville_arrivee": "Paris",
    "date": demain,
})
print(vols_demain)
assert "COMPLET" in vols_demain, "Checkpoint 2 failed: full flight not flagged."
print("Checkpoint 2: PASSED\n")

# --- CHECKPOINT 3 : CALCUL & API ---
print("=== Checkpoint 3 : calculer_cout_modification (T05) ===")
cout = calculer_cout_modification.invoke({
    "famille": "Light",
    "prix_paye": 785,
    "nouveau_prix": 910,
})
print(cout)
assert "205 DT" in cout, "Checkpoint 3 failed: expected 205 DT."

print(f"\n=== Checkpoint 3 : meteo_destination (Paris le {demain}) ===")
meteo = meteo_destination.invoke({"ville": "Paris", "date": demain})
print(meteo)
print("Checkpoint 3: PASSED")