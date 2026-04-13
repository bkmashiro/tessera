"""
Spatial constraints for rectangle placement.

Includes margin, alignment, region restriction, fixed position,
and minimum distance constraints.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from tessera.core import Bin, Placement, Point
from tessera.constraints.base import Constraint, ConstraintViolation


class MarginConstraint(Constraint):
    """
    Enforces minimum margin between rectangles and/or bin edges.

    Attributes:
        inter_rect: Minimum distance between any two rectangles.
        bin_edge: Minimum distance from any rectangle to the bin edge.
        rect_ids: If specified, only apply to these rect IDs.
    """

    name = "margin"

    def __init__(
        self,
        inter_rect: float = 0.0,
        bin_edge: float = 0.0,
        rect_ids: Optional[Set[str]] = None,
        hard: bool = True,
    ):
        self.inter_rect = inter_rect
        self.bin_edge = bin_edge
        self.rect_ids = rect_ids
        self.hard = hard

    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        violations = []
        filtered = self._filter(placements)

        # Check inter-rect margins
        if self.inter_rect > 0:
            for i, p1 in enumerate(filtered):
                for p2 in filtered[i + 1:]:
                    if p1.bin_index != p2.bin_index:
                        continue
                    dist = p1.distance_to(p2)
                    if dist < self.inter_rect - 1e-9:
                        violations.append(ConstraintViolation(
                            constraint_name=self.name,
                            message=f"Rects {p1.rect.rid[:8]} and {p2.rect.rid[:8]} "
                                    f"too close: {dist:.2f} < {self.inter_rect}",
                            severity=(self.inter_rect - dist) / self.inter_rect,
                            placement_rid=p1.rect.rid,
                            details={"distance": dist, "required": self.inter_rect},
                        ))

        # Check bin edge margins
        if self.bin_edge > 0:
            for p in filtered:
                if p.bin_index < len(bins):
                    b = bins[p.bin_index]
                    issues = []
                    if p.x < self.bin_edge - 1e-9:
                        issues.append(f"left={p.x:.2f}")
                    if p.y < self.bin_edge - 1e-9:
                        issues.append(f"top={p.y:.2f}")
                    if p.right > b.width - self.bin_edge + 1e-9:
                        issues.append(f"right gap={b.width - p.right:.2f}")
                    if p.bottom > b.height - self.bin_edge + 1e-9:
                        issues.append(f"bottom gap={b.height - p.bottom:.2f}")
                    if issues:
                        violations.append(ConstraintViolation(
                            constraint_name=self.name,
                            message=f"Rect {p.rect.rid[:8]} too close to bin edge: "
                                    f"{', '.join(issues)}",
                            severity=1.0,
                            placement_rid=p.rect.rid,
                        ))

        return violations

    def _filter(self, placements: List[Placement]) -> List[Placement]:
        if self.rect_ids is None:
            return placements
        return [p for p in placements if p.rect.rid in self.rect_ids]


class AlignmentConstraint(Constraint):
    """
    Enforces alignment of rectangles along a grid or axis.

    Attributes:
        grid_x: If > 0, x positions must be multiples of this value.
        grid_y: If > 0, y positions must be multiples of this value.
        axis: "x" for horizontal alignment, "y" for vertical, None for grid.
        rect_ids: If specified, only apply to these rect IDs.
    """

    name = "alignment"

    def __init__(
        self,
        grid_x: float = 0.0,
        grid_y: float = 0.0,
        axis: Optional[str] = None,
        rect_ids: Optional[Set[str]] = None,
        hard: bool = False,
    ):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.axis = axis
        self.rect_ids = rect_ids
        self.hard = hard

    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        violations = []
        filtered = [p for p in placements
                    if self.rect_ids is None or p.rect.rid in self.rect_ids]

        for p in filtered:
            if self.grid_x > 0:
                remainder = p.x % self.grid_x
                if remainder > 1e-9 and abs(remainder - self.grid_x) > 1e-9:
                    violations.append(ConstraintViolation(
                        constraint_name=self.name,
                        message=f"Rect {p.rect.rid[:8]} x={p.x:.2f} not aligned to grid_x={self.grid_x}",
                        severity=min(remainder, self.grid_x - remainder) / self.grid_x,
                        placement_rid=p.rect.rid,
                    ))

            if self.grid_y > 0:
                remainder = p.y % self.grid_y
                if remainder > 1e-9 and abs(remainder - self.grid_y) > 1e-9:
                    violations.append(ConstraintViolation(
                        constraint_name=self.name,
                        message=f"Rect {p.rect.rid[:8]} y={p.y:.2f} not aligned to grid_y={self.grid_y}",
                        severity=min(remainder, self.grid_y - remainder) / self.grid_y,
                        placement_rid=p.rect.rid,
                    ))

        # Axis alignment: all specified rects should share the same x or y
        if self.axis and len(filtered) > 1:
            if self.axis == "x":
                xs = [p.x for p in filtered]
                if max(xs) - min(xs) > 1e-9:
                    violations.append(ConstraintViolation(
                        constraint_name=self.name,
                        message=f"Rects not aligned on x-axis: range {min(xs):.2f}-{max(xs):.2f}",
                        severity=1.0,
                    ))
            elif self.axis == "y":
                ys = [p.y for p in filtered]
                if max(ys) - min(ys) > 1e-9:
                    violations.append(ConstraintViolation(
                        constraint_name=self.name,
                        message=f"Rects not aligned on y-axis: range {min(ys):.2f}-{max(ys):.2f}",
                        severity=1.0,
                    ))

        return violations


class RegionConstraint(Constraint):
    """
    Restricts placement of specified rects to a rectangular region within the bin.

    Attributes:
        x, y, width, height: The allowed region.
        rect_ids: Rects that must be within this region.
    """

    name = "region"

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        rect_ids: Set[str],
        hard: bool = True,
    ):
        self.region_x = x
        self.region_y = y
        self.region_w = width
        self.region_h = height
        self.rect_ids = rect_ids
        self.hard = hard

    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        violations = []

        for p in placements:
            if p.rect.rid not in self.rect_ids:
                continue

            in_region = (
                p.x >= self.region_x - 1e-9 and
                p.y >= self.region_y - 1e-9 and
                p.right <= self.region_x + self.region_w + 1e-9 and
                p.bottom <= self.region_y + self.region_h + 1e-9
            )

            if not in_region:
                violations.append(ConstraintViolation(
                    constraint_name=self.name,
                    message=f"Rect {p.rect.rid[:8]} at ({p.x:.1f},{p.y:.1f}) "
                            f"outside region ({self.region_x},{self.region_y}) "
                            f"{self.region_w}x{self.region_h}",
                    severity=1.0,
                    placement_rid=p.rect.rid,
                ))

        return violations


class FixedPositionConstraint(Constraint):
    """
    Forces specific rectangles to exact positions.

    Useful for pre-placed items or required positions.
    """

    name = "fixed_position"

    def __init__(
        self,
        positions: Dict[str, Tuple[float, float]],
        tolerance: float = 1e-6,
        hard: bool = True,
    ):
        self.positions = positions  # rid -> (x, y)
        self.tolerance = tolerance
        self.hard = hard

    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        violations = []

        for p in placements:
            if p.rect.rid in self.positions:
                target_x, target_y = self.positions[p.rect.rid]
                dx = abs(p.x - target_x)
                dy = abs(p.y - target_y)
                if dx > self.tolerance or dy > self.tolerance:
                    violations.append(ConstraintViolation(
                        constraint_name=self.name,
                        message=f"Rect {p.rect.rid[:8]} at ({p.x:.2f},{p.y:.2f}) "
                                f"should be at ({target_x:.2f},{target_y:.2f})",
                        severity=1.0,
                        placement_rid=p.rect.rid,
                        details={"dx": dx, "dy": dy},
                    ))

        return violations


class MinDistanceConstraint(Constraint):
    """
    Enforces minimum distance between specific pairs of rectangles.
    """

    name = "min_distance"

    def __init__(
        self,
        pairs: List[Tuple[str, str, float]],
        hard: bool = True,
    ):
        """
        Args:
            pairs: List of (rid_a, rid_b, min_distance) tuples.
        """
        self.pairs = pairs
        self.hard = hard

    def evaluate(
        self,
        placements: List[Placement],
        bins: List[Bin],
    ) -> List[ConstraintViolation]:
        violations = []
        placement_map = {p.rect.rid: p for p in placements}

        for rid_a, rid_b, min_dist in self.pairs:
            pa = placement_map.get(rid_a)
            pb = placement_map.get(rid_b)
            if pa is None or pb is None:
                continue

            dist = pa.distance_to(pb)
            if dist < min_dist - 1e-9:
                violations.append(ConstraintViolation(
                    constraint_name=self.name,
                    message=f"Rects {rid_a[:8]} and {rid_b[:8]} distance {dist:.2f} "
                            f"< minimum {min_dist}",
                    severity=(min_dist - dist) / min_dist if min_dist > 0 else 1.0,
                    details={"distance": dist, "required": min_dist},
                ))

        return violations
