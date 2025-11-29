import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import time


@dataclass
class Obstacle:
    x: float
    y: float
    width: float
    height: float
    
    @property
    def left(self) -> float:
        return self.x
    
    @property
    def right(self) -> float:
        return self.x + self.width
    
    @property
    def bottom(self) -> float:
        return self.y
    
    @property
    def top(self) -> float:
        return self.y + self.height


@dataclass
class Cell:
    left: float
    right: float
    bottom: float
    top: float
    id: int
    
    @property
    def width(self) -> float:
        return self.right - self.left
    
    @property
    def height(self) -> float:
        return self.top - self.bottom
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.left + self.right) / 2, (self.bottom + self.top) / 2)


@dataclass
class PathSegment:
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    segment_type: str
    cell_id: Optional[int] = None
    
    @property
    def length(self) -> float:
        return math.sqrt((self.end_x - self.start_x)**2 + (self.end_y - self.start_y)**2)


class BoustrophedonPlanner:
    """
    # Coverage path planner using Boustrophedon Cellular Decomposition.
    
    # Algorithm phases:
    # 1. Cell Decomposition: Partition space around obstacles
    # 2. Coverage Pattern: Generate zig-zag paths within cells
    # 3. TSP Optimization: Order cells to minimize transitions
    # 4. Path Assembly: Combine cell patterns with transitions
    """
    
    def __init__(self, wall_width: float, wall_height: float, 
                 tool_width: float, obstacles: List[Obstacle]):
        self.wall_width = wall_width
        self.wall_height = wall_height
        self.tool_width = tool_width
        self.obstacles = obstacles
        self.overlap_margin = tool_width * 0.05  # 5% overlap for safety
        
    def plan(self) -> Tuple[List[PathSegment], Dict]:
        start_time = time.time()
        
        # Phase 1: Cell Decomposition
        cells = self._decompose_cells()
        
        # Phase 2: Generate coverage patterns for each cell
        cell_patterns = {}
        for cell in cells:
            cell_patterns[cell.id] = self._generate_boustrophedon_pattern(cell)
        
        # Phase 3: TSP Optimization - order cells
        cell_order = self._optimize_cell_order(cells, cell_patterns)
        
        # Phase 4: Assemble complete path with transitions
        path_segments = self._assemble_path(cells, cell_patterns, cell_order)
        
        # Calculate metrics
        execution_time_ms = round((time.time() - start_time) * 1000, 2)
        
        coverage_length = sum(seg.length for seg in path_segments if seg.segment_type == 'coverage')
        transition_length = sum(seg.length for seg in path_segments if seg.segment_type == 'transition')
        total_length = coverage_length + transition_length
        
        wall_area = self.wall_width * self.wall_height
        obstacle_area = sum(obs.width * obs.height for obs in self.obstacles)
        coverage_area = wall_area - obstacle_area
        
        # Theoretical minimum path length (all parallel lines)
        theoretical_min = coverage_area / self.tool_width
        coverage_percentage = (theoretical_min / total_length * 100) if total_length > 0 else 0
        
        metadata = {
            'num_cells': len(cells),
            'total_length': total_length,
            'coverage_length': coverage_length,
            'transition_length': transition_length,
            'coverage_percentage': coverage_percentage,
            'execution_time_ms': execution_time_ms,
        }
        
        return path_segments, metadata
    
    def _decompose_cells(self) -> List[Cell]:
        """
        Phase 1: Decompose wall into cells using vertical sweep line.
        
        Algorithm:
        1. Identify critical x-coordinates (obstacle boundaries)
        2. Sort critical points
        3. Create vertical slices between critical points
        4. For each slice, identify free vertical spans (avoiding obstacles)
        """
        # Collect critical x-coordinates
        critical_x = [0, self.wall_width]
        
        for obs in self.obstacles:
            critical_x.append(obs.left)
            critical_x.append(obs.right)
        
        # Sort and remove duplicates
        critical_x = sorted(set(critical_x))
        
        cells = []
        cell_id = 0
        
        # Process each vertical slice
        for i in range(len(critical_x) - 1):
            x_left = critical_x[i]
            x_right = critical_x[i + 1]
            
            # Skip zero-width slices
            if x_right - x_left < 1e-6:
                continue
            
            # Find free vertical spans in this slice
            free_spans = self._find_free_vertical_spans(x_left, x_right)
            
            for y_bottom, y_top in free_spans:
                cells.append(Cell(
                    left=x_left,
                    right=x_right,
                    bottom=y_bottom,
                    top=y_top,
                    id=cell_id
                ))
                cell_id += 1
        
        return cells
    
    def _find_free_vertical_spans(self, x_left: float, x_right: float) -> List[Tuple[float, float]]:
        """
        Find free vertical spans in a vertical slice.
        Returns list of (y_bottom, y_top) tuples.
        """
        # Collect y-coordinates of obstacles that intersect this slice
        blocking_y = []
        
        for obs in self.obstacles:
            # Check if obstacle intersects this x-range
            if obs.right > x_left and obs.left < x_right:
                blocking_y.append((obs.bottom, obs.top))
        
        # Sort by bottom y-coordinate
        blocking_y.sort()
        
        # Find free spans
        free_spans = []
        current_y = 0
        
        for y_bottom, y_top in blocking_y:
            # Add free span before this obstacle
            if current_y < y_bottom - 1e-6:
                free_spans.append((current_y, y_bottom))
            current_y = max(current_y, y_top)
        
        # Add final free span
        if current_y < self.wall_height - 1e-6:
            free_spans.append((current_y, self.wall_height))
        
        return free_spans
    
    def _generate_boustrophedon_pattern(self, cell: Cell) -> List[PathSegment]:
        """
        Phase 2: Generate back-and-forth coverage pattern within a cell.
        
        Uses horizontal sweep (can be configured for vertical).
        """
        segments = []
        
        # Use effective tool width with overlap
        effective_width = self.tool_width - self.overlap_margin
        
        # Generate horizontal lines
        y = cell.bottom + self.tool_width / 2
        direction = 1  # 1 = left-to-right, -1 = right-to-left
        
        while y <= cell.top + 1e-6:
            if direction == 1:
                # Left to right
                segments.append(PathSegment(
                    start_x=cell.left,
                    start_y=y,
                    end_x=cell.right,
                    end_y=y,
                    segment_type='coverage',
                    cell_id=cell.id
                ))
            else:
                # Right to left
                segments.append(PathSegment(
                    start_x=cell.right,
                    start_y=y,
                    end_x=cell.left,
                    end_y=y,
                    segment_type='coverage',
                    cell_id=cell.id
                ))
            
            y += effective_width
            direction *= -1
        
        return segments
    
    def _optimize_cell_order(self, cells: List[Cell], 
                            cell_patterns: Dict[int, List[PathSegment]]) -> List[int]:
        """
        Phase 3: Optimize cell visiting order using greedy nearest-neighbor with 2-opt.
        
        This is a TSP variant considering entry/exit points.
        """
        if not cells:
            return []
        
        if len(cells) == 1:
            return [cells[0].id]
        
        # Greedy nearest-neighbor
        visited = set()
        order = []
        
        # Start with leftmost cell (bottom-left corner)
        current_cell = min(cells, key=lambda c: (c.left, c.bottom))
        order.append(current_cell.id)
        visited.add(current_cell.id)
        
        # Get exit point of current cell
        current_exit = self._get_exit_point(current_cell, cell_patterns[current_cell.id])
        
        while len(visited) < len(cells):
            # Find nearest unvisited cell
            nearest_cell = None
            min_distance = float('inf')
            
            for cell in cells:
                if cell.id in visited:
                    continue
                
                # Get entry point of candidate cell
                entry_point = self._get_entry_point(cell, cell_patterns[cell.id])
                
                # Calculate transition distance
                distance = math.sqrt(
                    (entry_point[0] - current_exit[0])**2 +
                    (entry_point[1] - current_exit[1])**2
                )
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_cell = cell
            
            if nearest_cell:
                order.append(nearest_cell.id)
                visited.add(nearest_cell.id)
                current_exit = self._get_exit_point(nearest_cell, cell_patterns[nearest_cell.id])
        
        # Apply 2-opt improvement
        order = self._two_opt_improve(order, cells, cell_patterns)
        
        return order
    
    def _get_entry_point(self, cell: Cell, pattern: List[PathSegment]) -> Tuple[float, float]:
        """Get the entry point (start of first segment) for a cell."""
        if pattern:
            first_seg = pattern[0]
            return (first_seg.start_x, first_seg.start_y)
        return cell.center
    
    def _get_exit_point(self, cell: Cell, pattern: List[PathSegment]) -> Tuple[float, float]:
        """Get the exit point (end of last segment) for a cell."""
        if pattern:
            last_seg = pattern[-1]
            return (last_seg.end_x, last_seg.end_y)
        return cell.center
    
    def _two_opt_improve(self, order: List[int], cells: List[Cell],
                        cell_patterns: Dict[int, List[PathSegment]]) -> List[int]:
        """
        Apply 2-opt local search to improve cell order.
        Swaps pairs of edges to reduce total path length.
        """
        improved = True
        best_order = order[:]
        
        # Create cell lookup
        cell_lookup = {cell.id: cell for cell in cells}
        
        iterations = 0
        max_iterations = 50
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            for i in range(1, len(best_order) - 1):
                for j in range(i + 1, len(best_order)):
                    # Try reversing segment [i:j]
                    new_order = best_order[:i] + best_order[i:j][::-1] + best_order[j:]
                    
                    # Calculate improvement
                    old_cost = self._calculate_order_cost(best_order, cell_lookup, cell_patterns)
                    new_cost = self._calculate_order_cost(new_order, cell_lookup, cell_patterns)
                    
                    if new_cost < old_cost:
                        best_order = new_order
                        improved = True
                        break
                
                if improved:
                    break
        
        return best_order
    
    def _calculate_order_cost(self, order: List[int], cell_lookup: Dict[int, Cell],
                             cell_patterns: Dict[int, List[PathSegment]]) -> float:
        """Calculate total transition cost for a cell order."""
        total_cost = 0
        
        for i in range(len(order) - 1):
            current_cell = cell_lookup[order[i]]
            next_cell = cell_lookup[order[i + 1]]
            
            current_exit = self._get_exit_point(current_cell, cell_patterns[order[i]])
            next_entry = self._get_entry_point(next_cell, cell_patterns[order[i + 1]])
            
            distance = math.sqrt(
                (next_entry[0] - current_exit[0])**2 +
                (next_entry[1] - current_exit[1])**2
            )
            total_cost += distance
        
        return total_cost
    
    def _assemble_path(self, cells: List[Cell], 
                      cell_patterns: Dict[int, List[PathSegment]],
                      cell_order: List[int]) -> List[PathSegment]:
        """
        Phase 4: Assemble complete path with transitions between cells.
        """
        path_segments = []
        cell_lookup = {cell.id: cell for cell in cells}
        
        for i, cell_id in enumerate(cell_order):
            # Add coverage pattern for this cell
            pattern = cell_patterns[cell_id]
            path_segments.extend(pattern)
            
            # Add transition to next cell
            if i < len(cell_order) - 1:
                next_cell_id = cell_order[i + 1]
                
                current_exit = self._get_exit_point(cell_lookup[cell_id], pattern)
                next_entry = self._get_entry_point(cell_lookup[next_cell_id], 
                                                   cell_patterns[next_cell_id])
                
                # Add transition segment
                path_segments.append(PathSegment(
                    start_x=current_exit[0],
                    start_y=current_exit[1],
                    end_x=next_entry[0],
                    end_y=next_entry[1],
                    segment_type='transition',
                    cell_id=None
                ))
        
        return path_segments
