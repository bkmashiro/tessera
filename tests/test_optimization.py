"""Tests for optimization module."""

import pytest
from tessera.core import Bin, PackingProblem, Rect, SortStrategy
from tessera.algorithms.maxrects import MaxRectsAlgorithm
from tessera.optimization.annealing import AnnealingConfig, SimulatedAnnealing
from tessera.optimization.genetic import GeneticConfig, GeneticOptimizer
from tessera.optimization.multistart import MultiStartOptimizer
from tessera.optimization.objective import DefaultObjective


def make_problem(n=10, bin_size=100):
    """Create a standard test problem."""
    problem = PackingProblem()
    problem.add_bin(bin_size, bin_size)
    for i in range(n):
        w = 10 + (i * 7) % 30
        h = 10 + (i * 11) % 30
        problem.add_rect(w, h, label=f"R{i}")
    return problem


class TestDefaultObjective:
    def test_all_placed_lower_score(self):
        obj = DefaultObjective()
        bins = [Bin(100, 100)]

        good = PackingProblem()
        good.add_bin(100, 100)
        for i in range(4):
            good.add_rect(10, 10)
        algo = MaxRectsAlgorithm()
        good_result = algo.pack(good.rects, bins)

        bad_result = algo.pack([Rect(200, 200)], bins)

        good_score = obj.evaluate(good_result, bins)
        bad_score = obj.evaluate(bad_result, bins)
        assert good_score < bad_score

    def test_higher_efficiency_lower_score(self):
        obj = DefaultObjective()
        bins = [Bin(100, 100)]
        algo = MaxRectsAlgorithm()

        # More rects packed = higher efficiency = lower score
        few = algo.pack([Rect(10, 10)], bins)
        many = algo.pack([Rect(50, 50), Rect(40, 40)], bins)

        # many has more area packed
        few_score = obj.evaluate(few, bins)
        many_score = obj.evaluate(many, bins)
        assert many_score < few_score

    def test_empty_result(self):
        obj = DefaultObjective()
        from tessera.core import PackingResult
        result = PackingResult()
        score = obj.evaluate(result, [Bin(100, 100)])
        assert score >= 0


class TestSimulatedAnnealing:
    def test_basic_optimization(self):
        problem = make_problem(8, 100)
        algo = MaxRectsAlgorithm()
        config = AnnealingConfig(
            initial_temp=100,
            cooling_rate=0.95,
            min_temp=1,
            max_iterations=50,
            restarts=1,
            seed=42,
        )
        optimizer = SimulatedAnnealing(algo, config)
        result = optimizer.optimize(problem)
        assert result.total_placed > 0
        assert result.metadata.get("optimizer") == "simulated_annealing"

    def test_seed_reproducibility(self):
        problem = make_problem(6, 100)
        algo = MaxRectsAlgorithm()
        config = AnnealingConfig(
            initial_temp=50, cooling_rate=0.9, min_temp=1,
            max_iterations=30, restarts=1, seed=123,
        )

        r1 = SimulatedAnnealing(algo, config).optimize(problem)
        r2 = SimulatedAnnealing(algo, config).optimize(problem)
        assert r1.total_placed == r2.total_placed

    def test_respects_max_iterations(self):
        problem = make_problem(5, 100)
        config = AnnealingConfig(
            initial_temp=1000, cooling_rate=0.999, min_temp=0.001,
            max_iterations=10, restarts=1, seed=42,
        )
        optimizer = SimulatedAnnealing(MaxRectsAlgorithm(), config)
        result = optimizer.optimize(problem)
        assert result.iterations <= 15  # 10 + some overhead

    def test_single_rect(self):
        problem = PackingProblem()
        problem.add_bin(100, 100)
        problem.add_rect(50, 50)
        config = AnnealingConfig(max_iterations=10, restarts=1, seed=42)
        optimizer = SimulatedAnnealing(MaxRectsAlgorithm(), config)
        result = optimizer.optimize(problem)
        assert result.total_placed == 1


class TestGeneticOptimizer:
    def test_basic_optimization(self):
        problem = make_problem(8, 100)
        config = GeneticConfig(
            population_size=10,
            generations=5,
            seed=42,
        )
        optimizer = GeneticOptimizer(MaxRectsAlgorithm(), config)
        result = optimizer.optimize(problem)
        assert result.total_placed > 0
        assert result.metadata.get("optimizer") == "genetic"

    def test_seed_reproducibility(self):
        problem = make_problem(6, 100)
        config = GeneticConfig(population_size=8, generations=3, seed=99)

        r1 = GeneticOptimizer(MaxRectsAlgorithm(), config).optimize(problem)
        r2 = GeneticOptimizer(MaxRectsAlgorithm(), config).optimize(problem)
        assert r1.total_placed == r2.total_placed

    def test_single_rect(self):
        problem = PackingProblem()
        problem.add_bin(100, 100)
        problem.add_rect(50, 50)
        config = GeneticConfig(population_size=5, generations=2, seed=42)
        optimizer = GeneticOptimizer(MaxRectsAlgorithm(), config)
        result = optimizer.optimize(problem)
        assert result.total_placed == 1

    def test_two_rects(self):
        problem = PackingProblem()
        problem.add_bin(100, 100)
        problem.add_rect(50, 50)
        problem.add_rect(40, 40)
        config = GeneticConfig(population_size=5, generations=2, seed=42)
        optimizer = GeneticOptimizer(MaxRectsAlgorithm(), config)
        result = optimizer.optimize(problem)
        assert result.total_placed == 2


class TestMultiStartOptimizer:
    def test_basic(self):
        problem = make_problem(8, 100)
        optimizer = MultiStartOptimizer()
        result = optimizer.optimize(problem)
        assert result.total_placed > 0
        assert result.metadata.get("optimizer") == "multi_start"

    def test_finds_good_solution(self):
        problem = PackingProblem()
        problem.add_bin(100, 100)
        # These should all fit perfectly
        for _ in range(4):
            problem.add_rect(50, 50)
        optimizer = MultiStartOptimizer()
        result = optimizer.optimize(problem)
        assert result.total_placed == 4

    def test_configs_tried(self):
        problem = make_problem(5, 100)
        optimizer = MultiStartOptimizer()
        result = optimizer.optimize(problem)
        assert result.metadata.get("configs_tried", 0) > 1
