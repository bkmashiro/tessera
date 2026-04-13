"""
Grouping constraints for Tessera.

Controls how groups of related rectangles should be placed relative to each other.
"""

from __future__ import annotations

import math
from typing import Dict, List, Set

from tessera.core import Bin, Placement, Point
from tessera.constraints.base import Constraint, ConstraintViolation


class GroupConstraint(Constraint):
    """
    Ensures rectangles in the same group are placed in the same bin.

    Optionally enforces that all group members form a contiguous cluster
    (each member touches or is within max_gap of another group member).
    """

    name = "group"

    def __init__(
        self,
        groups: Dict[str, Set[str]],
        same_bin: bool = True,
        max_gap: float = -1.0,
        hard: bool = True,
    ):
        """
        Args:
            groups: Mapping of group_name -> set of rect IDs.
            same_bin: If True, all group members must be in the same bin.
            max_gap: If >= 0, maximum gap between group members.
        """
        self.groups = groups
        self.same_bin = same_bin
        self.max_gap = max_gap
        self.hard = hard

    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        violations = []
        placement_map = {p.rect.rid: p for p in placements}

        for group_name, member_ids in self.groups.items():
            placed_members = [
                placement_map[rid] for rid in member_ids
                if rid in placement_map
            ]

            if len(placed_members) < 2:
                continue

            # Check same bin
            if self.same_bin:
                bin_indices = set(p.bin_index for p in placed_members)
                if len(bin_indices) > 1:
                    violations.append(ConstraintViolation(
                        constraint_name=self.name,
                        message=f"Group '{group_name}' split across bins: {bin_indices}",
                        severity=1.0,
                        details={"group": group_name, "bins": list(bin_indices)},
                    ))

            # Check max gap (contiguity)
            if self.max_gap >= 0:
                for i, p1 in enumerate(placed_members):
                    for p2 in placed_members[i + 1:]:
                        if p1.bin_index != p2.bin_index:
                            continue
                        dist = p1.distance_to(p2)
                        if dist > self.max_gap + 1e-9:
                            violations.append(ConstraintViolation(
                                constraint_name=self.name,
                                message=f"Group '{group_name}' members "
                                        f"{p1.rect.rid[:8]} and {p2.rect.rid[:8]} "
                                        f"gap {dist:.2f} > max {self.max_gap}",
                                severity=min(1.0, (dist - self.max_gap) / max(self.max_gap, 1)),
                                details={"group": group_name, "distance": dist},
                            ))

        return violations


class GroupProximityConstraint(Constraint):
    """
    Soft constraint that encourages group members to be placed close together.

    Uses the average distance between group member centers as a penalty.
    """

    name = "group_proximity"

    def __init__(
        self,
        groups: Dict[str, Set[str]],
        weight: float = 1.0,
    ):
        self.groups = groups
        self.weight = weight
        self.hard = False

    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        violations = []
        placement_map = {p.rect.rid: p for p in placements}

        for group_name, member_ids in self.groups.items():
            placed = [
                placement_map[rid] for rid in member_ids
                if rid in placement_map
            ]

            if len(placed) < 2:
                continue

            # Calculate centroid
            centers = [p.center for p in placed]
            cx = sum(c.x for c in centers) / len(centers)
            cy = sum(c.y for c in centers) / len(centers)
            centroid = Point(cx, cy)

            # Average distance from centroid
            avg_dist = sum(c.distance_to(centroid) for c in centers) / len(centers)

            if avg_dist > 1e-9:
                violations.append(ConstraintViolation(
                    constraint_name=self.name,
                    message=f"Group '{group_name}' avg spread: {avg_dist:.2f}",
                    severity=avg_dist * self.weight,
                    details={"group": group_name, "avg_distance": avg_dist},
                ))

        return violations

    def penalty(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> float:
        violations = self.evaluate(placements, bins)
        return sum(v.severity for v in violations)
