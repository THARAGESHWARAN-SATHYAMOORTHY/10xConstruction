import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base

# Create test database
TEST_DATABASE_URL = "sqlite:///./test_coverage_planner.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestHealthCheck:    
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "coverage-path-planning"


class TestPlanEndpoint:    
    def test_plan_simple_wall(self):
        request_data = {
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.5,
            "obstacles": []
        }
        
        response = client.post("/api/plan", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "trajectory_id" in data
        assert data["wall_width"] == 5.0
        assert data["wall_height"] == 5.0
        assert data["tool_width"] == 0.5
        assert len(data["obstacles"]) == 0
        assert data["total_length"] > 0
        assert data["num_segments"] > 0
        assert data["execution_time_ms"] >= 0
    
    def test_plan_with_obstacles(self):
        request_data = {
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.25,
            "obstacles": [
                {"x": 2.0, "y": 2.0, "width": 0.5, "height": 0.5}
            ]
        }
        
        response = client.post("/api/plan", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["obstacles"]) == 1
        assert data["num_cells"] > 1
        assert data["transition_length"] > 0
    
    def test_plan_multiple_obstacles(self):
        request_data = {
            "wall_width": 10.0,
            "wall_height": 10.0,
            "tool_width": 0.3,
            "obstacles": [
                {"x": 2.0, "y": 2.0, "width": 1.0, "height": 1.0},
                {"x": 6.0, "y": 6.0, "width": 1.0, "height": 1.0},
                {"x": 2.0, "y": 6.0, "width": 1.0, "height": 1.0}
            ]
        }
        
        response = client.post("/api/plan", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["obstacles"]) == 3
        assert data["num_cells"] >= 3
    
    def test_plan_invalid_wall_dimensions(self):
        request_data = {
            "wall_width": -5.0,
            "wall_height": 5.0,
            "tool_width": 0.5,
            "obstacles": []
        }
        
        response = client.post("/api/plan", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_plan_invalid_tool_width(self):
        request_data = {
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.0,
            "obstacles": []
        }
        
        response = client.post("/api/plan", json=request_data)
        assert response.status_code == 422
    
    def test_plan_obstacle_outside_wall(self):
        request_data = {
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.5,
            "obstacles": [
                {"x": 4.0, "y": 4.0, "width": 2.0, "height": 2.0}  # Extends beyond wall
            ]
        }
        
        response = client.post("/api/plan", json=request_data)
        assert response.status_code == 422
    
    def test_plan_response_structure(self):
        request_data = {
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.5,
            "obstacles": []
        }
        
        response = client.post("/api/plan", json=request_data)
        data = response.json()
        
        # Check all required fields
        required_fields = [
            "trajectory_id", "wall_id", "wall_width", "wall_height",
            "tool_width", "obstacles", "total_length", "coverage_length",
            "transition_length", "coverage_percentage", "execution_time_ms",
            "num_cells", "num_segments", "path_segments", "message"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_plan_path_segments_structure(self):
        request_data = {
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.5,
            "obstacles": []
        }
        
        response = client.post("/api/plan", json=request_data)
        data = response.json()
        
        assert len(data["path_segments"]) > 0
        
        segment = data["path_segments"][0]
        assert "sequence_order" in segment
        assert "start_x" in segment
        assert "start_y" in segment
        assert "end_x" in segment
        assert "end_y" in segment
        assert "segment_type" in segment
        assert segment["segment_type"] in ["coverage", "transition"]


class TestTrajectoryEndpoint:    
    def test_get_trajectory_by_id(self):
        # First create a trajectory
        request_data = {
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.5,
            "obstacles": []
        }
        
        plan_response = client.post("/api/plan", json=request_data)
        trajectory_id = plan_response.json()["trajectory_id"]
        
        # Now retrieve it
        response = client.get(f"/api/trajectories/{trajectory_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == trajectory_id
        assert "created_at" in data
        assert len(data["path_segments"]) > 0
    
    def test_get_nonexistent_trajectory(self):
        response = client.get("/api/trajectories/99999")
        assert response.status_code == 404
    
    def test_query_trajectories(self):
        # Create multiple trajectories
        for i in range(3):
            request_data = {
                "wall_width": 5.0 + i,
                "wall_height": 5.0 + i,
                "tool_width": 0.5,
                "obstacles": []
            }
            client.post("/api/plan", json=request_data)
        
        # Query all
        response = client.get("/api/trajectories")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
    
    def test_query_trajectories_by_wall_id(self):
        # Create trajectories
        response1 = client.post("/api/plan", json={
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.5,
            "obstacles": []
        })
        wall_id_1 = response1.json()["wall_id"]
        
        # Query by first wall ID
        response = client.get(f"/api/trajectories?wall_id={wall_id_1}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["wall_id"] == wall_id_1
    
    def test_query_trajectories_with_limit(self):
        # Create multiple trajectories
        for i in range(5):
            client.post("/api/plan", json={
                "wall_width": 5.0,
                "wall_height": 5.0,
                "tool_width": 0.5,
                "obstacles": []
            })
        
        # Query with limit
        response = client.get("/api/trajectories?limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3


class TestPlaybackEndpoint:    
    def test_get_playback_data(self):
        # Create trajectory
        request_data = {
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.5,
            "obstacles": [
                {"x": 2.0, "y": 2.0, "width": 0.5, "height": 0.5}
            ]
        }
        
        plan_response = client.post("/api/plan", json=request_data)
        trajectory_id = plan_response.json()["trajectory_id"]
        
        # Get playback data
        response = client.get(f"/api/playback/{trajectory_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["trajectory_id"] == trajectory_id
        assert data["wall_width"] == 5.0
        assert data["wall_height"] == 5.0
        assert len(data["obstacles"]) == 1
        assert len(data["path_segments"]) > 0
        assert "metadata" in data
        
        # Check metadata
        metadata = data["metadata"]
        assert "tool_width" in metadata
        assert "total_length" in metadata
        assert "coverage_percentage" in metadata
    
    def test_get_playback_nonexistent(self):
        response = client.get("/api/playback/99999")
        assert response.status_code == 404


class TestPerformance:    
    def test_planning_response_time(self):
        request_data = {
            "wall_width": 10.0,
            "wall_height": 10.0,
            "tool_width": 0.2,
            "obstacles": [
                {"x": 2.0, "y": 2.0, "width": 1.0, "height": 1.0},
                {"x": 6.0, "y": 6.0, "width": 1.0, "height": 1.0}
            ]
        }
        
        response = client.post("/api/plan", json=request_data)
        
        process_time = float(response.headers.get("X-Process-Time", "0"))
        
        assert process_time < 2000
    
    def test_query_response_time(self):
        for _ in range(5):
            client.post("/api/plan", json={
                "wall_width": 5.0,
                "wall_height": 5.0,
                "tool_width": 0.5,
                "obstacles": []
            })
        
        response = client.get("/api/trajectories")
        
        process_time = float(response.headers.get("X-Process-Time", "0"))
        
        assert process_time < 100


class TestEdgeCases:
    def test_minimum_wall_size(self):
        request_data = {
            "wall_width": 1.0,
            "wall_height": 1.0,
            "tool_width": 0.5,
            "obstacles": []
        }
        
        response = client.post("/api/plan", json=request_data)
        assert response.status_code == 200
    
    def test_large_wall(self):
        request_data = {
            "wall_width": 20.0,
            "wall_height": 20.0,
            "tool_width": 0.5,
            "obstacles": []
        }
        
        response = client.post("/api/plan", json=request_data)
        assert response.status_code == 200
    
    def test_very_small_tool(self):
        request_data = {
            "wall_width": 5.0,
            "wall_height": 5.0,
            "tool_width": 0.1,
            "obstacles": []
        }
        
        response = client.post("/api/plan", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["num_segments"] > 20


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
