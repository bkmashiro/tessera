"""
Multi-start optimizer.

Runs multiple algorithm/heuristic combinations in parallel and returns
the best result. A simple but effective strategy that exploits the fact
that different heuristics excel on different problem instances.
"""

from __future__ import annotations

import time
from typing import List, Optional

from tessera.core import Bin, PackingProblem, PackingResult, Rect, SortStrategy
from tessera.algorithms.base import BaseAlgorithm
from tessera.algorithms.maxrects import MaxRectsAlgorithm, MaxRectsHeuristic
from tessera.algorithms.guillotine import (
    GuillotineAlgorithm, GuillotineChoice, GuillotineSplit,
)
from tessera.algorithms.shelf import ShelfAlgorithm, ShelfChoice
from tessera.algorithms.skyline import SkylineAlgorithm, SkylineChoice
from tessera.constraints.base import Constraint
from tessera.optimization.objective import DefaultObjective, ObjectiveFunction


class MultiStartOptimizer:
    """
    Runs multiple algorithm configurations and returns the best result.

    Can be configured with specific algorithms or use a default set
    covering all built-in algorithms with their main heuristics.
    """

    def __init__(
        self,
        algorithms: Optional[List[BaseAlgorithm]] = None,
        sort_strategies: Optional[List[SortStrategy]] = None,
        objective: Optional[ObjectiveFunction] = None,
    ):
        self.algorithms = algorithms or self._default_algorithms()
        self.sort_strategies = sort_strategies or [
            SortStrategy.AREA_DESC,
            SortStrategy.HEIGHT_DESC,
            SortStrategy.WIDTH_DESC,
            SortStrategy.PERIMETER_DESC,
            SortStrategy.MAX_SIDE_DESC,
        ]
        self.objective = objective or DefaultObjective()

    def _default_algorithms(self) -> List[BaseAlgorithm]:
        """Create a diverse set of algorithm configurations."""
        from tessera.core import RotationPolicy

        algos = []
        for rotation in [RotationPolicy.NONE]:
            # MaxRects variants
            for h in MaxRectsHeuristic:
                algos.append(MaxRectsAlgorithm(heuristic=h, rotation=rotation))

            # Guillotine variants
            for choice in [GuillotineChoice.BEST_AREA_FIT, GuillotineChoice.BEST_SHORT_SIDE]:
                for split in [GuillotineSplit.SHORTER_LEFTOVER, GuillotineSplit.MIN_AREA]:
                    algos.append(GuillotineAlgorithm(
                        choice=choice, split=split, rotation=rotation
                    ))

            # Skyline variants
            for choice in SkylineChoice:
                algos.append(SkylineAlgorithm(choice=choice, rotation=rotation))

            # Shelf variants
            for choice in [ShelfChoice.FIRST_FIT, ShelfChoice.BEST_HEIGHT_FIT]:
                algos.append(ShelfAlgorithm(choice=choice, rotation=rotation))

        return algos

    def optimize(
        self,
        problem: PackingProblem,
        constraints: Optional[List[Constraint]] = None,
    ) -> PackingResult:
        """
        Run all algorithm/sort combinations and return the best result.
        """
        start = time.perf_counter()
        constraints = constraints or []

        best_result: Optional[PackingResult] = None
        best_score = float('inf')
        configs_tried = 0

        for sort_strategy in self.sort_strategies:
            sorted_rects = problem.sorted_rects()
            # Override sort strategy
            from tessera.core import sort_rects
            ordered = sort_rects(sorted_rects, sort_strategy)

            for algo in self.algorithms:
                result = algo.pack(
                    rects=ordered,
                    bins=problem.bins,
                    multi_bin=problem.multi_bin,
                )
                score = self.objective.evaluate(result, problem.bins, constraints)
                configs_tried += 1

                if score < best_score:
                    best_score = score
                    best_result = result
                    best_result.algorithm = f"{algo.name}+{sort_strategy.name}"

        if best_result is not None:
            best_result.elapsed_ms = (time.perf_counter() - start) * 1000
            best_result.iterations = configs_tried
            best_result.metadata["optimizer"] = "multi_start"
            best_result.metadata["configs_tried"] = configs_tried
            best_result.metadata["final_score"] = best_score

        return best_result or PackingResult()
