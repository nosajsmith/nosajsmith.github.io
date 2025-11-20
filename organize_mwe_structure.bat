@echo off
set "MWE_ROOT=C:\MWE"

echo ==========================================
echo   Organizing MacArthur War Engine folder
echo   Root: %MWE_ROOT%
echo ==========================================
echo.

REM --- Create main structure ---
echo Creating directory structure...
mkdir "%MWE_ROOT%\engine"
mkdir "%MWE_ROOT%\engine\core"
mkdir "%MWE_ROOT%\engine\staff"

mkdir "%MWE_ROOT%\bridge"
mkdir "%MWE_ROOT%\bridge\service_config"

mkdir "%MWE_ROOT%\scenarios"
mkdir "%MWE_ROOT%\scenarios\test_scenario"

mkdir "%MWE_ROOT%\ai"
mkdir "%MWE_ROOT%\ai\notebooks"
mkdir "%MWE_ROOT%\ai\prototypes"

mkdir "%MWE_ROOT%\tools"

mkdir "%MWE_ROOT%\docs"
mkdir "%MWE_ROOT%\design"
mkdir "%MWE_ROOT%\design\diagrams"

echo Directory structure created.
echo.

REM --- Move bridge scripts if present ---
echo Moving bridge files if found...
if exist "%MWE_ROOT%\mwe_bridge_p8.py" (
    move "%MWE_ROOT%\mwe_bridge_p8.py" "%MWE_ROOT%\bridge\" >nul
    echo - Moved mwe_bridge_p8.py
)

if exist "%MWE_ROOT%\install_service.bat" (
    move "%MWE_ROOT%\install_service.bat" "%MWE_ROOT%\bridge\service_config\" >nul
    echo - Moved install_service.bat
)

if exist "%MWE_ROOT%\uninstall_service.bat" (
    move "%MWE_ROOT%\uninstall_service.bat" "%MWE_ROOT%\bridge\service_config\" >nul
    echo - Moved uninstall_service.bat
)

echo Done moving bridge scripts.
echo.

REM --- Create placeholder files if they do not exist ---
echo Creating placeholder files...

if not exist "%MWE_ROOT%\README.md" (
    echo # MacArthur War Engine > "%MWE_ROOT%\README.md"
    echo Created README.md
)

if not exist "%MWE_ROOT%\.gitignore" (
    echo __pycache__/ > "%MWE_ROOT%\.gitignore"
    echo *.py[cod] >> "%MWE_ROOT%\.gitignore"
    echo venv/ >> "%MWE_ROOT%\.gitignore"
    echo .vscode/ >> "%MWE_ROOT%\.gitignore"
    echo Created .gitignore
)

if not exist "%MWE_ROOT%\docs\STAFF_OVERVIEW.md" (
    echo # MWE Staff Functions Overview > "%MWE_ROOT%\docs\STAFF_OVERVIEW.md"
    echo Created STAFF_OVERVIEW.md
)

echo Placeholder files created.
echo.

echo ==========================================
echo      MWE folder organization complete!
echo ==========================================
pause
