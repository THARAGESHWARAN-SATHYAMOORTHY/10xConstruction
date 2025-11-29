# Coverage Path Planning System

Boustrophedon-based coverage path planning for wall-finishing robots with obstacle avoidance.


**[View Algorithm Documentation](ALGO.md)** - Detailed explanation of the coverage path planning algorithm

## Installation

```bash
# Run setup script
./setup.sh
```

This creates a virtual environment and installs all dependencies.

## Getting Started

```bash
# Start the server
./run.sh
```

The API will be available at:
- **Web Interface**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Running Tests

```bash
pytest tests/ -v --disable-warnings
```

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

