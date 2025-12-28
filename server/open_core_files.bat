@echo off
setlocal
cd /d C:\MWE\server

echo Opening core files in Notepad++...

"C:\Program Files\Notepad++\notepad++.exe" ^
engine\staff\base_staff.py ^
engine\staff\g3_operations.py ^
engine\engine_api.py

echo Done.
pause
