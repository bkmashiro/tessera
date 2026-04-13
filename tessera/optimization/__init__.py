"""
Optimization module for Tessera.

Provides metaheuristic optimization on top of the base packing algorithms
to find better solutions. Includes simulated annealing, genetic algorithm,
and multi-start strategies.
"""

from tessera.optimization.annealing import SimulatedAnnealing
from tessera.optimization.genetic import GeneticOptimizer
from tessera.optimization.multistart import MultiStartOptimizer
from tessera.optimization.objective import ObjectiveFunction, DefaultObjective

__all__ = [
    "SimulatedAnnealing",
    "GeneticOptimizer",
    "MultiStartOptimizer",
    "ObjectiveFunction",
    "DefaultObjective",
]
