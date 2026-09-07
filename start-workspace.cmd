@echo off
cd /d "%~dp0"
if not exist "web\dist\index.html" (
  echo Build the interface first: cd web, npm ci, npm run build.
  pause
  exit /b 1
)
uv run --offline python -m driftwatch.workbench
if errorlevel 1 pause
