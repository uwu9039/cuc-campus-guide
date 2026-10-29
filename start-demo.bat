@echo off
setlocal
cd /d "%~dp0"

rem Demo / recording mode: no file watcher, no restart window.
rem Use start.bat while developing, use this one when recording or presenting.

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] Creating venv...
  python -m venv .venv
)

if not exist ".venv\Scripts\uvicorn.exe" (
  echo [2/2] Installing dependencies...
  ".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
)

echo Starting http://127.0.0.1:8000  (new UI /, classic /classic; demo mode, no reload)
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000
