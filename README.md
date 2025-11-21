# MacArthur War Engine (MWE)

MacArthur War Engine is a theater-level, staff-driven war simulator inspired by WWII Pacific command.  
Instead of micromanaging every unit, the player acts like a theater commander with a full G-staff:

- **G-1 Personnel** – strength, replacements, fatigue, morale  
- **G-2 Intelligence** – recon, fog of war, enemy estimates  
- **G-3 Operations** – orders, movement, combat execution  
- **G-4 Logistics** – supply, depots, ports, throughput  
- **G-5 Plans** – long-range campaign planning  
- **G-6 Signals** – command delay, comms disruption  

MWE is being built as a long-term hobby project and AI/engineering playground.

---

## Repo Structure

```text
MWE/
├─ Docs/                # Design docs, manuals, diagrams
├─ archive/             # Old runs, logs, saves you want to keep
├─ logs/                # Current log output
├─ rules/               # Data-driven rules (combat tables, logistics params, etc.)
├─ runs/                # Temporary run/output folders
├─ scenarios/           # Scenario data (OOBs, maps, configs)
├─ server/
│  ├─ engine/
│  │  ├─ core/          # Time system, unit model, map model
│  │  └─ staff/         # G-1 .. G-6 staff modules
│  └─ ...               # Existing backend & bridge code
└─ ui/                  # Any UI front-end / tools
