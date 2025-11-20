@echo off
sc query MWE_Bridge | findstr STATE
curl -s http://127.0.0.1:8770/healthz && echo.
