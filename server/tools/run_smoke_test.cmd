@echo off
setlocal

REM Always run from repo root so imports behave
cd /d C:\MWE\server

REM Make sure repo root is on PYTHONPATH for this session
set PYTHONPATH=C:\MWE\server

python tools\smoke_test_engine_api.py

endlocal
