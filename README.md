# Tessera

> Constraint-based 2D bin packing solver with metaheuristic optimization

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

## What is this?

Tessera is a 2D rectangle bin packing library that goes well beyond basic greedy placement. It implements four industry-standard packing algorithms -- MaxRects, Guillotine, Shelf, and Skyline -- each with multiple heuristic variants, and layers on a rich constraint system and metaheuristic optimizers (simulated annealing, genetic algorithm, multi-start) to push packing efficiency higher than any single-pass algorithm can achieve.

The core problem Tessera solves is: given a set of rectangles with varying dimensions, pack them into one or more fixed-size bins while minimizing wasted space and respecting constraints like minimum margins, group proximity, region restrictions, and grid alignment. This shows up constantly in practice -- texture atlas generation for games, CNC sheet cutting, PCB component placement, CSS sprite sheets, and warehouse container loading.

What makes Tessera interesting is the combination of classical packing algorithms with constraint satisfaction and optimization. You can declare that navigation elements must stay within a specific region, enforce minimum spacing between items, require certain groups of rectangles to cluster together, and then let simulated annealing or a genetic algorithm search the permutation space to find a layout that satisfies all constraints while maximizing bin utilization.

## Features

- **Four packing algorithms**: MaxRects (BSSF/BLSF/BAF/ContactPoint/BottomLeft), Guillotine (6 choice + 7 split heuristics), Shelf (FirstFit/NextFit/BestWidth/WorstWidth), Skyline (BottomLeft/BestFit)
- **Metaheuristic optimization**: Simulated annealing with configurable cooling schedule, genetic algorithm with order crossover (OX) and tournament selection, multi-start random restarts
- **Constraint system**: Margin constraints (inter-rect and bin-edge), alignment constraints (grid snapping, axis alignment), group constraints (cluster proximity, same-bin enforcement), region constraints, fixed positions, aspect ratio limits
- **Rotation support**: Optional 90-degree rotation with per-rectangle control
- **Multi-bin packing**: Overflow to additional bins when items don't fit
- **Configurable spacing**: Minimum gap between packed rectangles
- **8 sort strategies**: Area, perimeter, width, height, max side, aspect ratio, short side, long side -- all descending, with priority override
- **Visualization**: SVG renderer with color-coded layouts, labels, dimensions, grid overlay, and legend; ASCII renderer for terminal output
- **I/O**: JSON and CSV import/export for problems and results
- **CLI**: Full command-line interface for solving, benchmarking, quick packing, and random problem generation
- **Built-in benchmarking**: Compare all algorithms on the same problem in one call

## Installation

```bash
git clone https://github.com/bkmashiro/tessera.git
cd tessera
pip install -e .
```

## Quick Start

```python
from tessera import Rect, Bin, PackingProblem
from tessera.solver import Solver, SolverConfig, Algorithm, Optimizer

# Define the problem
problem = PackingProblem()
problem.add_bin(1024, 1024, label="Sprite Atlas")
problem.add_rect(256, 256, label="boss")
problem.add_rect(128, 64, label="player_run")
problem.add_rect(64, 64, label="player_idle")
problem.add_rect(32, 32, label="tile_grass")
problem.add_rect(512, 128, label="background")

# Solve with rotation and optimization
solver = Solver(SolverConfig(
    algorithm=Algorithm.MAXRECTS,
    optimizer=Optimizer.ANNEALING,
    rotation=RotationPolicy.ORTHOGONAL,
    spacing=2,
))
result = solver.solve(problem)

print(f"Placed: {result.total_placed}, Efficiency: {result.efficiency(problem.bins):.1%}")
```

## Usage

### Algorithm Selection and Benchmarking

Tessera includes four packing algorithms, each suited to different workloads. Run them all at once to find the best fit:

```python
solver = Solver()
results = solver.benchmark(problem)

for name, result in sorted(results.items(), key=lambda x: -x[1].efficiency(problem.bins)):
    print(f"{name}: {result.efficiency(problem.bins):.1%} efficiency")
```

### Fluent API

Build solver configurations with method chaining:

```python
from tessera.core import RotationPolicy, SortStrategy

result = (Solver()
    .with_algorithm(Algorithm.SKYLINE)
    .with_rotation(RotationPolicy.ORTHOGONAL)
    .with_spacing(4.0)
    .with_optimizer(Optimizer.GENETIC)
    .with_seed(42)
    .solve(problem))
```

### Constraints

Apply spatial and grouping constraints to control placement:

```python
from tessera import MarginConstraint, GroupConstraint, RegionConstraint

# Minimum 5px margin from bin edges, 2px between rectangles
margin = MarginConstraint(inter_rect=2, bin_edge=5)

# Navigation items must stay within the top 200px
region = RegionConstraint(x=0, y=0, width=1024, height=200, rect_ids={nav.rid for nav in nav_rects})

# Group related items together (max 50px gap)
group = GroupConstraint(
    groups={"nav": {r.rid for r in nav_rects}, "content": {r.rid for r in content_rects}},
    same_bin=True,
    max_gap=50,
)

solver = Solver()
solver.with_constraint(margin).with_constraint(region).with_constraint(group)
result = solver.solve(problem)
```

### Multi-Bin Packing

When items don't fit in a single bin, Tessera overflows to additional bins:

```python
problem = PackingProblem()
for i in range(6):
    problem.add_bin(100, 100, label=f"Sheet-{i}")
for i in range(30):
    problem.add_rect(random.randint(20, 45), random.randint(20, 45))

solver = Solver(SolverConfig(multi_bin=True))
result = solver.solve(problem)
print(f"Bins used: {result.bins_used}")
```

### SVG Visualization

Generate publication-quality SVG output:

```python
from tessera.visualization.svg_renderer import SvgRenderer

renderer = SvgRenderer(scale=2.0, show_labels=True, show_dimensions=True, show_grid=True)
svg = renderer.render(result, problem.bins)
with open("atlas.svg", "w") as f:
    f.write(svg)
```

### CLI

```bash
# Solve from JSON
tessera solve problem.json --algorithm maxrects --rotation --svg output.svg

# Quick pack from dimensions
tessera quick 1024x1024 --rects "256x256,128x64,64x64,32x32" --rotation --ascii

# Benchmark all algorithms
tessera benchmark problem.json

# Generate random test problems
tessera generate --count 50 --bin 1024x1024 --output test_problem.json
```

## Architecture

```
tessera/
    core.py              # Rect, Bin, Placement, PackingResult, PackingProblem
    solver.py            # High-level Solver with fluent API
    cli.py               # Command-line interface
    algorithms/
        base.py          # BaseAlgorithm ABC with multi-bin logic
        maxrects.py      # MaxRects with 5 heuristic variants
        guillotine.py    # Guillotine with 6 choice + 7 split strategies
        shelf.py         # Shelf-based packing
        skyline.py       # Skyline bottom-left packing
    constraints/
        base.py          # Constraint ABC, ConstraintViolation
        spatial.py       # Margin, alignment, region, fixed position, min distance
        grouping.py      # Group proximity constraints
        ratio.py         # Aspect ratio constraints
    optimization/
        objective.py     # Objective function for scoring packings
        annealing.py     # Simulated annealing (permutation search)
        genetic.py       # Genetic algorithm with OX crossover
        multistart.py    # Multi-start random restarts
    visualization/
        svg_renderer.py  # Color-coded SVG output with labels and legend
        ascii_renderer.py# Terminal-friendly text rendering
        stats.py         # Packing statistics and analysis
    io/
        json_io.py       # JSON import/export
        csv_io.py        # CSV import/export
```

The `Solver` is the main entry point. It takes a `PackingProblem` (rectangles + bins), selects the configured algorithm, optionally wraps it in an optimizer, and returns a `PackingResult` with placements, rejection list, and timing statistics. Constraints are evaluated post-hoc or used by optimizers as penalty terms in the objective function.

## Examples

Run the comprehensive demo to see all features in action:

```bash
python demo.py
```

This exercises basic packing, algorithm comparison, rotation, constraints, optimization (SA + GA), multi-bin packing, ASCII/SVG visualization, statistics, and a realistic texture atlas scenario.

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a PR. Run the test suite with:

```bash
python -m pytest tests/ -v
```

## License

MIT
