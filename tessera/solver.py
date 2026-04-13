"""
High-level solver interface for Tessera.

The Solver is the main entry point for users. It combines algorithm selection,
constraint handling, optimization, and result generation into a clean API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any

from tessera.core import (
    Bin, PackingProblem, PackingResult, Rect,
    RotationPolicy, SortStrategy,
)
from tessera.algorithms.maxrects import MaxRectsAlgorithm, MaxRectsHeuristic
from tessera.algorithms.guillotine import (
    GuillotineAlgorithm, GuillotineChoice, GuillotineSplit,
)
from tessera.algorithms.shelf import ShelfAlgorithm, ShelfChoice
from tessera.algorithms.skyline import SkylineAlgorithm, SkylineChoice
from tessera.algorithms.base import BaseAlgorithm
from tessera.constraints.base import Constraint
from tessera.optimization.annealing import SimulatedAnnealing, AnnealingConfig
from tessera.optimization.genetic import GeneticOptimizer, GeneticConfig
from tessera.optimization.multistart import MultiStartOptimizer
from tessera.optimization.objective import DefaultObjective, ObjectiveFunction


class Algorithm(Enum):
    """Available packing algorithms."""
    MAXRECTS = auto()
    GUILLOTINE = auto()
    SHELF = auto()
    SKYLINE = auto()


class Optimizer(Enum):
    """Available optimization strategies."""
    NONE = auto()
    MULTI_START = auto()
    ANNEALING = auto()
    GENETIC = auto()


@dataclass
class SolverConfig:
    """
    Configuration for the Tessera solver.

    Attributes:
        algorithm: Which packing algorithm to use.
        optimizer: Which optimization strategy to apply.
        rotation: Whether to allow rotation.
        sort_strategy: How to sort rects before packing.
        spacing: Minimum spacing between rects.
        multi_bin: Whether to use multiple bins.
        seed: Random seed for reproducibility.
    """
    algorithm: Algorithm = Algorithm.MAXRECTS
    optimizer: Optimizer = Optimizer.NONE
    rotation: RotationPolicy = RotationPolicy.NONE
    sort_strategy: SortStrategy = SortStrategy.AREA_DESC
    spacing: float = 0.0
    multi_bin: bool = False
    seed: Optional[int] = None

    # Algorithm-specific options
    maxrects_heuristic: MaxRectsHeuristic = MaxRectsHeuristic.BSSF
    guillotine_choice: GuillotineChoice = GuillotineChoice.BEST_AREA_FIT
    guillotine_split: GuillotineSplit = GuillotineSplit.SHORTER_LEFTOVER
    shelf_choice: ShelfChoice = ShelfChoice.FIRST_FIT
    skyline_choice: SkylineChoice = SkylineChoice.BOTTOM_LEFT

    # Optimization options
    annealing_config: Optional[AnnealingConfig] = None
    genetic_config: Optional[GeneticConfig] = None


class Solver:
    """
    High-level solver for 2D bin packing problems.

    Usage:
        solver = Solver(SolverConfig(algorithm=Algorithm.MAXRECTS))
        result = solver.solve(problem)

    Or with the fluent API:
        result = (Solver()
            .algorithm(Algorithm.SKYLINE)
            .rotation(RotationPolicy.ORTHOGONAL)
            .spacing(2.0)
            .optimize(Optimizer.ANNEALING)
            .solve(problem))
    """

    def __init__(self, config: Optional[SolverConfig] = None):
        self._config = config or SolverConfig()
        self._constraints: List[Constraint] = []
        self._objective: Optional[ObjectiveFunction] = None

    # Fluent API methods

    def with_algorithm(self, algo: Algorithm) -> Solver:
        """Set the packing algorithm."""
        self._config.algorithm = algo
        return self

    def with_rotation(self, policy: RotationPolicy) -> Solver:
        """Set the rotation policy."""
        self._config.rotation = policy
        return self

    def with_spacing(self, spacing: float) -> Solver:
        """Set minimum spacing between rects."""
        self._config.spacing = spacing
        return self

    def with_optimizer(self, opt: Optimizer) -> Solver:
        """Set the optimization strategy."""
        self._config.optimizer = opt
        return self

    def with_sort(self, strategy: SortStrategy) -> Solver:
        """Set the sort strategy."""
        self._config.sort_strategy = strategy
        return self

    def with_multi_bin(self, enabled: bool = True) -> Solver:
        """Enable or disable multi-bin packing."""
        self._config.multi_bin = enabled
        return self

    def with_constraint(self, constraint: Constraint) -> Solver:
        """Add a constraint."""
        self._constraints.append(constraint)
        return self

    def with_constraints(self, constraints: List[Constraint]) -> Solver:
        """Add multiple constraints."""
        self._constraints.extend(constraints)
        return self

    def with_objective(self, objective: ObjectiveFunction) -> Solver:
        """Set a custom objective function for optimization."""
        self._objective = objective
        return self

    def with_seed(self, seed: int) -> Solver:
        """Set random seed for reproducibility."""
        self._config.seed = seed
        return self

    # Solving

    def solve(self, problem: PackingProblem) -> PackingResult:
        """
        Solve a packing problem.

        Args:
            problem: The packing problem to solve.

        Returns:
            PackingResult with placements and statistics.
        """
        start = time.perf_counter()

        # Apply config to problem
        problem.rotation = self._config.rotation
        problem.sort_strategy = self._config.sort_strategy
        problem.spacing = self._config.spacing
        problem.multi_bin = self._config.multi_bin

        # Validate
        issues = problem.validate()
        if issues:
            # Non-fatal: log but continue
            pass

        # Get sorted rects
        sorted_rects = problem.sorted_rects()

        # Create algorithm instance
        algo = self._create_algorithm()

        # Run optimizer or plain algorithm
        if self._config.optimizer == Optimizer.NONE:
            result = algo.pack(
                rects=sorted_rects,
                bins=problem.bins,
                multi_bin=problem.multi_bin,
            )
        elif self._config.optimizer == Optimizer.MULTI_START:
            optimizer = MultiStartOptimizer(
                objective=self._objective or DefaultObjective(),
            )
            result = optimizer.optimize(problem, self._constraints)
        elif self._config.optimizer == Optimizer.ANNEALING:
            ann_config = self._config.annealing_config or AnnealingConfig(
                seed=self._config.seed,
            )
            optimizer = SimulatedAnnealing(
                algorithm=algo,
                config=ann_config,
                objective=self._objective or DefaultObjective(),
            )
            result = optimizer.optimize(problem, self._constraints)
        elif self._config.optimizer == Optimizer.GENETIC:
            gen_config = self._config.genetic_config or GeneticConfig(
                seed=self._config.seed,
            )
            optimizer = GeneticOptimizer(
                algorithm=algo,
                config=gen_config,
                objective=self._objective or DefaultObjective(),
            )
            result = optimizer.optimize(problem, self._constraints)
        else:
            result = algo.pack(
                rects=sorted_rects,
                bins=problem.bins,
                multi_bin=problem.multi_bin,
            )

        result.elapsed_ms = (time.perf_counter() - start) * 1000
        return result

    def solve_simple(
        self,
        rects: List[Rect],
        bin_width: float,
        bin_height: float,
    ) -> PackingResult:
        """
        Convenience method for simple single-bin packing.

        Args:
            rects: Rectangles to pack.
            bin_width: Width of the bin.
            bin_height: Height of the bin.

        Returns:
            PackingResult.
        """
        problem = PackingProblem(
            rects=rects,
            bins=[Bin(width=bin_width, height=bin_height)],
        )
        return self.solve(problem)

    def _create_algorithm(self) -> BaseAlgorithm:
        """Create the configured algorithm instance."""
        rotation = self._config.rotation
        spacing = self._config.spacing

        if self._config.algorithm == Algorithm.MAXRECTS:
            return MaxRectsAlgorithm(
                heuristic=self._config.maxrects_heuristic,
                rotation=rotation,
                spacing=spacing,
            )
        elif self._config.algorithm == Algorithm.GUILLOTINE:
            return GuillotineAlgorithm(
                choice=self._config.guillotine_choice,
                split=self._config.guillotine_split,
                rotation=rotation,
                spacing=spacing,
            )
        elif self._config.algorithm == Algorithm.SHELF:
            return ShelfAlgorithm(
                choice=self._config.shelf_choice,
                rotation=rotation,
                spacing=spacing,
            )
        elif self._config.algorithm == Algorithm.SKYLINE:
            return SkylineAlgorithm(
                choice=self._config.skyline_choice,
                rotation=rotation,
                spacing=spacing,
            )
        else:
            return MaxRectsAlgorithm(rotation=rotation, spacing=spacing)

    def benchmark(
        self,
        problem: PackingProblem,
        algorithms: Optional[List[Algorithm]] = None,
    ) -> Dict[str, PackingResult]:
        """
        Run multiple algorithms on the same problem and compare results.

        Returns a dict of algorithm_name -> PackingResult.
        """
        algorithms = algorithms or list(Algorithm)
        results = {}

        original_algo = self._config.algorithm

        for algo in algorithms:
            self._config.algorithm = algo
            result = self.solve(problem)
            results[algo.name] = result

        self._config.algorithm = original_algo
        return results
