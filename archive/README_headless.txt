Headless Scenario Harness (MacArthur Engine)
===========================================

Run a scenario for N turns, collect KPIs, and write:
- kpi_summary.json
- kpi_report.html (if --html)
- kpi_history.csv (if --history)

Examples:
---------
# Default scenario.json, 5 turns, write HTML + history
py headless_sim.py --turns 5 --html --history

# Named scenario from scenario_pack.json
py headless_sim.py --scenario bridgehead --turns 10 --seed 42 --html --history

# Literal path to a scenario
py headless_sim.py --scenario scenarios/interdiction.json --turns 8 --html

Artifacts:
----------
kpi_summary.json   : Detailed metrics (odds samples, VP by turn, convoy stats, route uptime)
kpi_report.html    : Visual summary using inline SVG
kpi_history.csv    : Appended row per run for tracking over time
