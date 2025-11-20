MWE – Phase 5 Files
=====================

Scope (Phase 5):
- AI Planning & Operations Loop (offensive planning, deception hooks, stance-driven behavior)
- Scenario State & Sync (units, HQs, positions, persistence)
- Map Canvas Integration (React canvas for unit rendering + selection)
- Backend Bridge Server (WebSocket) to connect UI <-> Engine/AI
- Command API schema

File List:
1) ai_planner.py
2) scenario_state.py
3) command_api.py
4) bridge_server.py
5) MapCanvas.tsx

Quick Start:
1. Ensure Phase 4 is installed and working.
2. `pip install websockets` (for bridge_server.py)
3. In one terminal: `python bridge_server.py`
4. In the React app, render MapCanvas.tsx and connect to the bridge (ws://localhost:8765).
5. From the UI or a small script, send commands (see command_api.py).

Notes:
- AI planner is deterministic when seeded; integrates with TurnEngine phases (orders/execution/review).
- Scenario state is a thin model for unit/HQ positions; expand as needed.
- MapCanvas draws basic symbols; replace with your full map engine later.
