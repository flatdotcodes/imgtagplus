#!/bin/bash
set -e

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Updating pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if command -v npm >/dev/null 2>&1; then
  echo "Installing frontend dependencies and building CSS..."
  npm install
  npm run build:css
else
  echo "npm not found; skipping frontend dependency install and CSS build."
fi

echo "Setup complete. You can now use the 'imgtagplus' command or run 'python server.py'."
echo "To activate the environment in your shell, run: source .venv/bin/activate"
