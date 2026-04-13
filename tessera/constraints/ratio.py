"""
Ratio and fill constraints.
"""

from __future__ import annotations

from typing import List, Optional, Set

from tessera.core import Bin, Placement
from tessera.constraints.base import Constraint, ConstraintViolation


class AspectRatioConstraint(Constraint):
    """
    Constrains the aspect ratio of the bounding box of placed rects.

    Useful for ensuring the output fits a target shape (e.g., square texture atlas).
    """

    name = "aspect_ratio"

    def __init__(
        self,
        target_ratio: float = 1.0,
        tolerance: float = 0.2,
        bin_index: int = 0,
        hard: bool = False,
    ):
        self.target_ratio = target_ratio
        self.tolerance = tolerance
        self.bin_index = bin_index
        self.hard = hard

    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        violations = []
        bin_placements = [p for p in placements if p.bin_index == self.bin_index]

        if len(bin_placements) < 2:
            return violations

        max_x = max(p.right for p in bin_placements)
        max_y = max(p.bottom for p in bin_placements)
        min_x = min(p.x for p in bin_placements)
        min_y = min(p.y for p in bin_placements)

        bb_width = max_x - min_x
        bb_height = max_y - min_y

        if bb_height > 1e-9 and bb_width > 1e-9:
            actual_ratio = bb_width / bb_height
            diff = abs(actual_ratio - self.target_ratio)
            if diff > self.tolerance:
                violations.append(ConstraintViolation(
                    constraint_name=self.name,
                    message=f"Bounding box ratio {actual_ratio:.3f} "
                            f"deviates from target {self.target_ratio:.3f} "
                            f"by {diff:.3f} (tolerance: {self.tolerance})",
                    severity=diff,
                    details={
                        "actual_ratio": actual_ratio,
                        "target_ratio": self.target_ratio,
                        "bb_width": bb_width,
                        "bb_height": bb_height,
                    },
                ))

        return violations


class BinFillConstraint(Constraint):
    """
    Enforces a minimum fill ratio for each used bin.

    Prevents bins from being used with very low utilization.
    """

    name = "bin_fill"

    def __init__(
        self,
        min_fill: float = 0.5,
        hard: bool = False,
    ):
        self.min_fill = min_fill
        self.hard = hard

    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        violations = []

        # Group placements by bin
        bin_areas: dict = {}
        for p in placements:
            bin_areas.setdefault(p.bin_index, 0.0)
            bin_areas[p.bin_index] += p.area

        for bin_idx, placed_area in bin_areas.items():
            if bin_idx < len(bins):
                fill = placed_area / bins[bin_idx].area if bins[bin_idx].area > 0 else 0
                if fill < self.min_fill:
                    violations.append(ConstraintViolation(
                        constraint_name=self.name,
                        message=f"Bin {bin_idx} fill {fill:.1%} below minimum {self.min_fill:.1%}",
                        severity=(self.min_fill - fill),
                        details={"bin_index": bin_idx, "fill": fill},
                    ))

        return violations
