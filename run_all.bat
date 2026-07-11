@echo off
REM Simple wrapper that calls the Python launcher (ensures correct encoding and no complex labels)
cd /d "%~dp0"
REM prefer venv python if exists
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" run_all.py %*
) else (
  python run_all.py %*
)
