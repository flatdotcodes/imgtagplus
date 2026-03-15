#!/bin/bash
set -e

# Check Python version (require >= 3.10)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
echo "Detected Python ${PYTHON_VERSION}"

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "Error: Python >= 3.10 is required, found ${PYTHON_VERSION}" >&2
    exit 1
fi

INSTALL_DEV=false
for arg in "$@"; do
    if [ "$arg" = "--dev" ]; then
        INSTALL_DEV=true
    fi
done

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Updating pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ "$INSTALL_DEV" = true ]; then
    echo "Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

if command -v npm >/dev/null 2>&1; then
  echo "Installing frontend dependencies and building CSS..."
  npm install
  npm run build:css
else
  echo "npm not found; skipping frontend dependency install and CSS build."
fi

echo "Setup complete. You can now use the 'imgtagplus' command or run 'python -m imgtagplus.server'."
echo "To activate the environment in your shell, run: source .venv/bin/activate"
echo "Model weights are downloaded locally on first use and are not meant to be committed to Git."
echo "Default cache: ~/.cache/imgtagplus (repo-local fallback: ./.cache/imgtagplus, which is gitignored)."
echo "Optional cache warm-up: python -m imgtagplus -i ./test_image.jpg --model-id clip --silent --output-dir /tmp/imgtagplus-model-warmup"
