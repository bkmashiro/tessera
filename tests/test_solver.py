"""Tests for the high-level Solver interface."""

import pytest
from tessera.core import Bin, PackingProblem, Rect, RotationPolicy, SortStrategy
from tessera.solver import Algorithm, Optimizer, Solver, SolverConfig


def make_problem():
    p = PackingProblem()
    p.add_bin(100, 100)
    for i in range(5):
        p.add_rect(20, 20, label=f"R{i}")
    return p


class TestSolverConfig:
    def test_defaults(self):
        config = SolverConfig()
        assert config.algorithm == Algorithm.MAXRECTS
        assert config.optimizer == Optimizer.NONE
        assert config.spacing == 0.0

    def test_custom(self):
        config = SolverConfig(
            algorithm=Algorithm.SKYLINE,
            spacing=5.0,
        )
        assert config.algorithm == Algorithm.SKYLINE
        assert config.spacing == 5.0


class TestSolver:
    def test_basic_solve(self):
        solver = Solver()
        result = solver.solve(make_problem())
        assert result.total_placed == 5

    def test_maxrects(self):
        config = SolverConfig(algorithm=Algorithm.MAXRECTS)
        result = Solver(config).solve(make_problem())
        assert result.total_placed == 5

    def test_guillotine(self):
        config = SolverConfig(algorithm=Algorithm.GUILLOTINE)
        result = Solver(config).solve(make_problem())
        assert result.total_placed == 5

    def test_shelf(self):
        config = SolverConfig(algorithm=Algorithm.SHELF)
        result = Solver(config).solve(make_problem())
        assert result.total_placed == 5

    def test_skyline(self):
        config = SolverConfig(algorithm=Algorithm.SKYLINE)
        result = Solver(config).solve(make_problem())
        assert result.total_placed == 5

    def test_fluent_api(self):
        result = (
            Solver()
            .with_algorithm(Algorithm.SKYLINE)
            .with_rotation(RotationPolicy.ORTHOGONAL)
            .with_spacing(2.0)
            .solve(make_problem())
        )
        assert result.total_placed > 0

    def test_solve_simple(self):
        solver = Solver()
        rects = [Rect(20, 20, label=f"R{i}") for i in range(5)]
        result = solver.solve_simple(rects, 100, 100)
        assert result.total_placed == 5

    def test_with_rotation(self):
        config = SolverConfig(rotation=RotationPolicy.ORTHOGONAL)
        solver = Solver(config)
        p = PackingProblem()
        p.add_bin(50, 100)
        p.add_rect(80, 20)  # needs rotation
        result = solver.solve(p)
        assert result.total_placed == 1

    def test_with_spacing(self):
        config = SolverConfig(spacing=5.0)
        result = Solver(config).solve(make_problem())
        # 5 rects of 20x20 with 5px spacing in 100x100 bin
        assert result.total_placed > 0

    def test_multi_bin(self):
        p = PackingProblem()
        p.add_bin(50, 50)
        p.add_bin(50, 50)
        for i in range(4):
            p.add_rect(25, 25, label=f"R{i}")

        config = SolverConfig(multi_bin=True)
        result = Solver(config).solve(p)
        assert result.total_placed == 4
        assert result.bins_used == 1  # All fit in first bin

    def test_multi_bin_overflow(self):
        p = PackingProblem()
        p.add_bin(50, 50)
        p.add_bin(50, 50)
        for i in range(5):
            p.add_rect(25, 25, label=f"R{i}")

        config = SolverConfig(multi_bin=True)
        result = Solver(config).solve(p)
        # 4 fit in first bin (2x2 grid of 25x25 in 50x50), 5th overflows to second
        assert result.total_placed == 5
        assert result.bins_used == 2

    def test_optimizer_multistart(self):
        config = SolverConfig(optimizer=Optimizer.MULTI_START)
        result = Solver(config).solve(make_problem())
        assert result.total_placed == 5

    def test_optimizer_annealing(self):
        from tessera.optimization.annealing import AnnealingConfig
        config = SolverConfig(
            optimizer=Optimizer.ANNEALING,
            annealing_config=AnnealingConfig(
                max_iterations=20, restarts=1, seed=42,
            ),
        )
        result = Solver(config).solve(make_problem())
        assert result.total_placed > 0

    def test_optimizer_genetic(self):
        from tessera.optimization.genetic import GeneticConfig
        config = SolverConfig(
            optimizer=Optimizer.GENETIC,
            genetic_config=GeneticConfig(
                population_size=5, generations=3, seed=42,
            ),
        )
        result = Solver(config).solve(make_problem())
        assert result.total_placed > 0

    def test_benchmark(self):
        solver = Solver()
        results = solver.benchmark(make_problem())
        assert len(results) == 4  # 4 algorithms
        for name, result in results.items():
            assert result.total_placed > 0

    def test_with_seed(self):
        result1 = Solver().with_seed(42).with_optimizer(Optimizer.ANNEALING).solve(make_problem())
        result2 = Solver().with_seed(42).with_optimizer(Optimizer.ANNEALING).solve(make_problem())
        # With same seed, should get same number placed
        assert result1.total_placed == result2.total_placed

    def test_elapsed_time(self):
        result = Solver().solve(make_problem())
        assert result.elapsed_ms > 0
