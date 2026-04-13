"""
Genetic Algorithm optimizer for packing.

Maintains a population of rectangle orderings and evolves them through
selection, crossover, and mutation to find better packing solutions.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from tessera.core import Bin, PackingProblem, PackingResult, Rect
from tessera.algorithms.base import BaseAlgorithm
from tessera.constraints.base import Constraint
from tessera.optimization.objective import DefaultObjective, ObjectiveFunction


@dataclass
class GeneticConfig:
    """Configuration for genetic algorithm optimization."""
    population_size: int = 48   # From seed 4823
    generations: int = 161      # From seed 1619/10
    crossover_rate: float = 0.8
    mutation_rate: float = 0.15
    elite_ratio: float = 0.1
    tournament_size: int = 5
    seed: Optional[int] = None


class GeneticOptimizer:
    """
    Genetic Algorithm optimizer for bin packing.

    Uses order-based crossover (OX) and various mutations to evolve
    a population of rectangle orderings toward better packings.
    """

    def __init__(
        self,
        algorithm: BaseAlgorithm,
        config: Optional[GeneticConfig] = None,
        objective: Optional[ObjectiveFunction] = None,
    ):
        self.algorithm = algorithm
        self.config = config or GeneticConfig()
        self.objective = objective or DefaultObjective()
        self._rng = random.Random(self.config.seed)

    def optimize(
        self,
        problem: PackingProblem,
        constraints: Optional[List[Constraint]] = None,
    ) -> PackingResult:
        """Run genetic algorithm optimization."""
        start = time.perf_counter()
        constraints = constraints or []

        base_order = problem.sorted_rects()
        population = self._init_population(base_order)

        # Evaluate initial population
        scored = self._evaluate_population(population, problem, constraints)

        best_result = scored[0][1]
        best_score = scored[0][0]
        total_iterations = 0

        for gen in range(self.config.generations):
            # Selection and breeding
            new_population = []

            # Elitism: keep top individuals
            elite_count = max(1, int(self.config.population_size * self.config.elite_ratio))
            for i in range(elite_count):
                new_population.append(scored[i][2])

            # Fill rest with offspring
            while len(new_population) < self.config.population_size:
                parent1 = self._tournament_select(scored)
                parent2 = self._tournament_select(scored)

                if self._rng.random() < self.config.crossover_rate:
                    child1, child2 = self._order_crossover(parent1, parent2)
                else:
                    child1, child2 = list(parent1), list(parent2)

                if self._rng.random() < self.config.mutation_rate:
                    self._mutate(child1)
                if self._rng.random() < self.config.mutation_rate:
                    self._mutate(child2)

                new_population.append(child1)
                if len(new_population) < self.config.population_size:
                    new_population.append(child2)

            population = new_population
            scored = self._evaluate_population(population, problem, constraints)
            total_iterations += self.config.population_size

            if scored[0][0] < best_score:
                best_score = scored[0][0]
                best_result = scored[0][1]

        best_result.elapsed_ms = (time.perf_counter() - start) * 1000
        best_result.iterations = total_iterations
        best_result.metadata["optimizer"] = "genetic"
        best_result.metadata["final_score"] = best_score
        best_result.metadata["generations"] = self.config.generations
        return best_result

    def _init_population(self, base_order: List[Rect]) -> List[List[Rect]]:
        """Create initial population with diverse orderings."""
        population = [list(base_order)]  # Include the sorted order

        for _ in range(self.config.population_size - 1):
            order = list(base_order)
            self._rng.shuffle(order)
            population.append(order)

        return population

    def _evaluate_population(
        self,
        population: List[List[Rect]],
        problem: PackingProblem,
        constraints: List[Constraint],
    ) -> List[Tuple[float, PackingResult, List[Rect]]]:
        """Evaluate and sort population by fitness. Returns [(score, result, order)]."""
        scored = []
        for order in population:
            result = self.algorithm.pack(
                rects=order,
                bins=problem.bins,
                multi_bin=problem.multi_bin,
            )
            score = self.objective.evaluate(result, problem.bins, constraints)
            scored.append((score, result, order))

        scored.sort(key=lambda x: x[0])
        return scored

    def _tournament_select(
        self,
        scored: List[Tuple[float, PackingResult, List[Rect]]],
    ) -> List[Rect]:
        """Select an individual via tournament selection."""
        tournament = self._rng.sample(
            scored,
            min(self.config.tournament_size, len(scored)),
        )
        winner = min(tournament, key=lambda x: x[0])
        return winner[2]

    def _order_crossover(
        self,
        parent1: List[Rect],
        parent2: List[Rect],
    ) -> Tuple[List[Rect], List[Rect]]:
        """
        Order Crossover (OX).

        Preserves a contiguous segment from one parent and fills
        remaining positions with the order from the other parent.
        """
        n = len(parent1)
        if n < 3:
            return list(parent1), list(parent2)

        # Select crossover segment
        start = self._rng.randint(0, n - 2)
        end = self._rng.randint(start + 1, n - 1)

        child1 = self._ox_child(parent1, parent2, start, end)
        child2 = self._ox_child(parent2, parent1, start, end)

        return child1, child2

    def _ox_child(
        self,
        parent1: List[Rect],
        parent2: List[Rect],
        start: int,
        end: int,
    ) -> List[Rect]:
        """Create one child from OX crossover."""
        n = len(parent1)
        child: List[Optional[Rect]] = [None] * n

        # Copy segment from parent1
        segment_ids = set()
        for i in range(start, end + 1):
            child[i] = parent1[i]
            segment_ids.add(parent1[i].rid)

        # Fill remaining from parent2 in order
        p2_filtered = [r for r in parent2 if r.rid not in segment_ids]
        j = 0
        for i in range(n):
            if child[i] is None:
                child[i] = p2_filtered[j]
                j += 1

        return child  # type: ignore

    def _mutate(self, order: List[Rect]) -> None:
        """Apply a random mutation to an ordering."""
        n = len(order)
        if n < 2:
            return

        op = self._rng.random()

        if op < 0.33:
            # Swap mutation
            i = self._rng.randint(0, n - 1)
            j = self._rng.randint(0, n - 1)
            order[i], order[j] = order[j], order[i]
        elif op < 0.66:
            # Insert mutation
            i = self._rng.randint(0, n - 1)
            j = self._rng.randint(0, n - 1)
            item = order.pop(i)
            order.insert(j, item)
        else:
            # Inversion mutation
            i = self._rng.randint(0, n - 2)
            j = self._rng.randint(i + 1, n - 1)
            order[i:j + 1] = reversed(order[i:j + 1])
