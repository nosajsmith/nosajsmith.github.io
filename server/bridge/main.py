import argparse
import json
from collections import defaultdict
from extractor import MWEExtractor
from rule_engine import load_rules, evaluate_rules
from order_system import OrderDispatcher
from order_persistence import OrderStorage
from order_execution import OrderExecutor
from staff_assistant import StaffAssistant
from game_state import GameState
from scenario_loader import load_units_from_file

parser = argparse.ArgumentParser()
parser.add_argument("--auto-approve", action="store_true")
parser.add_argument("--turn", type=int, default=0)
parser.add_argument("--scenario", type=str, default="scenario.json")
args = parser.parse_args()

turn = args.turn
extractor = MWEExtractor()
rules = load_rules("rules/fallback_rules.yaml")
order_dispatcher = OrderDispatcher()
staff = StaffAssistant(auto_approve=args.auto_approve)

game_state = GameState()
units = load_units_from_file(args.scenario)
for unit in units:
    game_state.add_unit(unit)

executor = OrderExecutor(game_state)

sentence = "The exhausted unit was ordered to fall back from the ridge."
spans = []

for span in extractor.extract(sentence):
    d = span.duration_data.copy()
    d["sentence"] = sentence
    recs = evaluate_rules(rules, {
        "fatigue": 75, "supply": 35, "flanked": True,
        "days_in_combat": 4, "casualties": 20
    }, triggered_mwes=["unit exhausted"])
    d["recommendations"] = [r["text"] for r in recs]
    staff.review_recommendations("2DIV", recs, turn, order_dispatcher)
    spans.append(d)

executor.execute_orders(order_dispatcher)
OrderStorage(f"orders_turn{turn}.json").save(order_dispatcher.active_orders)

with open(f"staff_log_turn{turn}.json", "w", encoding="utf-8") as f:
    json.dump(staff.log, f, indent=2)

def render_orders_html(orders):
    html = "<h2>📋 Active Orders</h2><ul>"
    for o in orders:
        icon = "🧍" if o.priority == "manual" else "🤖"
        html += (
            f"<li>{icon} <b>{o.unit_id}</b> → <b>{o.action.upper()}</b> "
            f"({o.status}, Priority: {o.priority})<br><i>{o.reason}</i></li>"
        )
    html += "</ul>"
    return html

def save_outputs(spans, output_prefix):
    html_path = f"{output_prefix}.html"
    grouped = defaultdict(list)
    for span in spans:
        typ = span.get("type", "unknown")
        grouped[typ].append(span)

    with open(html_path, "w", encoding="utf-8") as f_html:
        f_html.write("<html><head><style>mark { background: lightblue; }</style></head><body>")
        f_html.write("<h2>MWE Results</h2>")
        for typ, span_list in grouped.items():
            f_html.write(f"<h3>{typ}</h3><ul>")
            for span in span_list:
                tokens = span.get("span_tokens", ["?"])
                confidence = span.get("confidence", "?")
                sentence = span.get("sentence", "[No sentence]")
                f_html.write(
                    f"<li><b>{', '.join(tokens)}</b> → {confidence}<br><i>{sentence}</i></li>"
                )
            f_html.write("</ul>")
        if order_dispatcher.active_orders:
            f_html.write(render_orders_html(order_dispatcher.active_orders))
        f_html.write("</body></html>")

save_outputs(spans, f"turn_{turn}_report")
