@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Root folder is wherever this .bat lives
set "MWE_ROOT=%~dp0"
REM Remove trailing backslash if present
if "%MWE_ROOT:~-1%"=="\" set "MWE_ROOT=%MWE_ROOT:~0,-1%"

echo ==========================================
echo   MWE structure setup
echo   Root: %MWE_ROOT%
echo ==========================================
echo.

REM --- Create engine + staff structure under server ---
echo Creating engine/staff directories under server...
mkdir "%MWE_ROOT%\server\engine"
mkdir "%MWE_ROOT%\server\engine\core"
mkdir "%MWE_ROOT%\server\engine\staff"

REM --- Create basic docs structure ---
echo Creating docs structure...
mkdir "%MWE_ROOT%\Docs"
mkdir "%MWE_ROOT%\Docs\diagrams"

REM --- Create placeholder staff modules (if missing) ---
echo Creating staff function modules...

set "STAFF_DIR=%MWE_ROOT%\server\engine\staff"

if not exist "%STAFF_DIR%\g1_personnel.py" (
  echo """G-1 Personnel module - placeholder""" > "%STAFF_DIR%\g1_personnel.py"
  echo # TODO: implement manpower, replacements, fatigue >> "%STAFF_DIR%\g1_personnel.py"
  echo Created g1_personnel.py
)

if not exist "%STAFF_DIR%\g2_intel.py" (
  echo """G-2 Intelligence module - placeholder""" > "%STAFF_DIR%\g2_intel.py"
  echo # TODO: implement detection, fog of war, recon >> "%STAFF_DIR%\g2_intel.py"
  echo Created g2_intel.py
)

if not exist "%STAFF_DIR%\g3_operations.py" (
  echo """G-3 Operations module - placeholder""" > "%STAFF_DIR%\g3_operations.py"
  echo # TODO: implement orders, movement, combat prep >> "%STAFF_DIR%\g3_operations.py"
  echo Created g3_operations.py
)

if not exist "%STAFF_DIR%\g4_logistics.py" (
  echo """G-4 Logistics module - placeholder""" > "%STAFF_DIR%\g4_logistics.py"
  echo # TODO: implement supply, depots, throughput >> "%STAFF_DIR%\g4_logistics.py"
  echo Created g4_logistics.py
)

if not exist "%STAFF_DIR%\g5_plans.py" (
  echo """G-5 Plans module - placeholder""" > "%STAFF_DIR%\g5_plans.py"
  echo # TODO: implement long-range campaign planning >> "%STAFF_DIR%\g5_plans.py"
  echo Created g5_plans.py
)

if not exist "%STAFF_DIR%\g6_signals.py" (
  echo """G-6 Signals module - placeholder""" > "%STAFF_DIR%\g6_signals.py"
  echo # TODO: implement command delays, comms disruption >> "%STAFF_DIR%\g6_signals.py"
  echo Created g6_signals.py
)

REM --- Create core placeholder (time system, unit model, etc.) ---
set "CORE_DIR=%MWE_ROOT%\server\engine\core"

if not exist "%CORE_DIR%\time_system.py" (
  echo """Time system - placeholder""" > "%CORE_DIR%\time_system.py"
  echo # TODO: implement ticks / turns / daily cycles >> "%CORE_DIR%\time_system.py"
  echo Created time_system.py
)

if not exist "%CORE_DIR%\unit_model.py" (
  echo """Unit model - placeholder""" > "%CORE_DIR%\unit_model.py"
  echo # TODO: implement unit state (strength, fatigue, supply) >> "%CORE_DIR%\unit_model.py"
  echo Created unit_model.py
)

if not exist "%CORE_DIR%\map_model.py" (
  echo """Map model - placeholder""" > "%CORE_DIR%\map_model.py"
  echo # TODO: implement hex/area map representation >> "%CORE_DIR%\map_model.py"
  echo Created map_model.py
)

REM --- Create high-level docs if missing ---
if not exist "%MWE_ROOT%\Docs\STAFF_OVERVIEW.md" (
  echo # MWE Staff Functions Overview> "%MWE_ROOT%\Docs\STAFF_OVERVIEW.md"
  echo >> "%MWE_ROOT%\Docs\STAFF_OVERVIEW.md"
  echo Placeholder for G-1..G-6 descriptions.>> "%MWE_ROOT%\Docs\STAFF_OVERVIEW.md"
  echo Created Docs\STAFF_OVERVIEW.md
)

if not exist "%MWE_ROOT%\Docs\DEV_NOTES.md" (
  echo # Developer Notes> "%MWE_ROOT%\Docs\DEV_NOTES.md"
  echo >> "%MWE_ROOT%\Docs\DEV_NOTES.md"
  echo Use this file to jot down design ideas, TODOs, and tech notes.>> "%MWE_ROOT%\Docs\DEV_NOTES.md"
  echo Created Docs\DEV_NOTES.md
)

echo.
echo ==========================================
echo   Structure setup complete.
echo ==========================================
pause
endlocal
