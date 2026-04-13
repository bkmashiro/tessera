"""
Core data structures for Tessera.

Defines Rect, Bin, PackingResult, PackingProblem and the fundamental
geometry operations used throughout the system.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Iterator


class RotationPolicy(Enum):
    """Controls whether and how rectangles may be rotated."""
    NONE = auto()          # No rotation allowed
    ORTHOGONAL = auto()    # 90-degree rotation allowed
    ARBITRARY = auto()     # Any angle (for future extension)


class SortStrategy(Enum):
    """Pre-sort strategy for rectangle lists before packing."""
    NONE = auto()
    AREA_DESC = auto()
    PERIMETER_DESC = auto()
    WIDTH_DESC = auto()
    HEIGHT_DESC = auto()
    MAX_SIDE_DESC = auto()
    ASPECT_RATIO_DESC = auto()
    SHORT_SIDE_DESC = auto()
    LONG_SIDE_DESC = auto()


@dataclass
class Point:
    """A 2D point."""
    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))


@dataclass
class Rect:
    """
    A rectangle to be packed. Carries dimensions, identity, and optional metadata.

    Attributes:
        width: Width of the rectangle.
        height: Height of the rectangle.
        rid: Unique identifier (auto-generated if not provided).
        label: Human-readable label.
        rotatable: Whether this rect may be rotated.
        group: Optional group identifier for grouping constraints.
        priority: Higher priority rects are placed first (default 0).
        color: Optional color hint for visualization.
        metadata: Arbitrary user data.
    """
    width: float
    height: float
    rid: str = ""
    label: str = ""
    rotatable: bool = True
    group: str = ""
    priority: int = 0
    color: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.rid:
            self.rid = uuid.uuid4().hex[:12]
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Rect dimensions must be positive, got {self.width}x{self.height}")

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

    @property
    def aspect_ratio(self) -> float:
        return max(self.width, self.height) / min(self.width, self.height)

    @property
    def max_side(self) -> float:
        return max(self.width, self.height)

    @property
    def min_side(self) -> float:
        return min(self.width, self.height)

    @property
    def is_square(self) -> bool:
        return math.isclose(self.width, self.height, rel_tol=1e-9)

    def rotated(self) -> Rect:
        """Return a new Rect with width and height swapped."""
        return Rect(
            width=self.height,
            height=self.width,
            rid=self.rid,
            label=self.label,
            rotatable=self.rotatable,
            group=self.group,
            priority=self.priority,
            color=self.color,
            metadata=self.metadata,
        )

    def fits_in(self, width: float, height: float) -> bool:
        """Check if this rect fits within the given dimensions."""
        return self.width <= width + 1e-9 and self.height <= height + 1e-9

    def rotated_fits_in(self, width: float, height: float) -> bool:
        """Check if rotated version fits within the given dimensions."""
        return self.height <= width + 1e-9 and self.width <= height + 1e-9

    def __repr__(self) -> str:
        label_part = f" '{self.label}'" if self.label else ""
        return f"Rect({self.width}x{self.height}{label_part}, rid={self.rid[:8]})"


@dataclass
class Placement:
    """
    A placed rectangle within a bin.

    Attributes:
        rect: The original rectangle.
        x: X coordinate of the top-left corner.
        y: Y coordinate of the top-left corner.
        rotated: Whether the rectangle was rotated 90 degrees.
        bin_index: Which bin this was placed in.
    """
    rect: Rect
    x: float
    y: float
    rotated: bool = False
    bin_index: int = 0

    @property
    def placed_width(self) -> float:
        return self.rect.height if self.rotated else self.rect.width

    @property
    def placed_height(self) -> float:
        return self.rect.width if self.rotated else self.rect.height

    @property
    def right(self) -> float:
        return self.x + self.placed_width

    @property
    def bottom(self) -> float:
        return self.y + self.placed_height

    @property
    def center(self) -> Point:
        return Point(self.x + self.placed_width / 2, self.y + self.placed_height / 2)

    @property
    def area(self) -> float:
        return self.placed_width * self.placed_height

    @property
    def corners(self) -> Tuple[Point, Point, Point, Point]:
        """Return corners: top-left, top-right, bottom-right, bottom-left."""
        return (
            Point(self.x, self.y),
            Point(self.right, self.y),
            Point(self.right, self.bottom),
            Point(self.x, self.bottom),
        )

    def overlaps(self, other: Placement) -> bool:
        """Check if this placement overlaps with another."""
        if self.x >= other.right - 1e-9 or other.x >= self.right - 1e-9:
            return False
        if self.y >= other.bottom - 1e-9 or other.y >= self.bottom - 1e-9:
            return False
        return True

    def overlap_area(self, other: Placement) -> float:
        """Calculate the overlapping area between two placements."""
        x_overlap = max(0, min(self.right, other.right) - max(self.x, other.x))
        y_overlap = max(0, min(self.bottom, other.bottom) - max(self.y, other.y))
        return x_overlap * y_overlap

    def contains_point(self, p: Point) -> bool:
        """Check if a point is inside this placement."""
        return self.x <= p.x <= self.right and self.y <= p.y <= self.bottom

    def distance_to(self, other: Placement) -> float:
        """Minimum distance between two placements (0 if overlapping)."""
        dx = max(0, max(self.x - other.right, other.x - self.right))
        dy = max(0, max(self.y - other.bottom, other.y - self.bottom))
        return math.hypot(dx, dy)

    def __repr__(self) -> str:
        rot = " R" if self.rotated else ""
        return f"Placement({self.rect.rid[:8]} at ({self.x},{self.y}) {self.placed_width}x{self.placed_height}{rot})"


@dataclass
class FreeSpace:
    """An axis-aligned rectangular region of free space in a bin."""
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def can_fit(self, w: float, h: float) -> bool:
        return w <= self.width + 1e-9 and h <= self.height + 1e-9

    def overlaps_rect(self, x: float, y: float, w: float, h: float) -> bool:
        if self.x >= x + w - 1e-9 or x >= self.right - 1e-9:
            return False
        if self.y >= y + h - 1e-9 or y >= self.bottom - 1e-9:
            return False
        return True

    def __repr__(self) -> str:
        return f"FreeSpace({self.x},{self.y} {self.width}x{self.height})"


@dataclass
class Bin:
    """
    A container bin for packing rectangles into.

    Attributes:
        width: Width of the bin.
        height: Height of the bin.
        bid: Unique identifier.
        label: Human-readable label.
        padding: Internal padding from edges.
        allow_overflow: If True, rects can extend beyond bin boundaries.
    """
    width: float
    height: float
    bid: str = ""
    label: str = ""
    padding: float = 0.0
    allow_overflow: bool = False

    def __post_init__(self):
        if not self.bid:
            self.bid = uuid.uuid4().hex[:12]
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Bin dimensions must be positive, got {self.width}x{self.height}")

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def usable_width(self) -> float:
        return self.width - 2 * self.padding

    @property
    def usable_height(self) -> float:
        return self.height - 2 * self.padding

    @property
    def usable_area(self) -> float:
        return self.usable_width * self.usable_height

    def __repr__(self) -> str:
        label_part = f" '{self.label}'" if self.label else ""
        return f"Bin({self.width}x{self.height}{label_part})"


@dataclass
class PackingResult:
    """
    The result of a packing operation.

    Contains placements, statistics, and any rejected rects.
    """
    placements: List[Placement] = field(default_factory=list)
    rejected: List[Rect] = field(default_factory=list)
    bins_used: int = 0
    algorithm: str = ""
    elapsed_ms: float = 0.0
    iterations: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_placed(self) -> int:
        return len(self.placements)

    @property
    def total_rejected(self) -> int:
        return len(self.rejected)

    @property
    def placed_area(self) -> float:
        return sum(p.area for p in self.placements)

    @property
    def all_placed(self) -> bool:
        return len(self.rejected) == 0

    def efficiency(self, bins: List[Bin]) -> float:
        """Calculate packing efficiency as placed area / total bin area."""
        if not bins:
            return 0.0
        total_bin_area = sum(b.area for b in bins[:self.bins_used])
        if total_bin_area == 0:
            return 0.0
        return self.placed_area / total_bin_area

    def bin_efficiency(self, bin_index: int, bin_obj: Bin) -> float:
        """Calculate efficiency for a specific bin."""
        placed_in_bin = sum(p.area for p in self.placements if p.bin_index == bin_index)
        return placed_in_bin / bin_obj.area if bin_obj.area > 0 else 0.0

    def placements_in_bin(self, bin_index: int) -> List[Placement]:
        """Get all placements in a specific bin."""
        return [p for p in self.placements if p.bin_index == bin_index]

    def has_overlaps(self) -> bool:
        """Check if any placements overlap."""
        for i, p1 in enumerate(self.placements):
            for p2 in self.placements[i + 1:]:
                if p1.bin_index == p2.bin_index and p1.overlaps(p2):
                    return True
        return False

    def find_overlaps(self) -> List[Tuple[Placement, Placement]]:
        """Find all overlapping placement pairs."""
        overlaps = []
        for i, p1 in enumerate(self.placements):
            for p2 in self.placements[i + 1:]:
                if p1.bin_index == p2.bin_index and p1.overlaps(p2):
                    overlaps.append((p1, p2))
        return overlaps

    def bounding_box(self, bin_index: int = 0) -> Tuple[float, float]:
        """Get the bounding box of all placements in a bin."""
        bin_placements = self.placements_in_bin(bin_index)
        if not bin_placements:
            return (0.0, 0.0)
        max_x = max(p.right for p in bin_placements)
        max_y = max(p.bottom for p in bin_placements)
        return (max_x, max_y)

    def summary(self) -> str:
        """Return a human-readable summary of the result."""
        lines = [
            f"Packing Result ({self.algorithm})",
            f"  Placed: {self.total_placed}, Rejected: {self.total_rejected}",
            f"  Bins used: {self.bins_used}",
            f"  Placed area: {self.placed_area:.1f}",
            f"  Time: {self.elapsed_ms:.1f}ms",
        ]
        if self.iterations > 0:
            lines.append(f"  Iterations: {self.iterations}")
        return "\n".join(lines)

    def merge(self, other: PackingResult, bin_offset: int = 0) -> PackingResult:
        """Merge another result into this one, offsetting bin indices."""
        new_placements = list(self.placements)
        for p in other.placements:
            new_placements.append(Placement(
                rect=p.rect, x=p.x, y=p.y,
                rotated=p.rotated, bin_index=p.bin_index + bin_offset,
            ))
        return PackingResult(
            placements=new_placements,
            rejected=self.rejected + [r for r in other.rejected if r.rid not in {x.rid for x in self.rejected}],
            bins_used=max(self.bins_used, other.bins_used + bin_offset),
            algorithm=self.algorithm or other.algorithm,
            elapsed_ms=self.elapsed_ms + other.elapsed_ms,
            iterations=self.iterations + other.iterations,
        )


@dataclass
class PackingProblem:
    """
    A complete packing problem definition.

    Attributes:
        rects: Rectangles to pack.
        bins: Available bins (if empty, a single infinite bin is assumed).
        rotation: Rotation policy.
        sort_strategy: How to sort rects before packing.
        spacing: Minimum spacing between packed rects.
        multi_bin: Whether to use multiple bins.
    """
    rects: List[Rect] = field(default_factory=list)
    bins: List[Bin] = field(default_factory=list)
    rotation: RotationPolicy = RotationPolicy.NONE
    sort_strategy: SortStrategy = SortStrategy.AREA_DESC
    spacing: float = 0.0
    multi_bin: bool = False

    def add_rect(self, width: float, height: float, **kwargs) -> Rect:
        """Add a rectangle to the problem and return it."""
        r = Rect(width=width, height=height, **kwargs)
        self.rects.append(r)
        return r

    def add_bin(self, width: float, height: float, **kwargs) -> Bin:
        """Add a bin to the problem and return it."""
        b = Bin(width=width, height=height, **kwargs)
        self.bins.append(b)
        return b

    @property
    def total_rect_area(self) -> float:
        return sum(r.area for r in self.rects)

    @property
    def total_bin_area(self) -> float:
        return sum(b.area for b in self.bins) if self.bins else float('inf')

    @property
    def theoretical_min_bins(self) -> int:
        """Minimum bins needed assuming perfect packing."""
        if not self.bins:
            return 1
        max_bin_area = max(b.area for b in self.bins)
        return math.ceil(self.total_rect_area / max_bin_area) if max_bin_area > 0 else 1

    def sorted_rects(self) -> List[Rect]:
        """Return rects sorted according to the sort strategy."""
        rects = list(self.rects)
        # Always sort by priority first (descending)
        rects.sort(key=lambda r: r.priority, reverse=True)

        key_map = {
            SortStrategy.NONE: None,
            SortStrategy.AREA_DESC: lambda r: r.area,
            SortStrategy.PERIMETER_DESC: lambda r: r.perimeter,
            SortStrategy.WIDTH_DESC: lambda r: r.width,
            SortStrategy.HEIGHT_DESC: lambda r: r.height,
            SortStrategy.MAX_SIDE_DESC: lambda r: r.max_side,
            SortStrategy.ASPECT_RATIO_DESC: lambda r: r.aspect_ratio,
            SortStrategy.SHORT_SIDE_DESC: lambda r: r.min_side,
            SortStrategy.LONG_SIDE_DESC: lambda r: r.max_side,
        }
        key_fn = key_map.get(self.sort_strategy)
        if key_fn is not None:
            # Stable sort preserves priority ordering within same-priority groups
            rects.sort(key=key_fn, reverse=True)
            # Re-sort by priority to ensure it takes precedence
            rects.sort(key=lambda r: r.priority, reverse=True)
        return rects

    def validate(self) -> List[str]:
        """Validate the problem and return a list of issues."""
        issues = []
        if not self.rects:
            issues.append("No rectangles to pack")
        for r in self.rects:
            if r.width <= 0 or r.height <= 0:
                issues.append(f"Rect {r.rid} has non-positive dimensions")
        if not self.bins:
            issues.append("No bins defined (will use auto-sizing)")
        for b in self.bins:
            if b.width <= 0 or b.height <= 0:
                issues.append(f"Bin {b.bid} has non-positive dimensions")
        # Check if any rect is too large for all bins
        if self.bins:
            for r in self.rects:
                can_fit = False
                for b in self.bins:
                    if r.fits_in(b.usable_width, b.usable_height):
                        can_fit = True
                        break
                    if self.rotation != RotationPolicy.NONE and r.rotated_fits_in(b.usable_width, b.usable_height):
                        can_fit = True
                        break
                if not can_fit:
                    issues.append(f"Rect {r.rid} ({r.width}x{r.height}) doesn't fit in any bin")
        return issues

    def __repr__(self) -> str:
        return f"PackingProblem({len(self.rects)} rects, {len(self.bins)} bins)"


def sort_rects(rects: List[Rect], strategy: SortStrategy) -> List[Rect]:
    """Sort a list of rects by the given strategy (utility function)."""
    result = list(rects)
    key_map = {
        SortStrategy.NONE: None,
        SortStrategy.AREA_DESC: lambda r: r.area,
        SortStrategy.PERIMETER_DESC: lambda r: r.perimeter,
        SortStrategy.WIDTH_DESC: lambda r: r.width,
        SortStrategy.HEIGHT_DESC: lambda r: r.height,
        SortStrategy.MAX_SIDE_DESC: lambda r: r.max_side,
        SortStrategy.ASPECT_RATIO_DESC: lambda r: r.aspect_ratio,
        SortStrategy.SHORT_SIDE_DESC: lambda r: r.min_side,
        SortStrategy.LONG_SIDE_DESC: lambda r: r.max_side,
    }
    key_fn = key_map.get(strategy)
    if key_fn is not None:
        result.sort(key=key_fn, reverse=True)
    return result
