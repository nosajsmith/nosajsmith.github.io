@echo off
REM MacArthur War Engine - Structure Organizer (Option B: balanced)
REM Save this as organize_mwe_structure.bat in C:\MWE and run from there.

cd /d C:\MWE

echo === Creating core directory structure ===
mkdir server 2>nul
mkdir server\engine 2>nul
mkdir server\ai 2>nul
mkdir server\bridge 2>nul
mkdir server\tests 2>nul
mkdir server\tools 2>nul
mkdir data 2>nul
mkdir data\scenarios 2>nul
mkdir data\oob 2>nul
mkdir data\maps 2>nul
mkdir ui 2>nul
mkdir archive_backup 2>nul

echo === Backing up and moving ENGINE modules ===
for %%F in (
  combat_engine.py
  combat_resolver.py
  movement_engine.py
  morale.py
  supply_model.py
  terrain.py
  pathfinding.py
  objective_engine.py
  objective_tracker.py
  event_engine.py
  rule_engine.py
  game_state.py
  orders_executor.py
  order_execution.py
  order_hooks.py
  order_persistence.py
  order_system.py
  output_manager.py
  reports.py
  session_manager.py
  span.py
  staff_assistant.py
) do (
  if exist archive\%%F (
    echo   Processing %%F
    copy /Y archive\%%F archive_backup\%%F >nul
    move /Y archive\%%F server\engine\%%F >nul
  )
)

echo === Backing up and moving AI-related modules ===
for %%F in (
  ai_planner.py
  plan_manager.py
  plan_validator.py
  economy.py
  battle_metrics.py
) do (
  if exist archive\%%F (
    echo   Processing %%F
    copy /Y archive\%%F archive_backup\%%F >nul
    move /Y archive\%%F server\ai\%%F >nul
  )
)

echo === Backing up and moving BRIDGE / RUNNERS / UTILITIES ===
for %%F in (
  bridge_server.py
  bridge_server_p6.py
  bridge_client.js
  headless_sim.py
  run_game.py
  run_turn.py
  pdf_report.py
  desktop_launcher.py
  main.py
  main_gui.py
  streamlit_app.py
) do (
  if exist archive\%%F (
    echo   Processing %%F
    copy /Y archive\%%F archive_backup\%%F >nul
    move /Y archive\%%F server\bridge\%%F >nul
  )
)

echo === Backing up and moving SCENARIO / DATA FILES ===
for %%F in (
  scenario.json
  scenario_expanded.json
  scenario_pack.json
  scenario_state.py
  scenario_loader.py
  terrain.json
  objectives.json
  objectives_state.json
  supply_routes.json
  score.json
  score_history.json
  hq_pools.json
  plans.json
  plan_view.json
  convoys.json
  convoys_turn0.json
  convoys_turn1.json
  convoys_turn2.json
  convoys_turn3.json
  convoys_turn4.json
  convoys_turn5.json
  convoys_turn6.json
  convoys_turn7.json
  convoys_turn8.json
  convoys_turn9.json
) do (
  if exist archive\%%F (
    echo   Processing %%F
    copy /Y archive\%%F archive_backup\%%F >nul
    if /I "%%~xF"==".py" (
      move /Y archive\%%F server\engine\%%F >nul
    ) else (
      move /Y archive\%%F data\scenarios\%%F >nul
    )
  )
)

echo === Backing up and moving TERRAIN / MAP-RELATED PYTHON ===
for %%F in (
  map_overlay.py
  terrain.py
) do (
  if exist archive\%%F (
    echo   Processing %%F
    copy /Y archive\%%F archive_backup\%%F >nul
    move /Y archive\%%F server\engine\%%F >nul
  )
)

echo === Backing up and moving UI TSX/React components into ui/archive_ui ===
mkdir ui\archive_ui 2>nul
for %%F in (
  CommandCenter.tsx
  CommandCenter_P5.tsx
  MapCanvas.tsx
  MapOverlayMoves.tsx
  CombatLog.tsx
) do (
  if exist archive\%%F (
    echo   Processing %%F
    copy /Y archive\%%F archive_backup\%%F >nul
    move /Y archive\%%F ui\archive_ui\%%F >nul
  )
)

echo === Copying current js frontend into ui\current (if not already) ===
if exist js (
  mkdir ui\current 2>nul
  xcopy /E /I /Y js ui\current >nul
)

echo === Optional: clean up __pycache__ in root ===
if exist __pycache__ (
  echo   Removing root __pycache__ (safe - compiled files only)
  rmdir /S /Q __pycache__
)

echo === Done. Please review server\ and data\ structure ===
pause
