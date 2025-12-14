@echo off
cd ..

REM Run the scripts inside the project's virtual environment
REM uv run automatically uses the project's .venv and ensures
REM dependencies are in sync with uv.lock

uv run python quickstart.py
pause
