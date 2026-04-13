"""
Statistical analysis of packing results.

Computes detailed metrics about packing quality, waste distribution,
and algorithm comparison.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from tessera.core import Bin, PackingResult, Placement


@dataclass
class BinStats:
    """Statistics for a single bin."""
    bin_index: int
    bin_width: float
    bin_height: float
    bin_area: float
    placed_count: int
    placed_area: float
    efficiency: float
    bounding_box: Tuple[float, float]
    bb_efficiency: float  # placed_area / bounding_box_area
    avg_rect_area: float
    max_rect_area: float
    min_rect_area: float
    fragmentation: float  # Estimate of how fragmented free space is
    waste_area: float


@dataclass
class PackingStats:
    """
    Comprehensive statistics for a packing result.
    """

    def __init__(self, result: PackingResult, bins: List[Bin]):
        self.result = result
        self.bins = bins

    @property
    def total_placed(self) -> int:
        return self.result.total_placed

    @property
    def total_rejected(self) -> int:
        return self.result.total_rejected

    @property
    def bins_used(self) -> int:
        return self.result.bins_used

    @property
    def overall_efficiency(self) -> float:
        return self.result.efficiency(self.bins)

    @property
    def placed_area(self) -> float:
        return self.result.placed_area

    @property
    def total_bin_area(self) -> float:
        return sum(
            self.bins[i].area
            for i in range(min(self.result.bins_used, len(self.bins)))
        )

    @property
    def waste_area(self) -> float:
        return self.total_bin_area - self.placed_area

    @property
    def has_overlaps(self) -> bool:
        return self.result.has_overlaps()

    def per_bin_stats(self) -> List[BinStats]:
        """Get detailed statistics for each bin."""
        stats = []

        for bin_idx in range(self.result.bins_used):
            if bin_idx >= len(self.bins):
                break

            bin_obj = self.bins[bin_idx]
            placements = self.result.placements_in_bin(bin_idx)

            placed_area = sum(p.area for p in placements)
            bb = self.result.bounding_box(bin_idx)
            bb_area = bb[0] * bb[1] if bb[0] > 0 and bb[1] > 0 else 0

            rect_areas = [p.area for p in placements] if placements else [0]

            # Fragmentation estimate: ratio of gaps to total area
            frag = self._estimate_fragmentation(placements, bin_obj)

            stats.append(BinStats(
                bin_index=bin_idx,
                bin_width=bin_obj.width,
                bin_height=bin_obj.height,
                bin_area=bin_obj.area,
                placed_count=len(placements),
                placed_area=placed_area,
                efficiency=placed_area / bin_obj.area if bin_obj.area > 0 else 0,
                bounding_box=bb,
                bb_efficiency=placed_area / bb_area if bb_area > 0 else 0,
                avg_rect_area=sum(rect_areas) / len(rect_areas),
                max_rect_area=max(rect_areas),
                min_rect_area=min(rect_areas),
                fragmentation=frag,
                waste_area=bin_obj.area - placed_area,
            ))

        return stats

    def _estimate_fragmentation(
        self,
        placements: List[Placement],
        bin_obj: Bin,
    ) -> float:
        """
        Estimate fragmentation of free space.

        Uses a scanline approach to count transitions between
        occupied and free space. More transitions = more fragmentation.
        """
        if not placements:
            return 0.0

        # Simple approach: count how many distinct free space regions
        # exist in a coarse grid
        grid_size = 20
        cell_w = bin_obj.width / grid_size
        cell_h = bin_obj.height / grid_size

        grid = [[False] * grid_size for _ in range(grid_size)]

        for p in placements:
            x1 = int(p.x / cell_w)
            y1 = int(p.y / cell_h)
            x2 = int(p.right / cell_w)
            y2 = int(p.bottom / cell_h)

            for r in range(max(0, y1), min(grid_size, y2 + 1)):
                for c in range(max(0, x1), min(grid_size, x2 + 1)):
                    grid[r][c] = True

        # Count transitions (occupied <-> free)
        transitions = 0
        for r in range(grid_size):
            for c in range(grid_size - 1):
                if grid[r][c] != grid[r][c + 1]:
                    transitions += 1
        for c in range(grid_size):
            for r in range(grid_size - 1):
                if grid[r][c] != grid[r + 1][c]:
                    transitions += 1

        # Normalize
        max_transitions = 2 * grid_size * (grid_size - 1)
        return transitions / max_transitions if max_transitions > 0 else 0

    def size_distribution(self) -> Dict[str, int]:
        """Categorize placed rects by size."""
        categories = {"tiny": 0, "small": 0, "medium": 0, "large": 0, "huge": 0}

        if not self.result.placements:
            return categories

        areas = [p.area for p in self.result.placements]
        avg_area = sum(areas) / len(areas)

        for a in areas:
            ratio = a / avg_area if avg_area > 0 else 1
            if ratio < 0.25:
                categories["tiny"] += 1
            elif ratio < 0.5:
                categories["small"] += 1
            elif ratio < 1.5:
                categories["medium"] += 1
            elif ratio < 3.0:
                categories["large"] += 1
            else:
                categories["huge"] += 1

        return categories

    def rotation_stats(self) -> Dict[str, int]:
        """Count rotated vs non-rotated placements."""
        rotated = sum(1 for p in self.result.placements if p.rotated)
        return {
            "rotated": rotated,
            "not_rotated": self.total_placed - rotated,
        }

    def summary(self) -> str:
        """Generate a comprehensive text summary."""
        lines = [
            "=" * 60,
            f"  Tessera Packing Report — {self.result.algorithm}",
            "=" * 60,
            "",
            f"  Placed: {self.total_placed}  |  Rejected: {self.total_rejected}",
            f"  Bins used: {self.bins_used}",
            f"  Overall efficiency: {self.overall_efficiency:.1%}",
            f"  Total placed area: {self.placed_area:.0f}",
            f"  Total waste area: {self.waste_area:.0f}",
            f"  Time: {self.result.elapsed_ms:.1f}ms",
            f"  Overlaps: {'YES (!)' if self.has_overlaps else 'None'}",
            "",
        ]

        # Per-bin stats
        bin_stats = self.per_bin_stats()
        if bin_stats:
            lines.append("  Per-bin breakdown:")
            for bs in bin_stats:
                lines.append(
                    f"    Bin {bs.bin_index}: {bs.placed_count} rects, "
                    f"{bs.efficiency:.1%} eff, "
                    f"frag={bs.fragmentation:.2f}, "
                    f"BB={bs.bounding_box[0]:.0f}x{bs.bounding_box[1]:.0f}"
                )
            lines.append("")

        # Size distribution
        dist = self.size_distribution()
        lines.append("  Size distribution:")
        for cat, count in dist.items():
            if count > 0:
                lines.append(f"    {cat}: {count}")
        lines.append("")

        # Rotation stats
        rot = self.rotation_stats()
        if rot["rotated"] > 0:
            lines.append(
                f"  Rotations: {rot['rotated']} rotated, "
                f"{rot['not_rotated']} original"
            )
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def compare(self, other: "PackingStats") -> str:
        """Compare two packing results."""
        lines = [
            "Comparison:",
            f"  {'Metric':<25} {'This':>12} {'Other':>12} {'Delta':>12}",
            f"  {'-'*25} {'-'*12} {'-'*12} {'-'*12}",
        ]

        metrics = [
            ("Placed", self.total_placed, other.total_placed),
            ("Rejected", self.total_rejected, other.total_rejected),
            ("Bins used", self.bins_used, other.bins_used),
            ("Efficiency", f"{self.overall_efficiency:.2%}", f"{other.overall_efficiency:.2%}"),
            ("Time (ms)", f"{self.result.elapsed_ms:.1f}", f"{other.result.elapsed_ms:.1f}"),
        ]

        for name, v1, v2 in metrics:
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                delta = v1 - v2
                lines.append(f"  {name:<25} {v1:>12} {v2:>12} {delta:>+12}")
            else:
                lines.append(f"  {name:<25} {v1:>12} {v2:>12}")

        return "\n".join(lines)
