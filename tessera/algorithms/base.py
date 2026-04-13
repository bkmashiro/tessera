"""
Base algorithm interface for all packing algorithms.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from tessera.core import (
    Bin, FreeSpace, PackingResult, Placement, Rect, RotationPolicy,
)


class BaseAlgorithm(ABC):
    """
    Abstract base class for packing algorithms.

    Subclasses must implement `pack_into_bin` which attempts to pack a list
    of rectangles into a single bin. The framework handles multi-bin logic.
    """

    name: str = "base"

    def __init__(self, rotation: RotationPolicy = RotationPolicy.NONE, spacing: float = 0.0):
        self.rotation = rotation
        self.spacing = spacing

    @abstractmethod
    def pack_into_bin(
        self,
        rects: List[Rect],
        bin_obj: Bin,
    ) -> Tuple[List[Placement], List[Rect]]:
        """
        Pack rectangles into a single bin.

        Args:
            rects: Rectangles to pack (already sorted).
            bin_obj: The bin to pack into.

        Returns:
            Tuple of (placements, rejected_rects).
        """
        ...

    def pack(
        self,
        rects: List[Rect],
        bins: List[Bin],
        multi_bin: bool = False,
    ) -> PackingResult:
        """
        Pack rectangles into one or more bins.

        Args:
            rects: Rectangles to pack.
            bins: Available bins.
            multi_bin: If True, use multiple bins for overflow.

        Returns:
            PackingResult with all placements and rejected rects.
        """
        start = time.perf_counter()
        result = PackingResult(algorithm=self.name)

        remaining = list(rects)

        for bin_index, bin_obj in enumerate(bins):
            if not remaining:
                break

            placements, rejected = self.pack_into_bin(remaining, bin_obj)

            for p in placements:
                p.bin_index = bin_index
                result.placements.append(p)

            remaining = rejected

            if not multi_bin:
                break

        result.rejected = remaining
        result.bins_used = max(
            (p.bin_index + 1 for p in result.placements), default=0
        )
        result.elapsed_ms = (time.perf_counter() - start) * 1000
        return result

    def _can_rotate(self, rect: Rect) -> bool:
        """Check if a rect can be rotated given current policy."""
        if self.rotation == RotationPolicy.NONE:
            return False
        return rect.rotatable

    def _effective_width(self, rect: Rect, rotated: bool = False) -> float:
        """Get effective width including spacing."""
        w = rect.height if rotated else rect.width
        return w + self.spacing

    def _effective_height(self, rect: Rect, rotated: bool = False) -> float:
        """Get effective height including spacing."""
        h = rect.width if rotated else rect.height
        return h + self.spacing

    def _try_place(
        self,
        rect: Rect,
        space: FreeSpace,
        bin_obj: Bin,
    ) -> Optional[Tuple[float, float, bool]]:
        """
        Try to place a rect in a free space.

        Returns (x, y, rotated) or None if it doesn't fit.
        """
        ew = self._effective_width(rect)
        eh = self._effective_height(rect)

        x = space.x + bin_obj.padding
        y = space.y + bin_obj.padding

        if space.can_fit(ew, eh):
            return (space.x, space.y, False)

        if self._can_rotate(rect):
            ew_r = self._effective_width(rect, rotated=True)
            eh_r = self._effective_height(rect, rotated=True)
            if space.can_fit(ew_r, eh_r):
                return (space.x, space.y, True)

        return None
