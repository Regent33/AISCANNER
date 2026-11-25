@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Complete the Windows setup in README.md first.
  pause
  exit /b 1
)
if not exist "frontend\dist\index.html" (
  echo Build the frontend with npm.cmd --prefix frontend run build, then start again.
  pause
  exit /b 1
)
if not defined SCANNER_DATA if not exist "data\scanner.db" if exist "data\demo\scanner.db" set "SCANNER_DATA=data/demo"
echo Open http://127.0.0.1:8000/settings after the server starts. Keep this window open.
".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
if errorlevel 1 (
  echo If port 8000 is already in use by Paper Scanner, open the address above.
  pause
  exit /b 1
)
