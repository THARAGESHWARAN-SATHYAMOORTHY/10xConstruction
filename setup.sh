#!/bin/bash

echo "==================================="
echo "Coverage Path Planning Setup"
echo "==================================="

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "==================================="
echo "Setup complete!"
echo "==================================="
echo ""
echo "To start the server:"
echo "  ./run.sh"
echo ""
echo "To run tests:"
echo "  pytest tests/ -v --disable-warnings"
echo ""
