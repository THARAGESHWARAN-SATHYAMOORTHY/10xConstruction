#!/bin/bash

echo "Starting Coverage Path Planning Server..."
echo "Open http://localhost:8000 in your browser"
echo ""

if [ -d "venv" ]; then
    source venv/bin/activate
fi

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
