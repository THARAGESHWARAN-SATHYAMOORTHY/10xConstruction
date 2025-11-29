from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.database import get_db
from app.schemas import (
    PlanRequest, PlanResponse, TrajectoryResponse, 
    PlaybackResponse, ObstacleResponse, PathSegmentResponse
)
from app.models import Wall, Obstacle, Trajectory, PathSegment
from app.planner import BoustrophedonPlanner, Obstacle as PlannerObstacle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["coverage-planning"])


@router.post("/plan", response_model=PlanResponse)
async def plan_coverage_path(request: PlanRequest, db: Session = Depends(get_db)):
    """
    Generate coverage path for a wall with obstacles.
    
    Algorithm: Boustrophedon Cellular Decomposition with TSP optimization
    
    Steps:
    1. Create wall and obstacles in database
    2. Run path planning algorithm
    3. Store trajectory and path segments
    4. Return complete path with metadata
    """
    try:
        logger.info(f"Planning coverage path for wall: {request.wall_width}x{request.wall_height}m, "
                   f"tool: {request.tool_width}m, obstacles: {len(request.obstacles)}")
        
        wall = Wall(
            width=request.wall_width,
            height=request.wall_height
        )
        db.add(wall)
        db.flush()
        
        db_obstacles = []
        for obs in request.obstacles:
            db_obstacle = Obstacle(
                wall_id=wall.id,
                x=obs.x,
                y=obs.y,
                width=obs.width,
                height=obs.height
            )
            db.add(db_obstacle)
            db_obstacles.append(db_obstacle)
        
        db.flush()
        
        planner_obstacles = [
            PlannerObstacle(x=obs.x, y=obs.y, width=obs.width, height=obs.height)
            for obs in request.obstacles
        ]
        
        planner = BoustrophedonPlanner(
            wall_width=request.wall_width,
            wall_height=request.wall_height,
            tool_width=request.tool_width,
            obstacles=planner_obstacles
        )
        
        path_segments, metadata = planner.plan()
        
        logger.info(f"Path planning complete: {len(path_segments)} segments, "
                   f"{metadata['execution_time_ms']}ms, "
                   f"{metadata['coverage_percentage']:.1f}% efficiency")
        
        trajectory = Trajectory(
            wall_id=wall.id,
            tool_width=request.tool_width,
            total_length=metadata['total_length'],
            coverage_length=metadata['coverage_length'],
            transition_length=metadata['transition_length'],
            coverage_percentage=metadata['coverage_percentage'],
            execution_time_ms=metadata['execution_time_ms'],
            num_cells=metadata['num_cells']
        )
        db.add(trajectory)
        db.flush()
        
        for seq, segment in enumerate(path_segments):
            db_segment = PathSegment(
                trajectory_id=trajectory.id,
                sequence_order=seq,
                cell_id=segment.cell_id,
                start_x=segment.start_x,
                start_y=segment.start_y,
                end_x=segment.end_x,
                end_y=segment.end_y,
                segment_type=segment.segment_type
            )
            db.add(db_segment)
        
        db.commit()
        
        return PlanResponse(
            trajectory_id=trajectory.id,
            wall_id=wall.id,
            wall_width=request.wall_width,
            wall_height=request.wall_height,
            tool_width=request.tool_width,
            obstacles=[ObstacleResponse(id=obs.id, x=obs.x, y=obs.y, 
                                       width=obs.width, height=obs.height) 
                      for obs in db_obstacles],
            total_length=metadata['total_length'],
            coverage_length=metadata['coverage_length'],
            transition_length=metadata['transition_length'],
            coverage_percentage=metadata['coverage_percentage'],
            execution_time_ms=metadata['execution_time_ms'],
            num_cells=metadata['num_cells'],
            num_segments=len(path_segments),
            path_segments=[PathSegmentResponse(
                sequence_order=seq,
                cell_id=seg.cell_id,
                start_x=seg.start_x,
                start_y=seg.start_y,
                end_x=seg.end_x,
                end_y=seg.end_y,
                segment_type=seg.segment_type
            ) for seq, seg in enumerate(path_segments)]
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error planning coverage path: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error planning path: {str(e)}")


@router.get("/trajectories/{trajectory_id}", response_model=TrajectoryResponse)
async def get_trajectory(trajectory_id: int, db: Session = Depends(get_db)):
    try:
        trajectory = db.query(Trajectory).filter(Trajectory.id == trajectory_id).first()
        
        if not trajectory:
            raise HTTPException(status_code=404, detail=f"Trajectory {trajectory_id} not found")
        
        logger.info(f"Retrieved trajectory {trajectory_id}")
        
        return TrajectoryResponse(
            id=trajectory.id,
            wall_id=trajectory.wall_id,
            tool_width=trajectory.tool_width,
            total_length=trajectory.total_length,
            coverage_length=trajectory.coverage_length,
            transition_length=trajectory.transition_length,
            coverage_percentage=trajectory.coverage_percentage,
            execution_time_ms=trajectory.execution_time_ms,
            num_cells=trajectory.num_cells,
            created_at=trajectory.created_at,
            path_segments=[PathSegmentResponse(
                sequence_order=seg.sequence_order,
                cell_id=seg.cell_id,
                start_x=seg.start_x,
                start_y=seg.start_y,
                end_x=seg.end_x,
                end_y=seg.end_y,
                segment_type=seg.segment_type
            ) for seg in trajectory.path_segments]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving trajectory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving trajectory: {str(e)}")


@router.get("/trajectories", response_model=List[TrajectoryResponse])
async def query_trajectories(
    wall_id: Optional[int] = Query(None, description="Filter by wall ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Trajectory)
        
        if wall_id is not None:
            query = query.filter(Trajectory.wall_id == wall_id)
        
        trajectories = query.order_by(Trajectory.created_at.desc()).limit(limit).all()
        
        logger.info(f"Retrieved {len(trajectories)} trajectories (wall_id={wall_id})")
        
        return [TrajectoryResponse(
            id=traj.id,
            wall_id=traj.wall_id,
            tool_width=traj.tool_width,
            total_length=traj.total_length,
            coverage_length=traj.coverage_length,
            transition_length=traj.transition_length,
            coverage_percentage=traj.coverage_percentage,
            execution_time_ms=traj.execution_time_ms,
            num_cells=traj.num_cells,
            created_at=traj.created_at,
            path_segments=[PathSegmentResponse(
                sequence_order=seg.sequence_order,
                cell_id=seg.cell_id,
                start_x=seg.start_x,
                start_y=seg.start_y,
                end_x=seg.end_x,
                end_y=seg.end_y,
                segment_type=seg.segment_type
            ) for seg in traj.path_segments]
        ) for traj in trajectories]
        
    except Exception as e:
        logger.error(f"Error querying trajectories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error querying trajectories: {str(e)}")


@router.get("/playback/{trajectory_id}", response_model=PlaybackResponse)
async def get_playback_data(trajectory_id: int, db: Session = Depends(get_db)):
    try:
        trajectory = db.query(Trajectory).filter(Trajectory.id == trajectory_id).first()
        
        if not trajectory:
            raise HTTPException(status_code=404, detail=f"Trajectory {trajectory_id} not found")
        
        wall = trajectory.wall
        obstacles = wall.obstacles
        
        logger.info(f"Retrieved playback data for trajectory {trajectory_id}")
        
        return PlaybackResponse(
            trajectory_id=trajectory.id,
            wall_width=wall.width,
            wall_height=wall.height,
            obstacles=[ObstacleResponse(
                id=obs.id,
                x=obs.x,
                y=obs.y,
                width=obs.width,
                height=obs.height
            ) for obs in obstacles],
            path_segments=[PathSegmentResponse(
                sequence_order=seg.sequence_order,
                cell_id=seg.cell_id,
                start_x=seg.start_x,
                start_y=seg.start_y,
                end_x=seg.end_x,
                end_y=seg.end_y,
                segment_type=seg.segment_type
            ) for seg in trajectory.path_segments],
            metadata={
                'tool_width': trajectory.tool_width,
                'total_length': trajectory.total_length,
                'coverage_length': trajectory.coverage_length,
                'transition_length': trajectory.transition_length,
                'coverage_percentage': trajectory.coverage_percentage,
                'num_cells': trajectory.num_cells,
                'num_segments': len(trajectory.path_segments),
                'execution_time_ms': trajectory.execution_time_ms
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving playback data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving playback data: {str(e)}")
