# Coverage Path Planning System

Boustrophedon-based coverage path planning for wall-finishing robots with obstacle avoidance.

**Documentation**:
- **[Algorithm Documentation](ALGO.md)** - Detailed explanation of the coverage path planning algorithm
- **[How It Works](HOW_IT_WORKS.md)** - System overview and workflow

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/THARAGESHWARAN-SATHYAMOORTHY/10xConstruction.git
cd 10xConstruction
```

### 2. Installation

```bash
# Run setup script
./setup.sh
```

This creates a virtual environment and installs all dependencies.

### 3. Running the Application

```bash
# Start the server
./run.sh
```

The API will be available at:
- **Web Interface**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

## DEMO

https://github.com/user-attachments/assets/e4efa101-4838-4f9e-ab62-c1980d56a32c

## Running Tests

```bash
pytest tests/ -v --disable-warnings
```

https://github.com/user-attachments/assets/e04ec869-d4cd-47f9-8c2a-02d54a98bef9


