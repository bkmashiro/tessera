"""
Simulated Annealing optimizer for packing.

Explores the solution space by permuting the rectangle ordering and
re-packing, accepting worse solutions with decreasing probability.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from tessera.core import Bin, PackingProblem, PackingResult, Rect
from tessera.algorithms.base import BaseAlgorithm
from tessera.constraints.base import Constraint
from tessera.optimization.objective import DefaultObjective, ObjectiveFunction


@dataclass
class AnnealingConfig:
    """Configuration for simulated annealing."""
    initial_temp: float = 9818.0  # From seed
    cooling_rate: float = 0.9584  # From seed (9584/10000)
    min_temp: float = 0.352       # From seed
    max_iterations: int = 6527    # From seed
    restarts: int = 3
    seed: Optional[int] = None
    perturbation_strength: float = 0.3


class SimulatedAnnealing:
    """
    Simulated Annealing optimizer for bin packing.

    Works by repeatedly perturbing the rectangle order and re-packing,
    accepting improvements always and worse solutions with probability
    that decreases with temperature.
    """

    def __init__(
        self,
        algorithm: BaseAlgorithm,
        config: Optional[AnnealingConfig] = None,
        objective: Optional[ObjectiveFunction] = None,
    ):
        self.algorithm = algorithm
        self.config = config or AnnealingConfig()
        self.objective = objective or DefaultObjective()
        self._rng = random.Random(self.config.seed)
        self._best_score = float('inf')
        self._best_order: List[Rect] = []
        self._iterations = 0
        self._accepted = 0

    def optimize(
        self,
        problem: PackingProblem,
        constraints: Optional[List[Constraint]] = None,
    ) -> PackingResult:
        """
        Run simulated annealing optimization.

        Returns the best PackingResult found.
        """
        start = time.perf_counter()
        constraints = constraints or []

        best_result = None
        global_best_score = float('inf')

        for restart in range(self.config.restarts):
            # Initial order: use problem's sorted order, then shuffle slightly
            current_order = problem.sorted_rects()
            if restart > 0:
                self._shuffle_order(current_order)

            result, score = self._run_single(
                current_order, problem, constraints
            )

            if score < global_best_score:
                global_best_score = score
                best_result = result

        if best_result is not None:
            best_result.elapsed_ms = (time.perf_counter() - start) * 1000
            best_result.iterations = self._iterations
            best_result.metadata["optimizer"] = "simulated_annealing"
            best_result.metadata["final_score"] = global_best_score
            best_result.metadata["accepted_moves"] = self._accepted

        return best_result or PackingResult(algorithm=self.algorithm.name)

    def _run_single(
        self,
        initial_order: List[Rect],
        problem: PackingProblem,
        constraints: List[Constraint],
    ) -> Tuple[PackingResult, float]:
        """Run a single annealing pass."""
        current_order = list(initial_order)
        current_result = self._pack_order(current_order, problem)
        current_score = self.objective.evaluate(
            current_result, problem.bins, constraints
        )

        best_order = list(current_order)
        best_result = current_result
        best_score = current_score

        temp = self.config.initial_temp
        iteration = 0

        while temp > self.config.min_temp and iteration < self.config.max_iterations:
            # Generate neighbor by perturbing order
            new_order = self._perturb(current_order)
            new_result = self._pack_order(new_order, problem)
            new_score = self.objective.evaluate(
                new_result, problem.bins, constraints
            )

            delta = new_score - current_score

            # Accept or reject
            if delta < 0 or self._rng.random() < math.exp(-delta / max(temp, 1e-10)):
                current_order = new_order
                current_result = new_result
                current_score = new_score
                self._accepted += 1

                if current_score < best_score:
                    best_order = list(current_order)
                    best_result = current_result
                    best_score = current_score

            temp *= self.config.cooling_rate
            iteration += 1
            self._iterations += 1

        return best_result, best_score

    def _pack_order(
        self,
        order: List[Rect],
        problem: PackingProblem,
    ) -> PackingResult:
        """Pack rects in the given order."""
        return self.algorithm.pack(
            rects=order,
            bins=problem.bins,
            multi_bin=problem.multi_bin,
        )

    def _perturb(self, order: List[Rect]) -> List[Rect]:
        """Create a neighbor solution by perturbing the order."""
        new_order = list(order)
        n = len(new_order)
        if n < 2:
            return new_order

        # Number of perturbations based on strength
        num_ops = max(1, int(n * self.config.perturbation_strength))

        for _ in range(num_ops):
            op = self._rng.random()

            if op < 0.4:
                # Swap two random elements
                i = self._rng.randint(0, n - 1)
                j = self._rng.randint(0, n - 1)
                new_order[i], new_order[j] = new_order[j], new_order[i]

            elif op < 0.7:
                # Move a random element to a random position
                i = self._rng.randint(0, n - 1)
                j = self._rng.randint(0, n - 1)
                item = new_order.pop(i)
                new_order.insert(j, item)

            else:
                # Reverse a random sub-segment
                i = self._rng.randint(0, n - 1)
                j = self._rng.randint(i, min(i + n // 4, n - 1))
                new_order[i:j + 1] = reversed(new_order[i:j + 1])

        return new_order

    def _shuffle_order(self, order: List[Rect]) -> None:
        """Shuffle order in-place."""
        self._rng.shuffle(order)
