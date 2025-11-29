# How It Works

## Architecture Overview

**FastAPI Backend** → **Path Planner** → **SQLite Database** → **REST API**

## Request Flow

1. **Client sends POST `/api/plan`** with wall dimensions, tool width, and obstacles
2. **API validates** input and creates database records (Wall, Obstacles)
3. **BoustrophedonPlanner** processes the request:
   - Decomposes wall into cells around obstacles
   - Generates zig-zag coverage patterns per cell
   - Optimizes cell visit order (TSP with 2-opt)
   - Assembles complete path with transitions
4. **Results stored** in database (Trajectory, PathSegments)
5. **Response returned** with path segments and metadata

## Key Components

- **`app/main.py`**: FastAPI app with CORS, logging, static file serving
- **`app/api/routes.py`**: REST endpoints for planning, retrieval, playback
- **`app/planner.py`**: Core algorithm (Boustrophedon decomposition + TSP)
- **`app/models.py`**: SQLAlchemy models (Wall, Obstacle, Trajectory, PathSegment)
- **`app/database.py`**: SQLite connection and session management
- **`app/schemas.py`**: Pydantic models for request/response validation

## Data Flow

```
Input → Validation → Planning → Storage → Response
  ↓         ↓           ↓          ↓         ↓
JSON    Pydantic   Algorithm   SQLite    JSON
```

## API Endpoints

- `POST /api/plan` - Generate coverage path
- `GET /api/trajectories/{id}` - Get specific trajectory
- `GET /api/trajectories` - List trajectories (with filters)
- `GET /api/playback/{id}` - Get visualization data
- `GET /docs` - Interactive API documentation

## Path Segments

Each path consists of:
- **Coverage segments**: Zig-zag lines within cells (tool working)
- **Transition segments**: Straight lines between cells (tool idle)

