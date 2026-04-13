"""
Objective functions for optimization.

Combines packing efficiency, constraint penalties, and other metrics
into a single score that optimizers try to minimize.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from tessera.core import Bin, PackingResult
from tessera.constraints.base import Constraint


class ObjectiveFunction(ABC):
    """Base class for objective functions."""

    @abstractmethod
    def evaluate(
        self,
        result: PackingResult,
        bins: List[Bin],
        constraints: Optional[List[Constraint]] = None,
    ) -> float:
        """
        Evaluate the quality of a packing result. Lower is better.
        """
        ...


class DefaultObjective(ObjectiveFunction):
    """
    Default objective function that combines multiple quality metrics.

    Score components:
    - Rejection penalty: heavy penalty for each unpacked rect
    - Efficiency: penalize wasted space
    - Bins used: penalize using more bins
    - Constraint violations: weighted penalty for each violation
    - Compactness: prefer tighter bounding boxes
    """

    def __init__(
        self,
        rejection_weight: float = 1000.0,
        efficiency_weight: float = 10.0,
        bin_count_weight: float = 50.0,
        constraint_weight: float = 100.0,
        compactness_weight: float = 1.0,
    ):
        self.rejection_weight = rejection_weight
        self.efficiency_weight = efficiency_weight
        self.bin_count_weight = bin_count_weight
        self.constraint_weight = constraint_weight
        self.compactness_weight = compactness_weight

    def evaluate(
        self,
        result: PackingResult,
        bins: List[Bin],
        constraints: Optional[List[Constraint]] = None,
    ) -> float:
        score = 0.0

        # Rejection penalty
        score += self.rejection_weight * result.total_rejected

        # Efficiency penalty (inverted: lower waste = lower score)
        if bins and result.bins_used > 0:
            eff = result.efficiency(bins)
            score += self.efficiency_weight * (1.0 - eff)

        # Bin count penalty
        score += self.bin_count_weight * max(0, result.bins_used - 1)

        # Constraint penalties
        if constraints:
            for c in constraints:
                penalty = c.penalty(result.placements, bins)
                if c.hard:
                    score += self.constraint_weight * penalty * 10
                else:
                    score += self.constraint_weight * penalty

        # Compactness (tighter bounding box)
        if result.placements:
            for bin_idx in range(result.bins_used):
                bb = result.bounding_box(bin_idx)
                if bin_idx < len(bins):
                    # Ratio of bounding box to bin size
                    bb_area = bb[0] * bb[1]
                    bin_area = bins[bin_idx].area
                    if bin_area > 0:
                        score += self.compactness_weight * (bb_area / bin_area)

        return score
