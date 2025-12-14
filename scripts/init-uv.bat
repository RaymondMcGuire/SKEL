@echo off
cd ..

setlocal

REM Run this script from the project root directory.

where uv >nul 2>nul
if errorlevel 1 (
  echo [init] ERROR: uv is not found in PATH.
  echo [init] Please install uv first: https://astral.sh/uv
  pause
  exit /b 1
)

REM Ensure Python 3.12 is available
uv python install 3.12

REM Pin the project's Python version (.python-version)
uv python pin 3.12

REM Create project-local virtual environment (default: .venv)
uv venv

REM Resolve dependencies and generate uv.lock
uv lock

REM Install dependencies into .venv strictly from uv.lock
REM (By default, uv installs the current project in editable mode.)
uv sync

echo [init] Done. Environment is ready.
pause
endlocal