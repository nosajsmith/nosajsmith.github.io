# turn_engine.py — WEGO turn engine with supply, planner validator, overlays, HQ delays + HQ overlay pass-through
from __future__ import annotations
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='replace')

import json, csv
from collections import defaultdict
from typing import Dict, Any, List

from extractor import MWEExtractor
from rule_engine import load_rules, evaluate_rules
from staff_assistant import StaffAssistant
from order_system import OrderDispatcher
from order_persistence import OrderStorage
from order_execution import OrderExecutor
from scenario_loader import load_units_from_file
from game_state import GameState
from event_engine import EventEngine
from combat_engine import CombatEngine
from map_overlay import MapOverlay
from objective_engine import ObjectiveEngine
from supply_model import SupplyEngine
from hq_refit import RefitEngine
from terrain import TerrainMap
from morale import apply_post_combat_effects, rally_phase
from output_manager import OutputManager
from battle_metrics import METRICS
from plan_validator import validate_plans
from hq_hierarchy import CommandNetwork  # HQ delays network

try:
    from economy import ConvoyEngine
except Exception:
    ConvoyEngine = None

try:
    from ai_planner import AIPlanner, AIConfig
except Exception:
    AIPlanner = None
    AIConfig = None


def _load_game_config(path: str = "game_config.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"resolution_mode": "WEGO", "slices_per_turn": 3, "enable_op_fire": True}


class TurnEngine:
    def __init__(self, scenario_path="scenario.json", rules_path="rules/fallback_rules.yaml", auto_approve=True):
        self.turn = 0
        self.scenario_path = scenario_path
        self.rules_path = rules_path
        self.auto_approve = auto_approve
        self.config = _load_game_config()

        self.out = OutputManager(root=".", base_dir="runs")

        self.extractor = MWEExtractor()
        self.rules = load_rules(rules_path)
        self.staff = StaffAssistant(auto_approve=auto_approve)
        self.dispatcher = OrderDispatcher()
        self.game_state = GameState()
        self.executor = OrderExecutor(self.game_state, config=self.config)
        self.events = EventEngine(self.game_state, path="events.json")

        self.terrain = TerrainMap(path="terrain.json")
        self.combat = CombatEngine(self.game_state, terrain=self.terrain)

        self.overlay = MapOverlay(grid_size=(20, 20), cell_px=28, out_dir=".")
        self.objectives = ObjectiveEngine(self.game_state, path="objectives.json", state_path="objectives_state.json")

        self.supply = SupplyEngine(path="supply_routes.json")
        self.game_state.supply_engine = self.supply
        self.refit = RefitEngine(pool_path="hq_pools.json")
        self.economy = ConvoyEngine(pool_path="hq_pools.json", config_path="convoys.json", log_dir=".") if ConvoyEngine else None

        # HQ Command Network (delays)
        self.hq = CommandNetwork(path="hq_network.json")
        self._held_orders: List[Any] = []  # persist held orders across turns

        self.ai = None
        if AIPlanner and AIConfig:
            self.ai = AIPlanner(
                self.game_state, self.dispatcher, self.supply, self.objectives,
                AIConfig(side="RED", lane_width=6, group_size=2, min_attack_odds=1.25,
                         regroup_fatigue=70, regroup_supply=30.0, protect_routes=True)
            )

        self.load_scenario()
        self._morale_events_buffer = []
        self._timeline_buffer = []

    def load_scenario(self):
        for u in load_units_from_file(self.scenario_path):
            self.game_state.add_unit(u)

    def process_sentence(self, sentence: str, unit_id: str = "2DIV"):
        spans = []
        for span in self.extractor.extract(sentence):
            d = span.duration_data.copy(); d["sentence"] = sentence
            context = {"fatigue": 75, "supply": 35, "flanked": True, "days_in_combat": 4, "casualties": 20}
            recs = evaluate_rules(self.rules, context, triggered_mwes=["unit exhausted"])
            d["recommendations"] = [r["text"] for r in recs]
            self.staff.review_recommendations(unit_id, recs, self.turn, self.dispatcher)
            spans.append(d)
        return spans

    def _auto_advance_for_non_adjacent_attacks(self):
        injected = 0
        for o in list(self.dispatcher.active_orders):
            if o.status != "pending" or o.action != "attack": continue
            atk = self.game_state.get_unit(o.unit_id); dfn = self.game_state.get_unit(o.target_id)
            if not atk or not dfn: continue
            if not self.game_state.is_adjacent(tuple(atk.position), tuple(dfn.position)):
                step = self.game_state.next_step_towards(tuple(atk.position), tuple(dfn.position))
                self.dispatcher.dispatch_from_recommendations(o.unit_id, [{
                    "action":"move_to","text":f"Advance toward {o.target_id} for attack.","priority":"high","target_xy": step
                }], self.turn)
                injected += 1
        if injected: print(f"[Auto-Advance] Injected {injected} advance move(s) for non-adjacent attacks.")

    def _load_phase_filter(self):
        try:
            d = json.load(open("plan_view.json", "r", encoding="utf-8"))
            pf = d.get("phase_filter")
            if isinstance(pf, list) and all(isinstance(x, int) for x in pf): return pf
        except Exception:
            pass
        return None

    def run_turn(self, sentence: str | None):
        print(f"\n=== TURN {self.turn} ===")
        self.overlay.out_dir = str(self.out.turn_dir(self.turn))

        spans = self.process_sentence(sentence) if sentence else []

        # 0) Merge previously held orders so they can be reconsidered
        if self._held_orders:
            self.dispatcher.active_orders.extend(self._held_orders)
            self._held_orders = []

        # 1) Supply
        supply_summary = self.supply.resolve_and_apply(self.game_state)

        # 2) Economy
        convoy_log = {"delivered": [], "lost": [], "skipped": [], "pools": {}}
        if self.economy:
            convoy_log = self.economy.resolve_for_turn(self.turn, supply_summary)

        # 3) AI
        if self.ai:
            ai_summary = self.ai.plan_turn(self.turn)
            if ai_summary.get("orders"): print(f"[AI] Issued {ai_summary['orders']} order(s).")

        # 4) Auto-advance injection
        self._auto_advance_for_non_adjacent_attacks()

        # 5) HQ DELAYS — compute release_turn and split ready vs held
        ready, held, hq_timeline = self.hq.apply_delays(self.dispatcher.active_orders, self.game_state, self.turn)
        self._held_orders = held
        self.dispatcher.active_orders = ready

        # 6) Combat
        self.combat.set_terrain(self.terrain)
        battle_results = self.combat.resolve_attacks_from_orders(self.dispatcher.active_orders)
        if battle_results: self._save_combat_results(battle_results)

        # 7) Morale post-combat
        morale_events = apply_post_combat_effects(self.game_state, battle_results or [], self.turn)
        self._morale_events_buffer = morale_events

        # 8) HQ Refit
        refit_results = self.refit.apply(self.dispatcher, self.game_state, self.supply)

        # 9) Execute remaining
        timeline_exec = self.executor.execute_orders(self.dispatcher, config=self.config)
        self._timeline_buffer = hq_timeline + (timeline_exec or [])
        self.save_orders(); self.save_staff_log()

        # 10) Rally
        rally_events = rally_phase(self.game_state, self.supply, self.turn)
        self._morale_events_buffer.extend(rally_events)

        # 11) Events & Objectives
        self.events.run_for_turn(self.turn)
        obj_info = self.objectives.evaluate(self.turn, supply_state=supply_summary)

        # 12) Overlays + Plans + HQ overlay data
        plans = MapOverlay.load_plans("plans.json")
        supply_overlay = {
            "depots":[{"id":d.id,"name":d.name,"pos":list(d.pos)} for d in self.supply.state.depots],
            "routes":[{"id":r.id,"name":r.name,"side":r.side,
                       "status": ("cut" if r.damage >= 100 or r.status=='cut' else r.status),
                       "capacity":r.capacity,"effective":round(r.effective_throughput(),1),
                       "damage": round(r.damage,1),
                       "cut_turns": r.cut_turns,
                       "path":[list(p) for p in r.path]} for r in self.supply.state.routes]
        }
        terrain_overlay = {"tiles":[{"pos":list(k),"type":v} for k,v in self.terrain.tiles.items()],
                           "roads":[[list(p) for p in line] for line in self.terrain.roads]}
        obj_pins=[]; obj_status={}
        for o in obj_info["all"]:
            obj_status[o["id"]] = o.get("status","pending")
            if o["type"] in ("hold_hex","occupy_by"):
                obj_pins.append({"id": o["id"], "title": o["title"], "status": o["status"], "pos": o["params"]["pos"]})
            elif o["type"] == "route_state":
                rid = o["params"]["route_id"]
                for r in supply_overlay["routes"]:
                    if r["id"]==rid and r["path"]:
                        obj_pins.append({"id":o["id"],"title":o["title"],"status":o["status"],"pos":r["path"][0]})
                        break
        phase_filter = self._load_phase_filter()

        # Build HQ overlay payload
        # Count held orders per HQ and compile list of held unit IDs for badges
        held_units = [o.unit_id for o in self._held_orders]
        hq_counts = {hid:0 for hid in self.hq.hqs.keys()}
        for o in self._held_orders:
            u = self.game_state.get_unit(o.unit_id)
            if not u: continue
            h = self.hq._hq_for_unit(u)
            hq_counts[h.id] = hq_counts.get(h.id, 0) + 1

        hq_overlay = []
        for hid, h in self.hq.hqs.items():
            hq_overlay.append({
                "id": h.id,
                "side": h.side,
                "initiative": h.initiative,
                "staff_capacity": h.staff_capacity,
                "pos": list(h.pos),
                "held_count": int(hq_counts.get(h.id, 0)),
            })

        ascii_path=self.overlay.render_ascii(self.turn, self.game_state.all_units())
        html_map_path=self.overlay.render_html(
            self.turn, self.game_state.all_units(),
            plans=plans, supply=supply_overlay, terrain=terrain_overlay,
            objectives=obj_pins, phase_filter=phase_filter,
            objectives_status=obj_status, snap_to_roads=True, hexes_per_turn=1.0,
            hqs=hq_overlay, held_units=held_units
        )
        print(f"[✓] Overlay: {ascii_path} / {html_map_path}")
        print(f"[✓] Objectives: {obj_info['path']} (score={obj_info['score']})")

        # 13) Plan Validator
        plan_warnings = validate_plans(plans or {}, self.game_state, objectives_state=obj_info,
                                       hexes_per_turn=1.0, supply_summary=supply_summary)

        # 14) Exports
        self.export_html(spans, battle_results, obj_info, supply_summary,
                         refit_results, convoy_log, self._morale_events_buffer,
                         self._timeline_buffer, plan_warnings)
        self.export_units_csv()

    def _save_combat_results(self, results):
        path = self.out.path(self.turn, f"combat_results_turn{self.turn}.json")
        payload=[]
        for r in results:
            payload.append({"attackers":r.attackers,"defender_id":r.defender_id,"outcome":r.outcome,
                            "atk_strength":r.atk_strength,"def_strength":r.def_strength,
                            "atk_losses":r.atk_losses,"def_losses":r.def_losses,"notes":r.notes})
        with open(path,"w",encoding="utf-8") as f: json.dump(payload,f,indent=2,ensure_ascii=False)
        print(f"[✓] Saved combat log: {path}")

    def save_orders(self):
        path = self.out.path(self.turn, f"orders_turn{self.turn}.json")
        # save both ready and held so we can reconstruct state
        OrderStorage(str(path)).save(self.dispatcher.active_orders + self._held_orders)

    def save_staff_log(self):
        path = self.out.path(self.turn, f"staff_log_turn{self.turn}.json")
        with open(path,"w",encoding="utf-8") as f: json.dump(self.staff.log,f,indent=2,ensure_ascii=False)

    def export_html(self, spans, battle_results, obj_info, supply_summary, refit_results,
                    convoy_log, morale_events, timeline, plan_warnings):
        grouped=defaultdict(list)
        for s in spans: grouped[s.get("type","unknown")].append(s)
        path = self.out.path(self.turn, f"turn_{self.turn}_report.html")
        with open(path,"w",encoding="utf-8") as f:
            f.write("<html><head><meta charset='utf-8'/>"
                    "<style>mark{background:lightblue} body{font-family:system-ui,Segoe UI,Roboto,Arial}"
                    " table{border-collapse:collapse} td,th{padding:6px 8px;border:1px solid #ddd}"
                    " .pill{display:inline-block;padding:2px 8px;border-radius:10px;background:#eee;margin-left:6px;font-size:12px;color:#555}"
                    " .warn{color:#b26b00} .err{color:#b00020} .ok{color:#2c7}</style></head><body>")
            f.write("<h2>MWE Results</h2>")
            for typ, arr in grouped.items():
                f.write(f"<h3>{typ}</h3><ul>")
                for span in arr:
                    toks=span.get("span_tokens",["?"]); conf=span.get("confidence","?"); sent=span.get("sentence","[No sentence]")
                    f.write(f"<li><b>{', '.join(toks)}</b> → {conf}<br><i>{sent}</i></li>")
                f.write("</ul>")

            if battle_results:
                f.write("<h2>⚔️ Combat Results</h2><ul>")
                for r in battle_results:
                    f.write(f"<li><b>{', '.join(r.attackers)}</b> vs <b>{r.defender_id}</b> → <b>{r.outcome}</b> "
                            f"(ATK {r.atk_strength} / DEF {r.def_strength}) Losses A:{r.atk_losses} D:{r.def_losses} "
                            f"<i>{r.notes}</i></li>")
                f.write("</ul>")

            f.write("<h2>⏱️ Turn Timeline</h2>")
            if timeline:
                f.write("<table><thead><tr><th>Step</th></tr></thead><tbody>")
                for line in timeline: f.write(f"<tr><td>{line}</td></tr>")
                f.write("</tbody></table>")
            else:
                f.write("<p>No timeline events.</p>")

            f.write("<h2>🧠 Morale & Cohesion</h2>")
            if morale_events:
                f.write("<table><thead><tr><th>Unit</th><th>Event</th><th>Detail</th></tr></thead><tbody>")
                for ev in morale_events:
                    f.write(f"<tr><td>{ev.unit_id}</td><td>{ev.kind}</td><td>{ev.note}</td></tr>")
                f.write("</tbody></table>")
            else:
                f.write("<p>No morale events this turn.</p>")

            f.write("<h2>🛢️ Supply</h2>")
            f.write("<table><thead><tr><th>Route</th><th>Side</th><th>Status</th><th>Dmg%</th><th>Cap</th><th>Len</th><th>Effective</th></tr></thead><tbody>")
            for r in supply_summary["routes"]:
                f.write(f"<tr><td>{r['name']} ({r['id']})</td><td>{r['side']}</td><td>{r['status']}</td>"
                        f"<td>{r.get('damage','?')}</td><td>{r['capacity']}</td><td>{r['length']}</td><td>{r['effective']}</td></tr>")
            f.write("</tbody></table>")

            if convoy_log and any(convoy_log.get(k) for k in ("delivered","lost","skipped","pools")):
                f.write("<h2>🚚 Convoys</h2>")
                if convoy_log["delivered"]:
                    f.write("<h3>Arrived</h3><ul>")
                    for c in convoy_log["delivered"]:
                        f.write(f"<li>{c['name']} via {c['route']} — {c['delivered']} (ratio {round(c['ratio'],2)})</li>")
                    f.write("</ul>")
                if convoy_log["lost"]:
                    f.write("<h3>Lost / Interdicted</h3><ul>")
                    for c in convoy_log["lost"]:
                        f.write(f"<li>{c['name']} via {c['route']} — status={c['status']} (loss p={c['loss_chance']})</li>")
                    f.write("</ul>")
                if convoy_log["skipped"]:
                    f.write("<h3>Skipped</h3><ul>")
                    for c in convoy_log["skipped"]:
                        f.write(f"<li>{c['name']} ({c['id']}) — {c.get('reason','?')}</li>")
                    f.write("</ul>")
                if convoy_log.get("pools"):
                    f.write("<h3>HQ Pools</h3><table><thead><tr><th>Side</th><th>Inf</th><th>Armor</th><th>Supplies</th></tr></thead><tbody>")
                    for side, pool in convoy_log["pools"].items():
                        f.write(f"<tr><td>{side}</td><td>{pool.get('infantry',0)}</td><td>{pool.get('armor',0)}</td><td>{pool.get('supplies',0)}</td></tr>")
                    f.write("</tbody></table>")

            from hq_refit import RefitEngine as _RE
            f.write("<h2>🧰 HQ Refit</h2>"+ _RE.summary_table(refit_results))

            f.write("<h2>🎯 Objectives</h2>")
            f.write(f"<p><b>Score:</b> {obj_info['score']}</p><ul>")
            for o in obj_info["all"]:
                badge="✅" if o.get("status")=="secured" else ("❌" if o.get("status")=="failed" else "⏳")
                title=o.get("title",o["id"]); desc=o.get("desc","")
                f.write(f"<li>{badge} <b>{title}</b> – {desc}</li>")
            f.write("</ul>")

            ms = METRICS.summary()
            f.write("<h2>📊 Combat Metrics</h2>")
            f.write(f"<p>Attacks: {ms['attacks_total']} &middot; Coordinated (≥2 attackers): {ms['attacks_coordinated']} "
                    f"&middot; Avg odds: {ms['avg_attack_odds']} &middot; Loss ratio (A/D): {ms['loss_ratio']}</p>")

            f.write("<h2>🧭 Plan Validator</h2>")
            if plan_warnings:
                f.write("<ul>")
                for w in plan_warnings:
                    cls = "err" if w["level"] == "error" else "warn"
                    unit = f"{w.get('unit')}: " if w.get('unit') else ""
                    f.write(f"<li class='{cls}'><b>{w['level'].upper()}</b> {unit}{w['msg']}</li>")
                f.write("</ul>")
            else:
                f.write("<p class='ok'>No planner warnings.</p>")

            f.write("<h2>🗺️ Map</h2><p><a href='map_turn{0}.html'>Open Map Overlay</a></p>".format(self.turn))
            f.write("</body></html>")
        print(f"[✓] Exported HTML: {path}")

    def export_units_csv(self):
        path = self.out.path(self.turn, f"unit_status_turn{self.turn}.csv")
        with open(path,"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f)
            w.writerow(["unit_id","name","x","y","fatigue","supply","entrenchment","exposure","stance",
                        "suppressed_turns","side","morale","cohesion","shaken","routed"])
            for u in self.game_state.all_units():
                x,y=u.position
                w.writerow([u.unit_id,u.name,x,y,u.fatigue,u.supply,u.entrenchment,u.exposure,
                            getattr(u,"stance","-"),getattr(u,"suppressed_turns",0),u.side,
                            getattr(u,"morale",70), getattr(u,"cohesion",70),
                            int(getattr(u,"shaken",False)), int(getattr(u,"routed",False))])
        print(f"[✓] Exported CSV: {path}")

    def advance_turn(self):
        self.turn+=1
        self.game_state.advance_turn()
        # keep held orders; clear transient logs and ready orders
        self.staff.log=[]
        self.dispatcher.active_orders=[]
