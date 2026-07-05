#!/usr/bin/env bash
set -e

echo ""
echo "  JDE Manufacturing Chatbot"
echo "  --------------------------------"

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "  ERROR: Python 3 not found. Install from https://python.org"
  exit 1
fi

PYTHON=$(command -v python3)
echo "  Python: $($PYTHON --version)"

# Create venv if not exists
if [ ! -d ".venv" ]; then
  echo "  Creating virtual environment..."
  $PYTHON -m venv .venv
fi

# Activate venv (Linux/Mac)
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  source .venv/Scripts/activate
else
  echo "  ERROR: Could not find venv activate script"
  exit 1
fi

echo "  Installing dependencies..."
pip install -q -r requirements.txt

# Check Ollama
if command -v ollama &>/dev/null; then
  echo "  Ollama: found"
else
  echo "  WARNING: Ollama not found - install from https://ollama.com"
  echo "  Then run: ollama pull llama3.1"
fi

echo ""
echo "  Starting server on http://localhost:8000"
echo "  Press Ctrl+C to stop"
echo ""

python run.py
