from rule_engine import load_rules, evaluate_rules

unit_state = {
    "fatigue": 72,
    "supply": 35,
    "flanked": True,
    "days_in_combat": 4,
    "casualties": 23
}

mwes = ["enemy breakthrough", "unit exhausted"]
rules = load_rules("rules/fallback_rules.yaml")
recommendations = evaluate_rules(rules, unit_state, mwes)

for r in recommendations:
    print(f"[AI Suggestion] {r['text']} → {r['action'].upper()}")
