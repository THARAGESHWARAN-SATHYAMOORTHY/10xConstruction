from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Wall(Base):
    __tablename__ = "walls"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    obstacles = relationship("Obstacle", back_populates="wall", cascade="all, delete-orphan")
    trajectories = relationship("Trajectory", back_populates="wall", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Wall(id={self.id}, width={self.width}, height={self.height})>"


class Obstacle(Base):
    __tablename__ = "obstacles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wall_id = Column(Integer, ForeignKey("walls.id"), nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    
    # Relationship
    wall = relationship("Wall", back_populates="obstacles")
    
    __table_args__ = (
        Index('idx_obstacles_wall', 'wall_id'),
    )
    
    def __repr__(self):
        return f"<Obstacle(id={self.id}, x={self.x}, y={self.y}, w={self.width}, h={self.height})>"


class Trajectory(Base):
    __tablename__ = "trajectories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wall_id = Column(Integer, ForeignKey("walls.id"), nullable=False)
    tool_width = Column(Float, nullable=False)
    total_length = Column(Float, nullable=False)
    coverage_length = Column(Float, nullable=False)
    transition_length = Column(Float, nullable=False)
    coverage_percentage = Column(Float, nullable=False)
    execution_time_ms = Column(Integer, nullable=False)
    num_cells = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    wall = relationship("Wall", back_populates="trajectories")
    path_segments = relationship("PathSegment", back_populates="trajectory", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_trajectories_wall', 'wall_id'),
        Index('idx_trajectories_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Trajectory(id={self.id}, wall_id={self.wall_id}, length={self.total_length:.2f})>"


class PathSegment(Base):
    __tablename__ = "path_segments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trajectory_id = Column(Integer, ForeignKey("trajectories.id"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    cell_id = Column(Integer, nullable=True)  # Which cell this segment belongs to
    start_x = Column(Float, nullable=False)
    start_y = Column(Float, nullable=False)
    end_x = Column(Float, nullable=False)
    end_y = Column(Float, nullable=False)
    segment_type = Column(String, nullable=False)  # 'coverage' or 'transition'
    
    # Relationship
    trajectory = relationship("Trajectory", back_populates="path_segments")
    
    __table_args__ = (
        Index('idx_segments_trajectory', 'trajectory_id', 'sequence_order'),
        CheckConstraint("segment_type IN ('coverage', 'transition')", name='check_segment_type'),
    )
    
    def __repr__(self):
        return f"<PathSegment(id={self.id}, seq={self.sequence_order}, type={self.segment_type})>"
