#!/bin/bash
# Run from project root: bash scripts/generate_mock_data.sh

echo "Generating mock data for mall-e-app..."

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Navigate to project root (parent of scripts directory)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Set PYTHONPATH
export PYTHONPATH="scripts"

# Activate virtual environment if it exists, create if not
VENV_PATH="scripts/get_store_url_and_tags/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    cd scripts/get_store_url_and_tags
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
    cd "$PROJECT_ROOT"
else
    echo "Activating existing virtual environment..."
    source "$VENV_PATH/bin/activate"
fi

# Create mall-e-app/src/data directory if it doesn't exist
mkdir -p mall-e-app/src/data

# Run scraper with limited stores and URLs for quick mock data
echo "Running scraper (this may take a few minutes)..."
python -m get_store_url_and_tags --stores "AmericanEagle,Abercrombie" --max-urls-per-shop 3 --json 2>/dev/null > mall-e-app/src/data/mock-data.json

echo "Mock data generated successfully at mall-e-app/src/data/mock-data.json"
echo "Check the file to verify the data was generated correctly."