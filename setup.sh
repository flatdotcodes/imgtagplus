#!/bin/bash
set -e

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Updating pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. You can now use the 'imgtagplus' command or run 'python server.py'."
echo "To activate the environment in your shell, run: source .venv/bin/activate"
