"""
Base constraint interface and violation tracking.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from tessera.core import Bin, Placement


@dataclass
class ConstraintViolation:
    """Describes a constraint violation."""
    constraint_name: str
    message: str
    severity: float = 1.0  # 0.0 to 1.0, used for soft constraints
    placement_rid: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Violation({self.constraint_name}: {self.message})"


class Constraint(ABC):
    """
    Base class for packing constraints.

    Constraints can be hard (must be satisfied) or soft (penalized in
    optimization). They evaluate placements and report violations.
    """

    name: str = "base"
    hard: bool = True  # Hard constraints must be satisfied

    @abstractmethod
    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        """
        Evaluate this constraint against current placements.

        Returns a list of violations (empty if constraint is satisfied).
        """
        ...

    def penalty(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> float:
        """
        Calculate a penalty score for optimization.

        Returns 0.0 if satisfied, positive values for violations.
        Default implementation counts violations weighted by severity.
        """
        violations = self.evaluate(placements, bins)
        return sum(v.severity for v in violations)

    def is_satisfied(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> bool:
        """Check if this constraint is fully satisfied."""
        return len(self.evaluate(placements, bins)) == 0

    def __repr__(self) -> str:
        kind = "hard" if self.hard else "soft"
        return f"{self.__class__.__name__}({kind})"
