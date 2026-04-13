"""
Tessera - A constraint-based 2D bin packing and tiling solver.

Solves rectangle packing problems with support for constraints, rotation,
multiple bins, and optimization via metaheuristics. Useful for texture atlas
generation, sheet cutting, container loading, and layout computation.
"""

__version__ = "0.1.0"

from tessera.core import Rect, Bin, PackingResult, PackingProblem
from tessera.solver import Solver, SolverConfig
from tessera.constraints import (
    Constraint,
    MarginConstraint,
    AlignmentConstraint,
    GroupConstraint,
    RegionConstraint,
    AspectRatioConstraint,
)

__all__ = [
    "Rect",
    "Bin",
    "PackingResult",
    "PackingProblem",
    "Solver",
    "SolverConfig",
    "Constraint",
    "MarginConstraint",
    "AlignmentConstraint",
    "GroupConstraint",
    "RegionConstraint",
    "AspectRatioConstraint",
]
