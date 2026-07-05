@echo off
echo.
echo   JDE Manufacturing Chatbot
echo   ----------------------------------------

where python >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found. Install from https://python.org
    pause & exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   Python: %PYVER%

if not exist ".venv" (
    echo   Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo   ERROR: Could not create virtual environment.
        pause & exit /b 1
    )
)

echo   Activating virtual environment...
call .venv\Scripts\activate.bat

echo   Upgrading pip...
python -m pip install --upgrade pip --quiet

echo   Installing dependencies (pure Python, no compiler needed)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo   ERROR: pip install failed. Check your internet connection.
    pause & exit /b 1
)

echo   Dependencies ready.
echo.

where ollama >nul 2>&1
if errorlevel 1 (
    echo   WARNING: Ollama not found.
    echo   Install from https://ollama.com then run: ollama pull llama3.1
    echo.
) else (
    echo   Ollama: found
    echo.
)

echo   Starting server on http://localhost:8000
echo   Open browser to: http://localhost:8000
echo   Press Ctrl+C to stop
echo.

python run.py
pause
