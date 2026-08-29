@echo off
echo ============================================
echo   Helix Education - Windows Setup
echo   (requires Python 3.11 via py launcher)
echo ============================================
echo.

REM Create virtual environment
echo [1/3] Creating virtual environment...
py -3.11 -m venv .venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create .venv. Ensure Python 3.11 is installed (py -3.11).
    pause
    exit /b 1
)

REM Activate and install dependencies
echo [2/3] Installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
if %errorlevel% neq 0 (
    echo ERROR: Dependency install failed.
    pause
    exit /b 1
)

echo [3/3] Setup complete!
echo.
echo ============================================
echo   Run tests with:
echo     python -m pytest -q
echo ============================================
pause
