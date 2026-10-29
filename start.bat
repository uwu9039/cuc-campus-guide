@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating venv...
  python -m venv .venv
)

if not exist ".venv\Scripts\uvicorn.exe" (
  echo [2/3] Installing dependencies...
  ".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
)

echo [3/3] Starting http://127.0.0.1:8000  (new UI at /, classic at /classic; hot reload)
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
