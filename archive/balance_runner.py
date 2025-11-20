# balance_runner.py — multi-run balance harness with UTF-8 safe printing & colored output
from __future__ import annotations
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='replace')

import json, subprocess, statistics as stats, argparse, random, shutil, re
from pathlib import Path
from datetime import datetime

try:
    from colorama import Fore, Style, init as color_init
    color_init(autoreset=True)
except ImportError:
    class Dummy:
        def __getattr__(self, k): return ''
    Fore = Style = Dummy()

ROOT = Path(".").resolve()
SESSION_RE = re.compile(r"^\[Headless\]\s+session\s+->\s+(.+)$", re.I)
WROTE_RE   = re.compile(r"^\[Headless\]\s+Wrote:\s+(.+kpi_summary\.json)$", re.I)

def timestamp(): return datetime.now().strftime("%Y%m%d_%H%M%S")

def run_once(scenario: str, turns: int, seed: int, html: bool, history: bool):
    args = ["py", "headless_sim.py", "--scenario", scenario, "--turns", str(turns), "--seed", str(seed)]
    if html: args.append("--html")
    if history: args.append("--history")

    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        print(Fore.RED + p.stdout)
        raise RuntimeError("headless_sim failed")

    session_dir, kpi_path = None, None
    for line in p.stdout.splitlines():
        m = SESSION_RE.match(line.strip())
        if m: session_dir = Path(m.group(1)).resolve()
        w = WROTE_RE.match(line.strip())
        if w: kpi_path = Path(w.group(1)).resolve()

    if not session_dir:
        runs = sorted((ROOT / "runs").glob("session_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        session_dir = runs[0] if runs else None
    if not session_dir or not session_dir.exists():
        raise RuntimeError("Session folder not found.")

    if not kpi_path: kpi_path = session_dir / "kpi_summary.json"
    kpis = json.loads(kpi_path.read_text(encoding="utf-8"))
    return kpis, session_dir

def summarize(rows: list[dict]) -> dict:
    def m(name): return stats.mean([r.get(name, 0) for r in rows]) if rows else 0
    def s(name): return stats.pstdev([r.get(name, 0) for r in rows]) if rows else 0
    numeric = {k for k,v in rows[0].items() if isinstance(v,(int,float))} if rows else set()
    return {
        "count": len(rows),
        "means": {k: round(m(k),4) for k in numeric},
        "stdevs": {k: round(s(k),4) for k in numeric}
    }

def html_report(summary: dict, scenario: str, turns: int, runs: int, path: Path):
    html = ["<html><head><meta charset='utf-8'><style>body{font-family:system-ui}table{border-collapse:collapse}th,td{padding:6px 10px;border:1px solid #ddd}</style></head><body>"]
    html.append(f"<h2>Balance Report — {scenario} | turns={turns} runs={runs}</h2>")
    html.append("<table><thead><tr><th>KPI</th><th>Mean</th><th>Stdev</th></tr></thead><tbody>")
    for k,v in summary["means"].items():
        html.append(f"<tr><td>{k}</td><td>{v}</td><td>{summary['stdevs'].get(k,0)}</td></tr>")
    html.append("</tbody></table></body></html>")
    path.write_text("".join(html), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="bridgehead")
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--html", action="store_true")
    ap.add_argument("--history", action="store_true")
    args = ap.parse_args()

    stamp = timestamp()
    bal_root = ROOT / "runs" / f"balance_{stamp}_{args.scenario}"
    bal_root.mkdir(parents=True, exist_ok=True)

    rows = []
    for i in range(args.runs):
        seed = random.randint(1, 10_000_000)
        print(Fore.CYAN + f"[Balance] {i+1}/{args.runs} seed={seed}")
        try:
            kpis, session_dir = run_once(args.scenario, args.turns, seed, args.html, args.history)
            rows.append(kpis)
            run_dir = bal_root / f"run_{i+1:02d}"
            run_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(session_dir / "kpi_summary.json", run_dir / "kpi_summary.json")
            rpt = session_dir / "kpi_report.html"
            if rpt.exists(): shutil.copy2(rpt, run_dir / "kpi_report.html")
            print(Fore.GREEN + f"  ✓ Run {i+1} done → {run_dir.name}")
        except Exception as e:
            print(Fore.RED + f"  ✗ Run {i+1} failed: {e}")

    if not rows:
        print(Fore.RED + "No successful runs.")
        return

    summary = summarize(rows)
    (bal_root / "balance_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.html:
        html_report(summary, args.scenario, args.turns, args.runs, bal_root / "balance_report.html")
    print(Fore.YELLOW + f"[✓] Balance results saved to {bal_root}")

if __name__ == "__main__":
    main()
