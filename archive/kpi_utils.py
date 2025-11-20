# kpi_utils.py — collect KPIs, write history, emit HTML report (no external deps)
from __future__ import annotations
import csv, json, os, statistics
from typing import Dict, Any, List

def safe_load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def append_history_csv(path: str, row: Dict[str, Any], header_order: List[str]):
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header_order)
        if not exists:
            w.writeheader()
        # ensure all keys present
        row_full = {k: row.get(k, "") for k in header_order}
        w.writerow(row_full)

def finalize_kpis(kpi: Dict[str, Any]) -> Dict[str, Any]:
    # compute aggregates
    if kpi.get("atk_odds_samples"):
        try:
            kpi["mean_atk_odds"] = round(statistics.mean(kpi["atk_odds_samples"]), 2)
            kpi["median_atk_odds"] = round(statistics.median(kpi["atk_odds_samples"]), 2)
        except statistics.StatisticsError:
            kpi["mean_atk_odds"] = 0.0
            kpi["median_atk_odds"] = 0.0
    else:
        kpi["mean_atk_odds"] = 0.0
        kpi["median_atk_odds"] = 0.0

    # route uptime %
    cut_turns = sum(kpi["routes_cut_turns"].values()) if kpi.get("routes_cut_turns") else 0
    total_routes = len(kpi.get("routes_seen", []))
    turns = max(1, int(kpi.get("turns", 1)))
    total_route_turns = max(1, total_routes * turns)
    up = 100.0 * (1.0 - (cut_turns / total_route_turns)) if total_routes > 0 else 0.0
    kpi["route_uptime_pct"] = round(up, 1)

    # casualties totals
    kpi["atk_casualties_total"] = int(kpi.get("atk_casualties_total", 0))
    kpi["def_casualties_total"] = int(kpi.get("def_casualties_total", 0))

    # convoy delivery/loss totals already tracked

    return kpi

def write_kpi_summary_json(path: str, kpi: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(kpi, f, indent=2)

def _sparkline(data: List[float], w=260, h=60, pad=6, color="#1976d2"):
    if not data:
        return f'<svg width="{w}" height="{h}"><text x="5" y="30" fill="#999">n/a</text></svg>'
    lo, hi = min(data), max(data)
    rng = (hi - lo) or 1.0
    step = (w - 2*pad) / max(1, len(data)-1)
    pts = []
    for i, v in enumerate(data):
        x = pad + i * step
        y = h - pad - ((v - lo) / rng) * (h - 2*pad)
        pts.append(f"{x:.1f},{y:.1f}")
    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <polyline fill="none" stroke="{color}" stroke-width="2" points="{' '.join(pts)}"/>
  <rect x="0" y="0" width="{w}" height="{h}" fill="none" stroke="#ddd"/>
</svg>'''

def write_kpi_report_html(path: str, kpi: Dict[str, Any]) -> None:
    turns = kpi.get("turns", 0)
    odds_samples = kpi.get("atk_odds_samples", [])
    vp_curve = kpi.get("vp_by_turn", [])
    vp_svg = _sparkline(vp_curve, color="#2e7d32")
    odds_svg = _sparkline(odds_samples, color="#7b1fa2")

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"/>
<title>KPI Report</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,Arial;margin:20px}}
h2{{margin-top:28px}}
table{{border-collapse:collapse;margin-top:8px}}
td,th{{border:1px solid #ddd;padding:6px 8px}}
.small{{color:#666;font-size:12px}}
.grid{{display:grid;grid-template-columns: 1fr 1fr; gap: 18px}}
.card{{border:1px solid #e0e0e0;border-radius:8px;padding:12px}}
.kv{{margin:0;}}
.kv dt{{color:#666;font-size:12px}}
.kv dd{{margin:0 0 10px 0;font-size:18px}}
</style>
</head>
<body>
<h1>Scenario KPI Report</h1>

<div class="grid">
  <div class="card">
    <h3>Victory Points (by turn)</h3>
    {vp_svg}
  </div>
  <div class="card">
    <h3>Attack Odds Samples</h3>
    {odds_svg}
  </div>
</div>

<h2>Summary</h2>
<dl class="kv">
  <dt>Turns</dt><dd>{turns}</dd>
  <dt>Victory Score (final)</dt><dd>{kpi.get('victory_score',0)}</dd>
  <dt>Battles (total)</dt><dd>{kpi.get('battles',0)}</dd>
  <dt>Mean Attack Odds</dt><dd>{kpi.get('mean_atk_odds',0.0)}</dd>
  <dt>Route Uptime %</dt><dd>{kpi.get('route_uptime_pct',0.0)}%</dd>
  <dt>Convoys Arrived / Lost</dt><dd>{kpi.get('convoys_arrived',0)} / {kpi.get('convoys_lost',0)}</dd>
  <dt>Casualties A/D</dt><dd>{kpi.get('atk_casualties_total',0)} / {kpi.get('def_casualties_total',0)}</dd>
</dl>

<h2>Notes</h2>
<p class="small">This report aggregates headless simulation metrics for quick balancing and regression checks.</p>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
