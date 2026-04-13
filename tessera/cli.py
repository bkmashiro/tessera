"""
Command-line interface for Tessera.

Provides commands for solving packing problems, benchmarking algorithms,
and generating visualizations from the terminal.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

from tessera.core import (
    Bin, PackingProblem, Rect, RotationPolicy, SortStrategy,
)
from tessera.solver import Algorithm, Optimizer, Solver, SolverConfig
from tessera.algorithms.maxrects import MaxRectsHeuristic
from tessera.visualization.ascii_renderer import AsciiRenderer
from tessera.visualization.svg_renderer import SvgRenderer
from tessera.visualization.stats import PackingStats
from tessera.io.json_io import JsonIO
from tessera.io.csv_io import CsvIO


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="tessera",
        description="Tessera — 2D Bin Packing Solver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Solve a problem from JSON
  tessera solve problem.json --algorithm maxrects --output result.json

  # Generate SVG visualization
  tessera solve problem.json --svg output.svg

  # Benchmark all algorithms
  tessera benchmark problem.json

  # Quick pack from dimensions
  tessera quick 100x100 --rects "20x30,15x25,40x10,30x30"

  # Import from CSV
  tessera solve --csv rects.csv --bin 1024x1024
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Solve command
    solve_parser = subparsers.add_parser("solve", help="Solve a packing problem")
    solve_parser.add_argument("input", nargs="?", help="Input JSON problem file")
    solve_parser.add_argument("--csv", help="Import rects from CSV file")
    solve_parser.add_argument("--bin", help="Bin dimensions WxH (e.g., 1024x1024)")
    solve_parser.add_argument(
        "--algorithm", "-a",
        choices=["maxrects", "guillotine", "shelf", "skyline"],
        default="maxrects",
        help="Packing algorithm",
    )
    solve_parser.add_argument(
        "--heuristic",
        choices=["bssf", "blsf", "baf", "cp", "bl"],
        default="bssf",
        help="MaxRects heuristic",
    )
    solve_parser.add_argument(
        "--optimizer", "-O",
        choices=["none", "multistart", "annealing", "genetic"],
        default="none",
        help="Optimization strategy",
    )
    solve_parser.add_argument("--rotation", "-r", action="store_true", help="Allow rotation")
    solve_parser.add_argument("--spacing", "-s", type=float, default=0.0, help="Spacing between rects")
    solve_parser.add_argument("--multi-bin", "-m", action="store_true", help="Use multiple bins")
    solve_parser.add_argument("--output", "-o", help="Output JSON result file")
    solve_parser.add_argument("--svg", help="Output SVG file")
    solve_parser.add_argument("--ascii", action="store_true", help="Show ASCII visualization")
    solve_parser.add_argument("--stats", action="store_true", help="Show detailed statistics")
    solve_parser.add_argument("--seed", type=int, help="Random seed")

    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Benchmark algorithms")
    bench_parser.add_argument("input", help="Input JSON problem file")
    bench_parser.add_argument("--output", "-o", help="Output JSON results file")

    # Quick command
    quick_parser = subparsers.add_parser("quick", help="Quick pack from dimensions")
    quick_parser.add_argument("bin_size", help="Bin dimensions WxH")
    quick_parser.add_argument("--rects", required=True, help="Comma-separated WxH dimensions")
    quick_parser.add_argument("--rotation", "-r", action="store_true", help="Allow rotation")
    quick_parser.add_argument("--spacing", "-s", type=float, default=0.0)
    quick_parser.add_argument("--ascii", action="store_true", help="Show ASCII visualization")
    quick_parser.add_argument("--svg", help="Output SVG file")

    # Generate command (random problem generation for testing)
    gen_parser = subparsers.add_parser("generate", help="Generate a random problem")
    gen_parser.add_argument("--count", "-n", type=int, default=20, help="Number of rectangles")
    gen_parser.add_argument("--bin", default="1024x1024", help="Bin dimensions WxH")
    gen_parser.add_argument("--min-size", type=int, default=10, help="Min rect dimension")
    gen_parser.add_argument("--max-size", type=int, default=200, help="Max rect dimension")
    gen_parser.add_argument("--output", "-o", required=True, help="Output JSON file")
    gen_parser.add_argument("--seed", type=int, help="Random seed")

    return parser


def parse_dimensions(dim_str: str) -> tuple:
    """Parse 'WxH' string into (width, height)."""
    parts = dim_str.lower().split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid dimensions: {dim_str}. Expected WxH format.")
    return float(parts[0]), float(parts[1])


def cmd_solve(args) -> int:
    """Execute the solve command."""
    # Build problem
    if args.input:
        problem = JsonIO.load_problem(args.input)
    elif args.csv and args.bin:
        rects = CsvIO.import_rects(args.csv)
        bw, bh = parse_dimensions(args.bin)
        problem = PackingProblem(rects=rects, bins=[Bin(width=bw, height=bh)])
    elif args.bin:
        print("Error: --bin requires either --csv or an input file", file=sys.stderr)
        return 1
    else:
        print("Error: provide an input file or --csv with --bin", file=sys.stderr)
        return 1

    # Configure solver
    algo_map = {
        "maxrects": Algorithm.MAXRECTS,
        "guillotine": Algorithm.GUILLOTINE,
        "shelf": Algorithm.SHELF,
        "skyline": Algorithm.SKYLINE,
    }
    opt_map = {
        "none": Optimizer.NONE,
        "multistart": Optimizer.MULTI_START,
        "annealing": Optimizer.ANNEALING,
        "genetic": Optimizer.GENETIC,
    }
    heuristic_map = {
        "bssf": MaxRectsHeuristic.BSSF,
        "blsf": MaxRectsHeuristic.BLSF,
        "baf": MaxRectsHeuristic.BAF,
        "cp": MaxRectsHeuristic.CP,
        "bl": MaxRectsHeuristic.BL,
    }

    config = SolverConfig(
        algorithm=algo_map[args.algorithm],
        optimizer=opt_map[args.optimizer],
        rotation=RotationPolicy.ORTHOGONAL if args.rotation else RotationPolicy.NONE,
        spacing=args.spacing,
        multi_bin=args.multi_bin,
        maxrects_heuristic=heuristic_map.get(args.heuristic, MaxRectsHeuristic.BSSF),
        seed=args.seed,
    )

    solver = Solver(config)
    result = solver.solve(problem)

    # Output
    print(f"\nPlaced: {result.total_placed}/{result.total_placed + result.total_rejected}")
    if problem.bins:
        print(f"Efficiency: {result.efficiency(problem.bins):.1%}")
    print(f"Bins used: {result.bins_used}")
    print(f"Time: {result.elapsed_ms:.1f}ms")

    if result.rejected:
        print(f"\nRejected ({len(result.rejected)}):")
        for r in result.rejected[:10]:
            print(f"  {r}")

    if args.ascii:
        renderer = AsciiRenderer()
        print("\n" + renderer.render_all_bins(result, problem.bins))

    if args.stats:
        stats = PackingStats(result, problem.bins)
        print("\n" + stats.summary())

    if args.output:
        JsonIO.save_result(result, args.output)
        print(f"\nResult saved to {args.output}")

    if args.svg:
        renderer = SvgRenderer(scale=1.0, show_dimensions=True)
        svg = renderer.render_all_bins(result, problem.bins)
        with open(args.svg, "w") as f:
            f.write(svg)
        print(f"SVG saved to {args.svg}")

    return 0


def cmd_benchmark(args) -> int:
    """Execute the benchmark command."""
    problem = JsonIO.load_problem(args.input)

    print(f"Benchmarking {len(problem.rects)} rects in "
          f"{len(problem.bins)} bin(s)...\n")

    solver = Solver()
    results = solver.benchmark(problem)

    # Display results
    print(f"{'Algorithm':<15} {'Placed':>8} {'Rejected':>10} "
          f"{'Efficiency':>12} {'Time (ms)':>12}")
    print("-" * 60)

    for name, result in sorted(results.items(), key=lambda x: -x[1].efficiency(problem.bins)):
        eff = result.efficiency(problem.bins)
        print(f"{name:<15} {result.total_placed:>8} {result.total_rejected:>10} "
              f"{eff:>11.1%} {result.elapsed_ms:>12.1f}")

    if args.output:
        data = {name: JsonIO.export_result(r) for name, r in results.items()}
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nResults saved to {args.output}")

    return 0


def cmd_quick(args) -> int:
    """Execute the quick command."""
    bw, bh = parse_dimensions(args.bin_size)

    rects = []
    for i, dim_str in enumerate(args.rects.split(",")):
        w, h = parse_dimensions(dim_str.strip())
        rects.append(Rect(width=w, height=h, label=f"R{i+1}"))

    problem = PackingProblem(
        rects=rects,
        bins=[Bin(width=bw, height=bh)],
    )

    config = SolverConfig(
        rotation=RotationPolicy.ORTHOGONAL if args.rotation else RotationPolicy.NONE,
        spacing=args.spacing,
    )

    solver = Solver(config)
    result = solver.solve(problem)

    print(f"Placed: {result.total_placed}/{len(rects)}")
    print(f"Efficiency: {result.efficiency(problem.bins):.1%}")

    if args.ascii:
        renderer = AsciiRenderer()
        print("\n" + renderer.render(result, problem.bins))

    if args.svg:
        renderer = SvgRenderer(show_dimensions=True)
        svg = renderer.render(result, problem.bins)
        with open(args.svg, "w") as f:
            f.write(svg)
        print(f"SVG saved to {args.svg}")

    return 0


def cmd_generate(args) -> int:
    """Execute the generate command."""
    import random

    rng = random.Random(args.seed)
    bw, bh = parse_dimensions(args.bin)

    rects = []
    for i in range(args.count):
        w = rng.randint(args.min_size, args.max_size)
        h = rng.randint(args.min_size, args.max_size)
        rects.append(Rect(width=w, height=h, label=f"rect_{i+1}"))

    problem = PackingProblem(
        rects=rects,
        bins=[Bin(width=bw, height=bh)],
    )

    JsonIO.save_problem(problem, args.output)
    total_area = sum(r.area for r in rects)
    print(f"Generated {args.count} rects (total area: {total_area:.0f})")
    print(f"Bin: {bw}x{bh} (area: {bw*bh:.0f})")
    print(f"Fill ratio: {total_area / (bw * bh):.1%}")
    print(f"Saved to {args.output}")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "solve": cmd_solve,
        "benchmark": cmd_benchmark,
        "quick": cmd_quick,
        "generate": cmd_generate,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
