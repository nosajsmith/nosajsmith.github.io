@echo off
robocopy "Q:\QDrive\Korea Project\Korea\mwe_engine" "C:\MWE" /MIR /XD .git logs /R:1 /W:1
echo Sync complete.
