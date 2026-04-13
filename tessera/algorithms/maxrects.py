"""
MaxRects algorithm for 2D bin packing.

Maintains a list of maximal free rectangles and places items using various
heuristics (Best Short Side Fit, Best Long Side Fit, Best Area Fit, etc.).
This is one of the most effective online packing algorithms.

Reference: Jukka Jylanki, "A Thousand Ways to Pack the Bin"
"""

from __future__ import annotations

from enum import Enum, auto
from typing import List, Optional, Tuple

from tessera.core import Bin, FreeSpace, Placement, Rect, RotationPolicy
from tessera.algorithms.base import BaseAlgorithm


class MaxRectsHeuristic(Enum):
    """Heuristic for choosing placement within the MaxRects algorithm."""
    BSSF = auto()  # Best Short Side Fit
    BLSF = auto()  # Best Long Side Fit
    BAF = auto()   # Best Area Fit
    CP = auto()     # Contact Point (maximize touching edges)
    BL = auto()     # Bottom-Left


class MaxRectsAlgorithm(BaseAlgorithm):
    """
    MaxRects packing algorithm.

    Maintains a list of maximal free rectangles. When a rectangle is placed,
    the overlapping free rects are split and merged. Uses configurable
    heuristics for choosing which free rect to use.
    """

    name = "maxrects"

    def __init__(
        self,
        heuristic: MaxRectsHeuristic = MaxRectsHeuristic.BSSF,
        rotation: RotationPolicy = RotationPolicy.NONE,
        spacing: float = 0.0,
    ):
        super().__init__(rotation=rotation, spacing=spacing)
        self.heuristic = heuristic
        self._free_rects: List[FreeSpace] = []
        self._placements: List[Placement] = []

    def pack_into_bin(
        self,
        rects: List[Rect],
        bin_obj: Bin,
    ) -> Tuple[List[Placement], List[Rect]]:
        # Initialize free rect list with the full usable area
        self._free_rects = [FreeSpace(
            x=bin_obj.padding,
            y=bin_obj.padding,
            width=bin_obj.usable_width,
            height=bin_obj.usable_height,
        )]
        self._placements = []

        placed = []
        rejected = []

        for rect in rects:
            placement = self._find_best_placement(rect, bin_obj)
            if placement is not None:
                self._place_rect(placement)
                placed.append(placement)
            else:
                rejected.append(rect)

        return placed, rejected

    def _find_best_placement(
        self,
        rect: Rect,
        bin_obj: Bin,
    ) -> Optional[Placement]:
        """Find the best placement for a rect according to the heuristic."""
        best_score1 = float('inf')
        best_score2 = float('inf')
        best_placement = None

        ew = self._effective_width(rect)
        eh = self._effective_height(rect)

        for free_rect in self._free_rects:
            # Try without rotation
            if free_rect.can_fit(ew, eh):
                score1, score2 = self._score_placement(
                    rect, free_rect, False, bin_obj
                )
                if score1 < best_score1 or (score1 == best_score1 and score2 < best_score2):
                    best_score1 = score1
                    best_score2 = score2
                    best_placement = Placement(
                        rect=rect, x=free_rect.x, y=free_rect.y, rotated=False
                    )

            # Try with rotation
            if self._can_rotate(rect):
                ew_r = self._effective_width(rect, rotated=True)
                eh_r = self._effective_height(rect, rotated=True)
                if free_rect.can_fit(ew_r, eh_r):
                    score1, score2 = self._score_placement(
                        rect, free_rect, True, bin_obj
                    )
                    if score1 < best_score1 or (score1 == best_score1 and score2 < best_score2):
                        best_score1 = score1
                        best_score2 = score2
                        best_placement = Placement(
                            rect=rect, x=free_rect.x, y=free_rect.y, rotated=True
                        )

        return best_placement

    def _score_placement(
        self,
        rect: Rect,
        free_rect: FreeSpace,
        rotated: bool,
        bin_obj: Bin,
    ) -> Tuple[float, float]:
        """Score a placement using the configured heuristic. Lower is better."""
        pw = rect.height if rotated else rect.width
        ph = rect.width if rotated else rect.height
        pw += self.spacing
        ph += self.spacing

        if self.heuristic == MaxRectsHeuristic.BSSF:
            leftover_h = abs(free_rect.width - pw)
            leftover_v = abs(free_rect.height - ph)
            return (min(leftover_h, leftover_v), max(leftover_h, leftover_v))

        elif self.heuristic == MaxRectsHeuristic.BLSF:
            leftover_h = abs(free_rect.width - pw)
            leftover_v = abs(free_rect.height - ph)
            return (max(leftover_h, leftover_v), min(leftover_h, leftover_v))

        elif self.heuristic == MaxRectsHeuristic.BAF:
            area_fit = free_rect.area - pw * ph
            short_side = min(abs(free_rect.width - pw), abs(free_rect.height - ph))
            return (area_fit, short_side)

        elif self.heuristic == MaxRectsHeuristic.CP:
            # Contact point: maximize edges touching bin walls or other rects
            contact = self._compute_contact_score(
                free_rect.x, free_rect.y, pw, ph, bin_obj
            )
            return (-contact, 0)  # Negate because lower is better

        elif self.heuristic == MaxRectsHeuristic.BL:
            # Bottom-left: prefer lower y, then lower x
            return (free_rect.y, free_rect.x)

        return (0, 0)

    def _compute_contact_score(
        self, x: float, y: float, w: float, h: float, bin_obj: Bin
    ) -> float:
        """Compute contact score for Contact Point heuristic."""
        score = 0.0

        # Contact with bin edges
        if x <= bin_obj.padding + 1e-9:
            score += h
        if y <= bin_obj.padding + 1e-9:
            score += w
        if x + w >= bin_obj.width - bin_obj.padding - 1e-9:
            score += h
        if y + h >= bin_obj.height - bin_obj.padding - 1e-9:
            score += w

        # Contact with existing placements
        for p in self._placements:
            # Left/right contact
            if (abs(p.right - x) < 1e-9 or abs(x + w - p.x) < 1e-9):
                overlap = min(y + h, p.bottom) - max(y, p.y)
                if overlap > 0:
                    score += overlap
            # Top/bottom contact
            if (abs(p.bottom - y) < 1e-9 or abs(y + h - p.y) < 1e-9):
                overlap = min(x + w, p.right) - max(x, p.x)
                if overlap > 0:
                    score += overlap

        return score

    def _place_rect(self, placement: Placement) -> None:
        """Place a rectangle and update free space list."""
        self._placements.append(placement)

        # Placed rectangle bounds (with spacing)
        px = placement.x
        py = placement.y
        pw = placement.placed_width + self.spacing
        ph = placement.placed_height + self.spacing

        new_free = []
        for free_rect in self._free_rects:
            if not free_rect.overlaps_rect(px, py, pw, ph):
                new_free.append(free_rect)
                continue

            # Split the free rect around the placed rect
            # Left piece
            if px > free_rect.x:
                new_free.append(FreeSpace(
                    x=free_rect.x, y=free_rect.y,
                    width=px - free_rect.x, height=free_rect.height,
                ))
            # Right piece
            if px + pw < free_rect.right:
                new_free.append(FreeSpace(
                    x=px + pw, y=free_rect.y,
                    width=free_rect.right - (px + pw), height=free_rect.height,
                ))
            # Top piece
            if py > free_rect.y:
                new_free.append(FreeSpace(
                    x=free_rect.x, y=free_rect.y,
                    width=free_rect.width, height=py - free_rect.y,
                ))
            # Bottom piece
            if py + ph < free_rect.bottom:
                new_free.append(FreeSpace(
                    x=free_rect.x, y=py + ph,
                    width=free_rect.width, height=free_rect.bottom - (py + ph),
                ))

        self._free_rects = self._prune_free_rects(new_free)

    def _prune_free_rects(self, free_rects: List[FreeSpace]) -> List[FreeSpace]:
        """Remove free rects that are fully contained by another free rect."""
        result = []
        n = len(free_rects)
        contained = [False] * n

        for i in range(n):
            if contained[i]:
                continue
            for j in range(n):
                if i == j or contained[j]:
                    continue
                # Check if i is contained in j
                fi = free_rects[i]
                fj = free_rects[j]
                if (fi.x >= fj.x - 1e-9 and fi.y >= fj.y - 1e-9 and
                        fi.right <= fj.right + 1e-9 and fi.bottom <= fj.bottom + 1e-9):
                    contained[i] = True
                    break

        for i in range(n):
            if not contained[i] and free_rects[i].area > 1e-9:
                result.append(free_rects[i])

        return result
