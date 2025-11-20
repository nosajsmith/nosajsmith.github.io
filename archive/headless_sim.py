# headless_sim.py — headless runner with UTF-8-safe printing and tidy session folders
from __future__ import annotations
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='replace')

import argparse, json, csv, os, random
from pathlib import Path
from turn_engine import TurnEngine
from session_manager import SessionManager

def resolve_scenario_path(scen: str) -> str:
    p = Path(scen)
    if p.suffix.lower() == ".json" and p.exists():
        return str(p)
    try:
        pack = json.load(open("scenario_pack.json","r",encoding="utf-8"))
        if scen in pack:
            return pack[scen]["path"]
    except Exception:
        pass
    return "scenario.json"

def summarize_supply(engine: TurnEngine) -> dict:
    try:
        st = engine.supply.state
        routes = []
        active = 0
        for r in st.routes:
            eff = round(r.effective_throughput(), 3)
            routes.append({"id": r.id, "side": r.side, "status": r.status, "effective": eff})
            if r.status == "active":
                active += 1
        uptime = active / max(1, len(st.routes))
        return {"routes": routes, "route_uptime": round(uptime, 3)}
    except Exception:
        return {"routes": [], "route_uptime": 0.0}

def compute_kpis(engine: TurnEngine, turns: int) -> tuple[dict, dict, dict]:
    obj_eval = engine.objectives.evaluate(engine.turn)
    supply = summarize_supply(engine)
    kpis = {
        "scenario": getattr(engine, "scenario_path", "scenario.json"),
        "turns": turns,
        "score": obj_eval.get("score", 0),
        "objectives_total": len(obj_eval.get("all", [])),
        "objectives_secured": len([o for o in obj_eval.get("all", []) if o.get("status") == "secured"]),
        "objectives_failed": len([o for o in obj_eval.get("all", []) if o.get("status") == "failed"]),
        "route_uptime": supply.get("route_uptime", 0.0),
        "blue_losses": 0,
        "red_losses": 0
    }
    return kpis, supply, obj_eval

def write_kpi_report(session_dir: Path, kpis: dict, supply: dict, obj_eval: dict):
    html = []
    html.append("<html><head><meta charset='utf-8'><style>body{font-family:system-ui} table{border-collapse:collapse} td,th{padding:6px 10px;border:1px solid #ddd}</style></head><body>")
    html.append("<h2>Headless KPI Report</h2><table><tbody>")
    for k in ("scenario","turns","score","objectives_secured","objectives_failed","route_uptime"):
        html.append(f"<tr><th>{k}</th><td>{kpis.get(k)}</td></tr>")
    html.append("</tbody></table><h3>Objectives</h3><ul>")
    for o in obj_eval.get("all", []):
        badge = "✅" if o.get("status")=="secured" else ("❌" if o.get("status")=="failed" else "⏳")
        html.append(f"<li>{badge} <b>{o.get('title', o['id'])}</b> – {o.get('desc','')}</li>")
    html.append("</ul><h3>Routes</h3><table><thead><tr><th>ID</th><th>Side</th><th>Status</th><th>Eff.</th></tr></thead><tbody>")
    for r in supply.get("routes", []):
        html.append(f"<tr><td>{r['id']}</td><td>{r['side']}</td><td>{r['status']}</td><td>{r['effective']}</td></tr>")
    html.append("</tbody></table></body></html>")
    (session_dir / "kpi_report.html").write_text("".join(html), encoding="utf-8")

def append_history(root: Path, kpis: dict):
    hist = root / "kpi_history.csv"
    new = not hist.exists()
    with open(hist, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["scenario","turns","score","objectives_secured","objectives_failed","route_uptime","blue_losses","red_losses"])
        w.writerow([kpis.get("scenario"), kpis.get("turns"), kpis.get("score"), kpis.get("objectives_secured"),
                    kpis.get("objectives_failed"), kpis.get("route_uptime"), kpis.get("blue_losses"), kpis.get("red_losses")])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="bridgehead")
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--history", action="store_true")
    args = ap.parse_args()

    if args.seed:
        random.seed(args.seed)

    scen_path = resolve_scenario_path(args.scenario)
    tag = Path(scen_path).stem
    sess = SessionManager(base_dir="runs").new_session_dir(tag=tag)
    print(f"[Headless] session -> {sess}")

    engine = TurnEngine(scenario_path=scen_path, auto_approve=True)

    for _ in range(args.turns):
        engine.run_turn(None)
        engine.advance_turn()

    kpis, supply, obj_eval = compute_kpis(engine, args.turns)
    (sess / "kpi_summary.json").write_text(json.dumps(kpis, indent=2), encoding="utf-8")

    if args.html:
        write_kpi_report(sess, kpis, supply, obj_eval)
    if args.history:
        append_history(Path("."), kpis)

    print(f"[Headless] Wrote: {(sess / 'kpi_summary.json')}")
    if args.html:
        print(f"[Headless] Wrote: {(sess / 'kpi_report.html')}")

if __name__ == "__main__":
    main()
