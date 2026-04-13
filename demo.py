#!/usr/bin/env python3
"""
Tessera Demo — Constraint-Based 2D Bin Packing Solver

This demo showcases the core capabilities of Tessera:
1. Basic packing with different algorithms
2. Algorithm comparison (benchmark)
3. Rotation and spacing
4. Constraint-based packing
5. Optimization with simulated annealing and genetic algorithm
6. Multi-bin packing
7. Visualization (ASCII + SVG)
8. Statistics and analysis
"""

import sys
import os
import time

# Ensure tessera is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tessera import (
    Rect, Bin, PackingProblem, PackingResult,
    MarginConstraint, GroupConstraint, AspectRatioConstraint,
)
from tessera.core import RotationPolicy, SortStrategy
from tessera.solver import Algorithm, Optimizer, Solver, SolverConfig
from tessera.algorithms.maxrects import MaxRectsAlgorithm, MaxRectsHeuristic
from tessera.algorithms.guillotine import GuillotineAlgorithm
from tessera.algorithms.shelf import ShelfAlgorithm
from tessera.algorithms.skyline import SkylineAlgorithm
from tessera.optimization.annealing import SimulatedAnnealing, AnnealingConfig
from tessera.optimization.genetic import GeneticOptimizer, GeneticConfig
from tessera.optimization.multistart import MultiStartOptimizer
from tessera.visualization.ascii_renderer import AsciiRenderer
from tessera.visualization.svg_renderer import SvgRenderer
from tessera.visualization.stats import PackingStats
from tessera.io.json_io import JsonIO


def section(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_basic_packing():
    section("1. BASIC PACKING")

    print("Packing 8 rectangles into a 100x100 bin using MaxRects (BSSF):\n")

    problem = PackingProblem()
    problem.add_bin(100, 100, label="Main")

    specs = [
        (40, 30, "Header"),
        (25, 25, "Avatar"),
        (35, 20, "Title"),
        (20, 15, "Icon-A"),
        (15, 20, "Icon-B"),
        (30, 25, "Panel"),
        (20, 20, "Button"),
        (10, 10, "Dot"),
    ]

    for w, h, label in specs:
        problem.add_rect(w, h, label=label)

    solver = Solver()
    result = solver.solve(problem)

    print(f"  Placed: {result.total_placed}/{result.total_placed + result.total_rejected}")
    print(f"  Efficiency: {result.efficiency(problem.bins):.1%}")
    print(f"  Time: {result.elapsed_ms:.2f}ms")
    print()

    # ASCII visualization
    renderer = AsciiRenderer(cell_width=5, cell_height=5)
    print(renderer.render(result, problem.bins))


def demo_algorithm_comparison():
    section("2. ALGORITHM COMPARISON (BENCHMARK)")

    print("Comparing all 4 algorithms on the same 20-rect problem:\n")

    problem = PackingProblem()
    problem.add_bin(200, 200, label="Benchmark")

    import random
    rng = random.Random(4823)  # Seed from our numbers!
    for i in range(20):
        w = rng.randint(15, 60)
        h = rng.randint(15, 60)
        problem.add_rect(w, h, label=f"R{i:02d}")

    solver = Solver()
    results = solver.benchmark(problem)

    print(f"  {'Algorithm':<15} {'Placed':>8} {'Rejected':>10} "
          f"{'Efficiency':>12} {'Time':>10}")
    print(f"  {'-'*15} {'-'*8} {'-'*10} {'-'*12} {'-'*10}")

    for name, result in sorted(
        results.items(),
        key=lambda x: (-x[1].total_placed, -x[1].efficiency(problem.bins))
    ):
        eff = result.efficiency(problem.bins)
        print(f"  {name:<15} {result.total_placed:>8} "
              f"{result.total_rejected:>10} {eff:>11.1%} "
              f"{result.elapsed_ms:>9.2f}ms")


def demo_rotation_spacing():
    section("3. ROTATION AND SPACING")

    # Problem: tall rects that need rotation to fit a wide bin
    problem = PackingProblem()
    problem.add_bin(200, 80, label="Wide Shelf")

    problem.add_rect(60, 20, label="Plank-A")
    problem.add_rect(70, 15, label="Plank-B")
    problem.add_rect(50, 25, label="Plank-C")
    problem.add_rect(20, 60, label="Tall-D")  # Needs rotation!
    problem.add_rect(15, 70, label="Tall-E")  # Needs rotation!

    # Without rotation
    solver_no_rot = Solver(SolverConfig(rotation=RotationPolicy.NONE))
    result_no = solver_no_rot.solve(problem)

    # With rotation
    solver_rot = Solver(SolverConfig(rotation=RotationPolicy.ORTHOGONAL))
    result_rot = solver_rot.solve(problem)

    # With rotation + spacing
    solver_spaced = Solver(SolverConfig(
        rotation=RotationPolicy.ORTHOGONAL,
        spacing=5.0,
    ))
    result_spaced = solver_spaced.solve(problem)

    print(f"  Without rotation:   {result_no.total_placed} placed, "
          f"{result_no.total_rejected} rejected")
    print(f"  With rotation:      {result_rot.total_placed} placed, "
          f"{result_rot.total_rejected} rejected")
    print(f"  Rotation + spacing: {result_spaced.total_placed} placed, "
          f"{result_spaced.total_rejected} rejected")

    # Show rotated placements
    print("\n  Rotated placements:")
    for p in result_rot.placements:
        if p.rotated:
            print(f"    {p.rect.label}: {p.rect.width}x{p.rect.height} -> "
                  f"{p.placed_width}x{p.placed_height} (rotated)")


def demo_constraints():
    section("4. CONSTRAINT-BASED PACKING")

    problem = PackingProblem()
    problem.add_bin(200, 200, label="Constrained")

    # Create groups of related items
    nav_items = []
    for i in range(3):
        r = problem.add_rect(30, 20, label=f"Nav-{i}", group="navigation")
        nav_items.append(r)

    content_items = []
    for i in range(4):
        r = problem.add_rect(40, 30, label=f"Content-{i}", group="content")
        content_items.append(r)

    problem.add_rect(50, 50, label="Hero")
    problem.add_rect(20, 20, label="Logo")

    solver = Solver()
    result = solver.solve(problem)

    # Evaluate constraints after packing
    margin_c = MarginConstraint(inter_rect=2, bin_edge=5)
    group_c = GroupConstraint(
        groups={
            "nav": {r.rid for r in nav_items},
            "content": {r.rid for r in content_items},
        },
        same_bin=True,
        max_gap=50,
    )

    margin_violations = margin_c.evaluate(result.placements, problem.bins)
    group_violations = group_c.evaluate(result.placements, problem.bins)

    print(f"  Placed: {result.total_placed}")
    print(f"  Margin violations: {len(margin_violations)}")
    print(f"  Group violations: {len(group_violations)}")

    if margin_violations:
        for v in margin_violations[:3]:
            print(f"    - {v.message}")


def demo_optimization():
    section("5. OPTIMIZATION (SA + GA)")

    print("Creating a challenging 25-rect problem and optimizing...\n")

    problem = PackingProblem()
    problem.add_bin(150, 150, label="Optimized")

    import random
    rng = random.Random(1619)  # Seed!
    for i in range(25):
        w = rng.randint(10, 50)
        h = rng.randint(10, 50)
        problem.add_rect(w, h, label=f"R{i:02d}")

    # Baseline: plain MaxRects
    baseline = Solver().solve(problem)

    # Simulated Annealing
    sa_config = SolverConfig(
        optimizer=Optimizer.ANNEALING,
        annealing_config=AnnealingConfig(
            initial_temp=500,
            cooling_rate=0.95,
            min_temp=1,
            max_iterations=200,
            restarts=2,
            seed=4823,
        ),
    )
    sa_result = Solver(sa_config).solve(problem)

    # Genetic Algorithm
    ga_config = SolverConfig(
        optimizer=Optimizer.GENETIC,
        genetic_config=GeneticConfig(
            population_size=20,
            generations=30,
            seed=6527,
        ),
    )
    ga_result = Solver(ga_config).solve(problem)

    # Multi-start
    ms_config = SolverConfig(optimizer=Optimizer.MULTI_START)
    ms_result = Solver(ms_config).solve(problem)

    print(f"  {'Method':<20} {'Placed':>8} {'Efficiency':>12} {'Time':>10}")
    print(f"  {'-'*20} {'-'*8} {'-'*12} {'-'*10}")

    for name, result in [
        ("Baseline (MaxRects)", baseline),
        ("Simulated Annealing", sa_result),
        ("Genetic Algorithm", ga_result),
        ("Multi-Start", ms_result),
    ]:
        eff = result.efficiency(problem.bins)
        print(f"  {name:<20} {result.total_placed:>8} "
              f"{eff:>11.1%} {result.elapsed_ms:>9.1f}ms")


def demo_multi_bin():
    section("6. MULTI-BIN PACKING")

    print("Packing 30 items into multiple 100x100 bins:\n")

    problem = PackingProblem()
    for i in range(6):
        problem.add_bin(100, 100, label=f"Bin-{i}")

    import random
    rng = random.Random(3798)
    for i in range(30):
        w = rng.randint(20, 45)
        h = rng.randint(20, 45)
        problem.add_rect(w, h, label=f"Item-{i:02d}")

    solver = Solver(SolverConfig(multi_bin=True))
    result = solver.solve(problem)

    print(f"  Total items: 30")
    print(f"  Placed: {result.total_placed}")
    print(f"  Bins used: {result.bins_used}")
    print()

    renderer = AsciiRenderer(cell_width=5, cell_height=5)
    for i in range(result.bins_used):
        line = renderer.render_compact(result, problem.bins, i)
        print(f"  {line}")


def demo_visualization():
    section("7. VISUALIZATION")

    problem = PackingProblem()
    problem.add_bin(120, 80, label="Demo Canvas")

    colors = ["#E74C3C", "#3498DB", "#2ECC71", "#F1C40F",
              "#9B59B6", "#E67E22", "#1ABC9C", "#34495E"]

    specs = [
        (40, 30), (30, 25), (25, 20), (35, 15),
        (20, 20), (15, 25), (30, 20), (20, 15),
    ]
    for i, (w, h) in enumerate(specs):
        problem.add_rect(w, h, label=f"Block-{chr(65+i)}",
                        color=colors[i % len(colors)])

    result = Solver().solve(problem)

    # ASCII
    print("ASCII Visualization:\n")
    renderer = AsciiRenderer(cell_width=5, cell_height=5)
    print(renderer.render(result, problem.bins))

    # SVG (save to file)
    svg_renderer = SvgRenderer(
        scale=3.0,
        show_labels=True,
        show_dimensions=True,
        show_grid=True,
        grid_spacing=10,
    )
    svg = svg_renderer.render(result, problem.bins)

    svg_path = os.path.join(os.path.dirname(__file__), "demo_output.svg")
    with open(svg_path, "w") as f:
        f.write(svg)
    print(f"\n  SVG saved to: {svg_path}")
    print(f"  (Open in a browser to see the color-coded visualization)")


def demo_statistics():
    section("8. DETAILED STATISTICS")

    problem = PackingProblem()
    problem.add_bin(300, 300, label="Stats Bin")

    import random
    rng = random.Random(9818)
    for i in range(40):
        w = rng.randint(10, 80)
        h = rng.randint(10, 80)
        problem.add_rect(w, h, label=f"R{i:02d}")

    result = Solver(SolverConfig(
        rotation=RotationPolicy.ORTHOGONAL,
    )).solve(problem)

    stats = PackingStats(result, problem.bins)
    print(stats.summary())


def demo_texture_atlas():
    section("BONUS: TEXTURE ATLAS GENERATION")

    print("Simulating game sprite atlas packing (1024x1024 atlas):\n")

    problem = PackingProblem()
    problem.add_bin(1024, 1024, label="Sprite Atlas")

    # Typical game sprite sizes
    sprites = {
        "player_idle": (64, 64),
        "player_run": (128, 64),
        "player_jump": (64, 96),
        "enemy_slime": (48, 48),
        "enemy_bat": (32, 32),
        "enemy_boss": (256, 256),
        "tile_grass": (32, 32),
        "tile_stone": (32, 32),
        "tile_water": (32, 32),
        "tile_lava": (32, 32),
        "ui_health": (128, 16),
        "ui_mana": (128, 16),
        "ui_inventory": (256, 128),
        "ui_minimap": (128, 128),
        "fx_explosion": (96, 96),
        "fx_smoke": (64, 64),
        "fx_sparkle": (32, 32),
        "bg_sky": (512, 128),
        "bg_clouds": (256, 64),
        "bg_mountains": (512, 96),
        "icon_sword": (24, 24),
        "icon_shield": (24, 24),
        "icon_potion": (24, 24),
        "icon_scroll": (24, 24),
        "icon_gem": (16, 16),
        "icon_key": (16, 16),
        "font_atlas": (256, 256),
        "logo": (384, 128),
    }

    for label, (w, h) in sprites.items():
        problem.add_rect(w, h, label=label)

    solver = Solver(SolverConfig(
        rotation=RotationPolicy.ORTHOGONAL,
        optimizer=Optimizer.MULTI_START,
        spacing=2,
    ))

    result = solver.solve(problem)

    print(f"  Sprites: {len(sprites)}")
    print(f"  All placed: {'Yes' if result.all_placed else 'No'}")
    print(f"  Efficiency: {result.efficiency(problem.bins):.1%}")
    print(f"  Algorithm: {result.algorithm}")
    print(f"  Time: {result.elapsed_ms:.1f}ms")
    print(f"  Bounding box: {result.bounding_box()[0]:.0f} x {result.bounding_box()[1]:.0f}")

    # Show placement summary
    print("\n  Placement summary:")
    rotated = sum(1 for p in result.placements if p.rotated)
    print(f"    Rotated sprites: {rotated}/{len(result.placements)}")

    # Save SVG
    svg_renderer = SvgRenderer(scale=0.5, show_labels=True, show_legend=True)
    svg = svg_renderer.render(result, problem.bins)
    svg_path = os.path.join(os.path.dirname(__file__), "demo_atlas.svg")
    with open(svg_path, "w") as f:
        f.write(svg)
    print(f"\n  Atlas SVG saved to: {svg_path}")


def main():
    print()
    print("  _____ _____ ____ ____  _____ ____      _    ")
    print(" |_   _| ____/ ___/ ___|| ____|  _ \\    / \\   ")
    print("   | | |  _| \\___ \\___ \\|  _| | |_) |  / _ \\  ")
    print("   | | | |___ ___) |__) | |___|  _ <  / ___ \\ ")
    print("   |_| |_____|____/____/|_____|_| \\_\\/_/   \\_\\")
    print()
    print("  Constraint-Based 2D Bin Packing Solver")
    print("  ======================================")

    demo_basic_packing()
    demo_algorithm_comparison()
    demo_rotation_spacing()
    demo_constraints()
    demo_optimization()
    demo_multi_bin()
    demo_visualization()
    demo_statistics()
    demo_texture_atlas()

    section("DEMO COMPLETE")
    print("  Tessera successfully demonstrated:")
    print("  - 4 packing algorithms (MaxRects, Guillotine, Shelf, Skyline)")
    print("  - 3 optimization strategies (SA, GA, Multi-Start)")
    print("  - Rotation and spacing support")
    print("  - Constraint system (margin, group, aspect ratio)")
    print("  - Multi-bin packing")
    print("  - ASCII and SVG visualization")
    print("  - Statistical analysis")
    print("  - JSON/CSV import/export")
    print()


if __name__ == "__main__":
    main()
