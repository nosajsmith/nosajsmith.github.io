import yaml
from pathlib import Path
import operator

# Define how we interpret condition operators
OPERATORS = {
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '==': operator.eq
}

def parse_condition(expression):
    for symbol in [">=", "<=", ">", "<", "=="]:
        if symbol in expression:
            value = float(expression.replace(symbol, '').strip())
            return OPERATORS[symbol], value
    raise ValueError(f"Invalid expression: {expression}")

def load_rules(rule_path):
    with open(rule_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def evaluate_conditions(conditions, unit_state):
    for key, expected in conditions.items():
        if isinstance(expected, bool):
            if unit_state.get(key) != expected:
                return False
        elif isinstance(expected, str):
            op, val = parse_condition(expected)
            if key not in unit_state:
                return False
            if not op(unit_state[key], val):
                return False
    return True

def evaluate_rules(rules, unit_state, triggered_mwes=[]):
    recommendations = []
    for rule in rules:
        if rule.get("trigger") and rule["trigger"] not in triggered_mwes:
            continue
        if evaluate_conditions(rule["conditions"], unit_state):
            recommendations.append({
                "name": rule["name"],
                "action": rule["action"],
                "text": rule.get("recommendation_text", rule["action"]),
                "priority": rule.get("priority", "normal"),
                "matched_rule": rule
            })
    return recommendations
