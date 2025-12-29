#!/usr/bin/env bash
# Quick launch script for Ready or Not Mod Manager

set -e

# Check if Python 3.11+ is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

# Check if PySide6 is installed
if ! python3 -c "import PySide6" &> /dev/null; then
    echo "PySide6 is not installed. Installing dependencies..."
    pip install -r requirements.txt || {
        echo "Error: Failed to install dependencies"
        exit 1
    }
fi

# Launch the application
python3 main.py
