# tidy_outputs.py — move loose turn artifacts into runs/turn_<N>/ folders, optionally zip/prune
from __future__ import annotations
import os, re, shutil, argparse, zipfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"

# filename patterns → extract turn number
PATTERNS = [
    (re.compile(r"^turn_(\d+)_report\.html$", re.I),               "turn_{n}"),
    (re.compile(r"^map_turn(\d+)\.html$", re.I),                    "turn_{n}"),
    (re.compile(r"^map_turn(\d+)\.txt$", re.I),                     "turn_{n}"),
    (re.compile(r"^unit_status_turn(\d+)\.csv$", re.I),             "turn_{n}"),
    (re.compile(r"^orders_turn(\d+)\.json$", re.I),                 "turn_{n}"),
    (re.compile(r"^staff_log_turn(\d+)\.json$", re.I),              "turn_{n}"),
    (re.compile(r"^combat_results_turn(\d+)\.json$", re.I),         "turn_{n}"),
    (re.compile(r"^objectives_turn(\d+)\.json$", re.I),             "turn_{n}"),
    (re.compile(r"^kpi_summary\.json$", re.I),                      "session"),   # headless outputs
    (re.compile(r"^kpi_report\.html$", re.I),                       "session"),
    (re.compile(r"^kpi_history\.csv$", re.I),                       "session"),
]

def find_target(fname: str):
    for rgx, bucket in PATTERNS:
        m = rgx.match(fname)
        if m:
            if bucket == "turn_{n}":
                n = m.group(1)
                return f"turn_{n}"
            return bucket
    return None

def zip_folder(folder: Path):
    zip_path = folder.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(folder))
    return zip_path

def prune_old(run_root: Path, keep: int):
    # keep most recent N folders (by modified time), delete older
    folders = [p for p in run_root.iterdir() if p.is_dir()]
    folders.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for old in folders[keep:]:
        shutil.rmtree(old, ignore_errors=True)

def main():
    ap = argparse.ArgumentParser(description="Tidy MWE outputs into runs/turn_N folders.")
    ap.add_argument("--root", default=str(ROOT), help="Engine root (where loose files are).")
    ap.add_argument("--into", default=str(RUNS), help="Destination root (default runs/).")
    ap.add_argument("--zip", action="store_true", help="Zip each turn folder after moving.")
    ap.add_argument("--keep", type=int, default=0, help="Keep only the most recent N turn folders (delete older).")
    ap.add_argument("--dry-run", action="store_true", help="Show actions only.")
    args = ap.parse_args()

    root = Path(args.root)
    into = Path(args.into)
    into.mkdir(parents=True, exist_ok=True)

    moved = 0
    for p in root.iterdir():
        if not p.is_file():
            continue
        tgt = find_target(p.name)
        if not tgt:
            continue
        # session outputs go into runs/session_<timestamp>/
        if tgt == "session":
            session_dir = into / f"session_{time.strftime('%Y%m%d_%H%M%S')}"
            if not args.dry_run:
                session_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), session_dir / p.name)
            print(f"[move] {p.name} → {session_dir}")
            moved += 1
            continue

        # turn_N
        turn_dir = into / tgt
        if not args.dry_run:
            turn_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), turn_dir / p.name)
        print(f"[move] {p.name} → {turn_dir}")
        moved += 1

    if args.zip:
        # zip each turn_* folder (skip if already zipped)
        for folder in into.iterdir():
            if folder.is_dir() and folder.name.startswith("turn_"):
                zip_path = folder.with_suffix(".zip")
                if not args.dry_run and not zip_path.exists():
                    print(f"[zip] {folder} → {zip_path.name}")
                    zip_folder(folder)

    if args.keep > 0:
        print(f"[prune] keeping latest {args.keep} turn folders under {into}")
        if not args.dry_run:
            prune_old(into, args.keep)

    print(f"[done] moved={moved} → {into}")

if __name__ == "__main__":
    main()
