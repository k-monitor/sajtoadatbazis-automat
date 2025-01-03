#!/bin/bash

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "script dir: $SCRIPT_DIR"

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

python3 "$SCRIPT_DIR/update_base.py"
python3 "$SCRIPT_DIR/update_classification.py"