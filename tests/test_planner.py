import pytest
import math
from app.planner import BoustrophedonPlanner, Obstacle, Cell, PathSegment


class TestObstacle:    
    def test_obstacle_boundaries(self):
        obs = Obstacle(x=1.0, y=2.0, width=3.0, height=4.0)
        
        assert obs.left == 1.0
        assert obs.right == 4.0
        assert obs.bottom == 2.0
        assert obs.top == 6.0


class TestCell:    
    def test_cell_properties(self):
        cell = Cell(left=0.0, right=2.0, bottom=0.0, top=3.0, id=1)
        
        assert cell.width == 2.0
        assert cell.height == 3.0
        assert cell.area == 6.0
        assert cell.center == (1.0, 1.5)


class TestPathSegment:
    def test_segment_length(self):
        seg = PathSegment(
            start_x=0.0, start_y=0.0,
            end_x=3.0, end_y=4.0,
            segment_type='coverage'
        )
        
        assert seg.length == 5.0  # 3-4-5 triangle


class TestBoustrophedonPlanner:
    
    def test_simple_wall_no_obstacles(self):
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.5,
            obstacles=[]
        )
        
        segments, metadata = planner.plan()
        
        # Should have segments
        assert len(segments) > 0
        
        # All segments should be coverage (no transitions needed)
        coverage_segments = [s for s in segments if s.segment_type == 'coverage']
        assert len(coverage_segments) == len(segments)
        
        # Should have exactly 1 cell
        assert metadata['num_cells'] == 1
        
        # Should have reasonable path length
        assert metadata['total_length'] > 0
        assert metadata['coverage_length'] == metadata['total_length']
        assert metadata['transition_length'] == 0
    
    def test_wall_with_single_obstacle(self):
        obstacle = Obstacle(x=2.0, y=2.0, width=1.0, height=1.0)
        
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.5,
            obstacles=[obstacle]
        )
        
        segments, metadata = planner.plan()
        
        # Should have segments
        assert len(segments) > 0
        
        # Should have multiple cells (obstacle creates partitions)
        assert metadata['num_cells'] > 1
        
        # Should have both coverage and transition segments
        coverage_segments = [s for s in segments if s.segment_type == 'coverage']
        transition_segments = [s for s in segments if s.segment_type == 'transition']
        
        assert len(coverage_segments) > 0
        assert len(transition_segments) > 0
        
        # Transition length should be less than total length
        assert metadata['transition_length'] < metadata['total_length']
    
    def test_wall_with_multiple_obstacles(self):
        obstacles = [
            Obstacle(x=1.0, y=1.0, width=0.5, height=0.5),
            Obstacle(x=3.0, y=3.0, width=0.5, height=0.5)
        ]
        
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.25,
            obstacles=obstacles
        )
        
        segments, metadata = planner.plan()
        
        # Should handle multiple obstacles
        assert len(segments) > 0
        assert metadata['num_cells'] >= 2
    
    def test_cell_decomposition_no_obstacles(self):
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.5,
            obstacles=[]
        )
        
        cells = planner._decompose_cells()
        
        # Should create exactly one cell covering the entire wall
        assert len(cells) == 1
        assert cells[0].left == 0.0
        assert cells[0].right == 5.0
        assert cells[0].bottom == 0.0
        assert cells[0].top == 5.0
    
    def test_cell_decomposition_with_obstacle(self):
        obstacle = Obstacle(x=2.0, y=2.0, width=1.0, height=1.0)
        
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.5,
            obstacles=[obstacle]
        )
        
        cells = planner._decompose_cells()
        
        # Should create multiple cells
        assert len(cells) > 1
        
        # All cells should be valid (positive dimensions)
        for cell in cells:
            assert cell.width > 0
            assert cell.height > 0
            assert cell.left >= 0
            assert cell.right <= 5.0
            assert cell.bottom >= 0
            assert cell.top <= 5.0
    
    def test_boustrophedon_pattern(self):
        cell = Cell(left=0.0, right=2.0, bottom=0.0, top=2.0, id=0)
        
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.5,
            obstacles=[]
        )
        
        pattern = planner._generate_boustrophedon_pattern(cell)
        
        # Should have multiple segments
        assert len(pattern) > 0
        
        # All segments should be horizontal lines
        for seg in pattern:
            assert seg.segment_type == 'coverage'
            assert seg.start_y == seg.end_y  # Horizontal line
            
            # Should alternate direction
            # Either left-to-right or right-to-left
            assert (seg.start_x == cell.left and seg.end_x == cell.right) or \
                   (seg.start_x == cell.right and seg.end_x == cell.left)
    
    def test_path_segments_connected(self):
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.5,
            obstacles=[]  # Use simple case first
        )
        
        segments, _ = planner.plan()
        
        # For a simple wall with no obstacles, all segments should be coverage
        # and should be connected (alternating horizontal lines)
        for i in range(len(segments) - 1):
            current_end = (segments[i].end_x, segments[i].end_y)
            next_start = (segments[i + 1].start_x, segments[i + 1].start_y)
            
            # Calculate distance - should be very small (just moving to next line)
            distance = math.sqrt(
                (next_start[0] - current_end[0])**2 +
                (next_start[1] - current_end[1])**2
            )
            
            # Segments should be reasonably connected
            assert distance < 1.0, f"Large gap at segment {i}: distance={distance}"
    
    def test_coverage_completeness(self):
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.5,
            obstacles=[]
        )
        
        _, metadata = planner.plan()
        
        # Calculate expected minimum coverage (wall area / tool width)
        wall_area = 5.0 * 5.0
        expected_min_length = wall_area / 0.5
        
        # Actual length should be reasonably close to expected
        # (accounting for turns and transitions)
        assert metadata['coverage_length'] >= expected_min_length * 0.9
    
    def test_execution_time_reasonable(self):
        planner = BoustrophedonPlanner(
            wall_width=10.0,
            wall_height=10.0,
            tool_width=0.2,
            obstacles=[
                Obstacle(x=2.0, y=2.0, width=1.0, height=1.0),
                Obstacle(x=6.0, y=6.0, width=1.0, height=1.0)
            ]
        )
        
        _, metadata = planner.plan()
        
        # Should complete in under 1 second (1000ms) for this size
        assert metadata['execution_time_ms'] < 1000
    
    def test_different_tool_widths(self):
        for tool_width in [0.1, 0.25, 0.5, 1.0]:
            planner = BoustrophedonPlanner(
                wall_width=5.0,
                wall_height=5.0,
                tool_width=tool_width,
                obstacles=[]
            )
            
            segments, metadata = planner.plan()
            
            # Smaller tool width should require more coverage segments
            assert len(segments) > 0
            assert metadata['coverage_length'] > 0
    
    def test_obstacle_at_boundary(self):
        obstacle = Obstacle(x=0.0, y=0.0, width=1.0, height=1.0)
        
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.5,
            obstacles=[obstacle]
        )
        
        segments, metadata = planner.plan()
        
        # Should handle boundary obstacle
        assert len(segments) > 0
        assert metadata['num_cells'] >= 1
    
    def test_very_small_cell(self):
        # Create obstacles that leave small gaps
        obstacles = [
            Obstacle(x=0.0, y=0.0, width=2.4, height=5.0),
            Obstacle(x=2.6, y=0.0, width=2.4, height=5.0)
        ]
        
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.1,
            obstacles=obstacles
        )
        
        segments,_ = planner.plan()
        
        # Should handle small gaps
        assert len(segments) > 0


class TestOptimization:    
    def test_cell_ordering(self):
        obstacles = [
            Obstacle(x=1.0, y=1.0, width=0.5, height=0.5),
            Obstacle(x=3.0, y=1.0, width=0.5, height=0.5),
            Obstacle(x=1.0, y=3.0, width=0.5, height=0.5),
            Obstacle(x=3.0, y=3.0, width=0.5, height=0.5)
        ]
        
        planner = BoustrophedonPlanner(
            wall_width=5.0,
            wall_height=5.0,
            tool_width=0.25,
            obstacles=obstacles
        )
        
        _, metadata = planner.plan()
        
        # Optimization should keep transition length reasonable
        # Transition length should be less than 50% of total length
        assert metadata['transition_length'] < metadata['total_length'] * 0.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
