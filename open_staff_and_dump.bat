@echo off
REM ============================================
REM  MWE Phase 8 – Staff Helper
REM  - Opens key staff files in Notepad++
REM  - Dumps full contents to one text file
REM ============================================

REM Adjust this if your MWE path is different
set "MWE_ROOT=C:\MWE"
set "STAFF_DIR=%MWE_ROOT%\server\engine\staff"

REM Adjust this if Notepad++ is installed elsewhere
set "NP_EXE=C:\Program Files\Notepad++\notepad++.exe"

REM --------------------------------------------
REM 1) Open staff files in Notepad++
REM --------------------------------------------
echo Opening staff files in Notepad++...

"%NP_EXE%" ^
  "%STAFF_DIR%\g3_operations.py" ^
  "%STAFF_DIR%\g4_logistics.py" ^
  "%STAFF_DIR%\g5_plans.py" ^
  "%STAFF_DIR%\g6_signals.py" ^
  "%STAFF_DIR%\g7_reinforcements.py" ^
  "%STAFF_DIR%\g8_objectives.py"

REM --------------------------------------------
REM 2) Dump all staff files into one text file
REM --------------------------------------------
set "OUT_FILE=%MWE_ROOT%\server\staff_phase8_dump.txt"
echo Creating combined dump: %OUT_FILE%
echo. > "%OUT_FILE%"

for %%F in (
  "g3_operations.py"
  "g4_logistics.py"
  "g5_plans.py"
  "g6_signals.py"
  "g7_reinforcements.py"
  "g8_objectives.py"
) do (
  echo ============================== >> "%OUT_FILE%"
  echo File: %%F >> "%OUT_FILE%"
  echo ============================== >> "%OUT_FILE%"
  type "%STAFF_DIR%\%%~F" >> "%OUT_FILE%"
  echo. >> "%OUT_FILE%"
)

echo Done.
echo Staff files opened in Notepad++ and dumped to:
echo   %OUT_FILE%
pause
