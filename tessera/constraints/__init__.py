"""
Constraint system for Tessera.

Provides composable constraints that restrict or guide rectangle placement.
Constraints are evaluated during packing and during optimization.
"""

from tessera.constraints.base import Constraint, ConstraintViolation
from tessera.constraints.spatial import (
    MarginConstraint,
    AlignmentConstraint,
    RegionConstraint,
    FixedPositionConstraint,
    MinDistanceConstraint,
)
from tessera.constraints.grouping import GroupConstraint, GroupProximityConstraint
from tessera.constraints.ratio import AspectRatioConstraint, BinFillConstraint

__all__ = [
    "Constraint",
    "ConstraintViolation",
    "MarginConstraint",
    "AlignmentConstraint",
    "RegionConstraint",
    "FixedPositionConstraint",
    "MinDistanceConstraint",
    "GroupConstraint",
    "GroupProximityConstraint",
    "AspectRatioConstraint",
    "BinFillConstraint",
]
