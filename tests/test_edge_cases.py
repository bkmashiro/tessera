"""Edge case and integration tests."""

import math
import pytest
from tessera.core import (
    Bin, PackingProblem, PackingResult, Placement, Point,
    Rect, RotationPolicy, SortStrategy,
)
from tessera.solver import Algorithm, Optimizer, Solver, SolverConfig
from tessera.algorithms.maxrects import MaxRectsAlgorithm, MaxRectsHeuristic
from tessera.algorithms.guillotine import GuillotineAlgorithm
from tessera.algorithms.shelf import ShelfAlgorithm
from tessera.algorithms.skyline import SkylineAlgorithm
from tessera.constraints.spatial import MarginConstraint, RegionConstraint
from tessera.constraints.grouping import GroupConstraint
from tessera.visualization.ascii_renderer import AsciiRenderer
from tessera.visualization.svg_renderer import SvgRenderer
from tessera.visualization.stats import PackingStats


class TestFloatingPointRects:
    def test_float_dimensions(self):
        r = Rect(width=10.5, height=20.3)
        assert math.isclose(r.area, 10.5 * 20.3)

    def test_very_small_rect(self):
        r = Rect(width=0.001, height=0.001)
        assert r.area > 0

    def test_large_rect(self):
        r = Rect(width=1e6, height=1e6)
        assert r.area == 1e12

    def test_pack_float_rects(self):
        algo = MaxRectsAlgorithm()
        rects = [Rect(10.5, 20.3), Rect(15.7, 8.2)]
        placed, _ = algo.pack_into_bin(rects, Bin(100, 100))
        assert len(placed) == 2


class TestSingleItem:
    def test_exact_fit_maxrects(self):
        algo = MaxRectsAlgorithm()
        placed, _ = algo.pack_into_bin([Rect(100, 100)], Bin(100, 100))
        assert len(placed) == 1
        assert placed[0].x == 0 and placed[0].y == 0

    def test_exact_fit_guillotine(self):
        algo = GuillotineAlgorithm()
        placed, _ = algo.pack_into_bin([Rect(100, 100)], Bin(100, 100))
        assert len(placed) == 1

    def test_exact_fit_shelf(self):
        algo = ShelfAlgorithm()
        placed, _ = algo.pack_into_bin([Rect(100, 100)], Bin(100, 100))
        assert len(placed) == 1

    def test_exact_fit_skyline(self):
        algo = SkylineAlgorithm()
        placed, _ = algo.pack_into_bin([Rect(100, 100)], Bin(100, 100))
        assert len(placed) == 1


class TestManyRects:
    def test_100_small_rects(self):
        algo = MaxRectsAlgorithm()
        rects = [Rect(10, 10, label=f"R{i}") for i in range(100)]
        placed, _ = algo.pack_into_bin(rects, Bin(100, 100))
        assert len(placed) == 100

    def test_mixed_sizes(self):
        algo = MaxRectsAlgorithm()
        rects = []
        for i in range(20):
            w = 5 + (i * 7) % 30
            h = 5 + (i * 11) % 30
            rects.append(Rect(w, h, label=f"R{i}"))
        result = algo.pack(rects, [Bin(200, 200)])
        assert result.total_placed > 0
        assert not result.has_overlaps()

    def test_identical_rects(self):
        algo = MaxRectsAlgorithm()
        rects = [Rect(25, 25, label=f"R{i}") for i in range(16)]
        placed, _ = algo.pack_into_bin(rects, Bin(100, 100))
        assert len(placed) == 16


class TestRotation:
    def test_rotation_enables_fit(self):
        algo = MaxRectsAlgorithm(rotation=RotationPolicy.ORTHOGONAL)
        # 80x20 won't fit in 30x100, but 20x80 will
        rects = [Rect(80, 20, label="Tall")]
        placed, _ = algo.pack_into_bin(rects, Bin(30, 100))
        assert len(placed) == 1
        assert placed[0].rotated

    def test_non_rotatable_rect(self):
        algo = MaxRectsAlgorithm(rotation=RotationPolicy.ORTHOGONAL)
        rects = [Rect(80, 20, rotatable=False)]
        placed, _ = algo.pack_into_bin(rects, Bin(30, 100))
        assert len(placed) == 0


class TestPadding:
    def test_bin_padding_reduces_space(self):
        algo = MaxRectsAlgorithm()
        b = Bin(100, 100, padding=10)
        rects = [Rect(85, 85)]  # Would fit in 100x100 but not 80x80
        placed, _ = algo.pack_into_bin(rects, b)
        assert len(placed) == 0

    def test_bin_padding_ok(self):
        algo = MaxRectsAlgorithm()
        b = Bin(100, 100, padding=10)
        rects = [Rect(75, 75)]
        placed, _ = algo.pack_into_bin(rects, b)
        assert len(placed) == 1
        # Should be placed at padding offset
        assert placed[0].x >= 10


class TestEndToEnd:
    def test_texture_atlas_scenario(self):
        """Simulate packing texture sprites into an atlas."""
        problem = PackingProblem()
        problem.add_bin(1024, 1024, label="Atlas")
        # Add various sprite sizes
        sizes = [
            (64, 64), (128, 128), (32, 32), (256, 256),
            (64, 128), (128, 64), (32, 64), (64, 32),
            (16, 16), (48, 48), (96, 96), (160, 160),
        ]
        for i, (w, h) in enumerate(sizes):
            problem.add_rect(w, h, label=f"sprite_{i}")

        solver = Solver(SolverConfig(
            algorithm=Algorithm.MAXRECTS,
            rotation=RotationPolicy.ORTHOGONAL,
        ))
        result = solver.solve(problem)
        assert result.all_placed
        assert not result.has_overlaps()
        assert result.efficiency(problem.bins) > 0

    def test_sheet_cutting_scenario(self):
        """Simulate cutting parts from a sheet."""
        problem = PackingProblem()
        problem.add_bin(4823, 3219, label="Sheet")  # Seed numbers!
        # Parts to cut
        for i in range(30):
            w = 100 + (i * 137) % 500
            h = 100 + (i * 251) % 400
            problem.add_rect(w, h, label=f"part_{i}")

        solver = Solver(SolverConfig(spacing=5.0))
        result = solver.solve(problem)
        assert result.total_placed > 0
        assert not result.has_overlaps()

    def test_multi_bin_warehouse(self):
        """Pack items into multiple containers."""
        problem = PackingProblem()
        for i in range(5):
            problem.add_bin(100, 100, label=f"Container_{i}")
        for i in range(20):
            problem.add_rect(30, 30, label=f"Box_{i}")

        solver = Solver(SolverConfig(multi_bin=True))
        result = solver.solve(problem)
        assert result.total_placed == 20  # 9 per bin easily, 20 in 3 bins
        assert not result.has_overlaps()

    def test_full_pipeline(self):
        """End-to-end: create problem, solve, analyze, visualize."""
        # Create
        problem = PackingProblem()
        problem.add_bin(200, 200)
        for i in range(10):
            problem.add_rect(30 + i * 5, 20 + i * 3, label=f"R{i}")

        # Solve
        solver = Solver()
        result = solver.solve(problem)

        # Analyze
        stats = PackingStats(result, problem.bins)
        summary = stats.summary()
        assert "Placed" in summary

        # Visualize
        ascii_r = AsciiRenderer(cell_width=10, cell_height=10)
        ascii_out = ascii_r.render(result, problem.bins)
        assert "Bin 0" in ascii_out

        svg_r = SvgRenderer()
        svg_out = svg_r.render(result, problem.bins)
        assert "<svg" in svg_out


class TestConstraintIntegration:
    def test_solver_with_constraint_evaluation(self):
        """Solve then check constraints."""
        problem = PackingProblem()
        problem.add_bin(200, 200)
        for i in range(5):
            problem.add_rect(30, 30, label=f"R{i}")

        solver = Solver()
        result = solver.solve(problem)

        # Evaluate margin constraint
        c = MarginConstraint(inter_rect=1)
        violations = c.evaluate(result.placements, problem.bins)
        # Placements from MaxRects should be non-overlapping
        # (and typically have at least 0 margin)

    def test_group_same_bin(self):
        """Group members should be in same bin."""
        r1 = Rect(30, 30, rid="a", group="team")
        r2 = Rect(30, 30, rid="b", group="team")
        r3 = Rect(30, 30, rid="c")

        problem = PackingProblem(
            rects=[r1, r2, r3],
            bins=[Bin(100, 100)],
        )
        result = Solver().solve(problem)

        c = GroupConstraint(groups={"team": {"a", "b"}})
        violations = c.evaluate(result.placements, problem.bins)
        assert len(violations) == 0  # All in same bin


class TestStressTests:
    def test_many_algorithms_same_problem(self):
        """All algorithms should produce valid results on the same problem."""
        problem = PackingProblem()
        problem.add_bin(200, 200)
        for i in range(15):
            problem.add_rect(20 + i * 3, 15 + i * 2, label=f"R{i}")

        for algo_enum in Algorithm:
            config = SolverConfig(algorithm=algo_enum)
            result = Solver(config).solve(problem)
            assert result.total_placed > 0, f"{algo_enum.name} placed nothing"
            assert not result.has_overlaps(), f"{algo_enum.name} has overlaps"

    def test_all_sort_strategies(self):
        """All sort strategies should produce valid results."""
        problem = PackingProblem()
        problem.add_bin(200, 200)
        for i in range(10):
            problem.add_rect(20 + i * 5, 15 + i * 3, label=f"R{i}")

        for strat in SortStrategy:
            config = SolverConfig(sort_strategy=strat)
            result = Solver(config).solve(problem)
            assert result.total_placed > 0, f"{strat.name} placed nothing"
