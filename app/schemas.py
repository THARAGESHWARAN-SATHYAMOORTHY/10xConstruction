from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


class ObstacleBase(BaseModel):
    x: float = Field(..., description="X coordinate of obstacle bottom-left corner")
    y: float = Field(..., description="Y coordinate of obstacle bottom-left corner")
    width: float = Field(..., gt=0, description="Width of obstacle")
    height: float = Field(..., gt=0, description="Height of obstacle")


class ObstacleCreate(ObstacleBase):
    pass


class ObstacleResponse(ObstacleBase):
    id: int
    
    class Config:
        from_attributes = True


class PlanRequest(BaseModel):
    wall_width: float = Field(..., gt=0, description="Width of the wall in meters")
    wall_height: float = Field(..., gt=0, description="Height of the wall in meters")
    tool_width: float = Field(..., gt=0, le=1.0, description="Width of the finishing tool in meters")
    obstacles: List[ObstacleCreate] = Field(default=[], description="List of rectangular obstacles")
    
    @field_validator('obstacles')
    @classmethod
    def validate_obstacles(cls, v, info):
        if 'wall_width' in info.data and 'wall_height' in info.data:
            wall_width = info.data['wall_width']
            wall_height = info.data['wall_height']
            
            for obs in v:
                if obs.x < 0 or obs.y < 0:
                    raise ValueError("Obstacle coordinates must be non-negative")
                if obs.x + obs.width > wall_width:
                    raise ValueError(f"Obstacle extends beyond wall width: {obs.x + obs.width} > {wall_width}")
                if obs.y + obs.height > wall_height:
                    raise ValueError(f"Obstacle extends beyond wall height: {obs.y + obs.height} > {wall_height}")
        
        return v


class PathSegmentResponse(BaseModel):
    sequence_order: int
    cell_id: Optional[int]
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    segment_type: str
    
    class Config:
        from_attributes = True


class TrajectoryResponse(BaseModel):
    id: int
    wall_id: int
    tool_width: float
    total_length: float
    coverage_length: float
    transition_length: float
    coverage_percentage: float
    execution_time_ms: int
    num_cells: int
    created_at: datetime
    path_segments: List[PathSegmentResponse] = []
    
    class Config:
        from_attributes = True


class PlanResponse(BaseModel):
    trajectory_id: int
    wall_id: int
    wall_width: float
    wall_height: float
    tool_width: float
    obstacles: List[ObstacleResponse]
    total_length: float
    coverage_length: float
    transition_length: float
    coverage_percentage: float
    execution_time_ms: int
    num_cells: int
    num_segments: int
    path_segments: List[PathSegmentResponse]
    message: str = "Coverage path generated successfully"


class PlaybackResponse(BaseModel):
    trajectory_id: int
    wall_width: float
    wall_height: float
    obstacles: List[ObstacleResponse]
    path_segments: List[PathSegmentResponse]
    metadata: dict
