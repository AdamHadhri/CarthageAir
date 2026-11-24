import json
from agent import poser_question

with open("scenarios_test.json", encoding="utf-8") as f:
    data = json.load(f)

scenarios = data if isinstance(data, list) else data.get("scenarios", [])

print(f"{'ID':<5} | {'Passager':<8} | {'Outils appelés'}")
print("-" * 70)

for sc in scenarios:
    sid = sc["id"]
    passager = sc["passager"] or "P1001"
    label_passager = sc["passager"] or "tous"
    question = sc["question"]

    msgs = poser_question(passager, question)

    outils_appeles = []
    reponse = ""
    for m in msgs:
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                outils_appeles.append(tc["name"])
        elif getattr(m, "type", "") == "ai" and m.content:
            reponse = m.content
        elif isinstance(m, dict) and m.get("role") == "assistant":
            reponse = m.get("content", "")

    print(f"{sid:<5} | {label_passager:<8} | {', '.join(outils_appeles) or 'aucun'}")
    print(f"   Q: {question}")
    print(f"   R: {reponse}\n")