"""
Packing algorithms for Tessera.

Each algorithm implements the BaseAlgorithm interface and provides a different
approach to the 2D bin packing problem.
"""

from tessera.algorithms.base import BaseAlgorithm
from tessera.algorithms.maxrects import MaxRectsAlgorithm, MaxRectsHeuristic
from tessera.algorithms.guillotine import GuillotineAlgorithm, GuillotineSplit, GuillotineChoice
from tessera.algorithms.shelf import ShelfAlgorithm, ShelfChoice
from tessera.algorithms.skyline import SkylineAlgorithm, SkylineChoice

__all__ = [
    "BaseAlgorithm",
    "MaxRectsAlgorithm",
    "MaxRectsHeuristic",
    "GuillotineAlgorithm",
    "GuillotineSplit",
    "GuillotineChoice",
    "ShelfAlgorithm",
    "ShelfChoice",
    "SkylineAlgorithm",
    "SkylineChoice",
]
