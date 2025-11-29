# Coverage Path Planning Algorithm

## Overview

This project implements a **Boustrophedon Cellular Decomposition** algorithm for generating optimal coverage paths on walls with obstacles. The algorithm ensures complete coverage while minimizing travel distance between cells.

## Algorithm Steps

The algorithm operates in four main phases:

1. **Cell Decomposition**: Partition the wall space into rectangular cells around obstacles
2. **Pattern Generation**: Generate zig-zag (boustrophedon) coverage patterns within each cell
3. **TSP Optimization**: Optimize the order of visiting cells to minimize transitions
4. **Path Assembly**: Combine cell patterns with transition segments into a complete path

---

## Pseudocode

```
ALGORITHM: Boustrophedon Coverage Path Planning

INPUT: wall_width, wall_height, tool_width, obstacles[]
OUTPUT: path_segments[], metadata

BEGIN
    // ============================================
    // PHASE 1: CELL DECOMPOSITION
    // ============================================
    
    Step 1.1: Collect critical x-coordinates
        critical_x = [0, wall_width]
        FOR EACH obstacle IN obstacles:
            critical_x.ADD(obstacle.left)
            critical_x.ADD(obstacle.right)
        critical_x = SORT(UNIQUE(critical_x))
    
    Step 1.2: Create vertical slices and find free spans
        cells = []
        cell_id = 0
        
        FOR i = 0 TO LENGTH(critical_x) - 2:
            x_left = critical_x[i]
            x_right = critical_x[i + 1]
            
            IF x_right - x_left < EPSILON:
                CONTINUE
            
            // Find obstacles intersecting this x-range
            blocking_y = []
            FOR EACH obstacle IN obstacles:
                IF obstacle.right > x_left AND obstacle.left < x_right:
                    blocking_y.APPEND((obstacle.bottom, obstacle.top))
            
            // Sort obstacles by y-coordinate
            blocking_y = SORT(blocking_y)
            
            // Find free vertical spans (gaps between obstacles)
            current_y = 0
            FOR EACH (y_bottom, y_top) IN blocking_y:
                IF current_y < y_bottom - EPSILON:
                    // Create cell for free span
                    cells.APPEND(Cell(x_left, x_right, current_y, y_bottom, cell_id))
                    cell_id = cell_id + 1
                current_y = MAX(current_y, y_top)
            
            // Add final cell to top of wall
            IF current_y < wall_height - EPSILON:
                cells.APPEND(Cell(x_left, x_right, current_y, wall_height, cell_id))
                cell_id = cell_id + 1
    
    // ============================================
    // PHASE 2: PATTERN GENERATION
    // ============================================
    
    Step 2.1: Generate zig-zag patterns for each cell
        cell_patterns = {}
        
        FOR EACH cell IN cells:
            segments = []
            effective_width = tool_width - overlap_margin
            y = cell.bottom + tool_width / 2
            direction = 1  // 1 = left-to-right, -1 = right-to-left
            
            WHILE y <= cell.top + EPSILON:
                IF direction == 1:
                    // Move left to right
                    segments.APPEND(PathSegment(
                        start = (cell.left, y),
                        end = (cell.right, y),
                        type = 'coverage'
                    ))
                ELSE:
                    // Move right to left
                    segments.APPEND(PathSegment(
                        start = (cell.right, y),
                        end = (cell.left, y),
                        type = 'coverage'
                    ))
                
                y = y + effective_width
                direction = direction * -1  // Alternate direction
            
            cell_patterns[cell.id] = segments
    
    // ============================================
    // PHASE 3: TSP OPTIMIZATION
    // ============================================
    
    Step 3.1: Greedy nearest-neighbor ordering
        visited = SET()
        cell_order = []
        
        // Start with leftmost cell
        current_cell = MIN(cells, key = (cell.left, cell.bottom))
        cell_order.APPEND(current_cell.id)
        visited.ADD(current_cell.id)
        current_exit = END_POINT_OF(cell_patterns[current_cell.id])
        
        WHILE LENGTH(visited) < LENGTH(cells):
            nearest_cell = NULL
            min_distance = INFINITY
            
            FOR EACH cell IN cells:
                IF cell.id IN visited:
                    CONTINUE
                
                entry_point = START_POINT_OF(cell_patterns[cell.id])
                distance = EUCLIDEAN_DISTANCE(entry_point, current_exit)
                
                IF distance < min_distance:
                    min_distance = distance
                    nearest_cell = cell
            
            IF nearest_cell != NULL:
                cell_order.APPEND(nearest_cell.id)
                visited.ADD(nearest_cell.id)
                current_exit = END_POINT_OF(cell_patterns[nearest_cell.id])
    
    Step 3.2: Apply 2-opt local improvement
        best_order = COPY(cell_order)
        improved = TRUE
        iterations = 0
        
        WHILE improved AND iterations < 50:
            improved = FALSE
            iterations = iterations + 1
            
            FOR i = 1 TO LENGTH(best_order) - 2:
                FOR j = i + 1 TO LENGTH(best_order) - 1:
                    // Try reversing segment [i:j]
                    new_order = best_order[0:i] + REVERSE(best_order[i:j]) + best_order[j:]
                    
                    old_cost = TOTAL_TRANSITION_DISTANCE(best_order, cells, cell_patterns)
                    new_cost = TOTAL_TRANSITION_DISTANCE(new_order, cells, cell_patterns)
                    
                    IF new_cost < old_cost:
                        best_order = new_order
                        improved = TRUE
                        BREAK
                
                IF improved:
                    BREAK
        
        cell_order = best_order
    
    // ============================================
    // PHASE 4: PATH ASSEMBLY
    // ============================================
    
    Step 4.1: Combine patterns with transitions
        path_segments = []
        cell_lookup = CREATE_LOOKUP(cells)
        
        FOR i = 0 TO LENGTH(cell_order) - 1:
            cell_id = cell_order[i]
            
            // Add all coverage segments for this cell
            pattern = cell_patterns[cell_id]
            path_segments.EXTEND(pattern)
            
            // Add transition to next cell (if exists)
            IF i < LENGTH(cell_order) - 1:
                next_cell_id = cell_order[i + 1]
                
                current_exit = END_POINT_OF(pattern)
                next_entry = START_POINT_OF(cell_patterns[next_cell_id])
                
                path_segments.APPEND(PathSegment(
                    start = current_exit,
                    end = next_entry,
                    type = 'transition'
                ))
    
    Step 4.2: Calculate metadata
        coverage_length = SUM(length of all 'coverage' segments)
        transition_length = SUM(length of all 'transition' segments)
        total_length = coverage_length + transition_length
        coverage_percentage = (theoretical_min / total_length) * 100
    
    RETURN path_segments, metadata
END
```

---

## Time Complexity

- **Cell Decomposition**: O(n²) where n is the number of obstacles
- **Pattern Generation**: O(m) where m is the number of cells
- **TSP Optimization**: O(k²) where k is the number of cells (with 2-opt)
- **Overall**: O(n² + k²) for typical scenarios
