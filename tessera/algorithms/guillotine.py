"""
Guillotine algorithm for 2D bin packing.

Uses guillotine cuts (full horizontal or vertical splits) to divide free space.
Simpler than MaxRects but can be more efficient for certain problem types,
especially when cuts correspond to physical manufacturing constraints.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import List, Optional, Tuple

from tessera.core import Bin, FreeSpace, Placement, Rect, RotationPolicy
from tessera.algorithms.base import BaseAlgorithm


class GuillotineSplit(Enum):
    """How to split remaining space after placing a rectangle."""
    SHORTER_LEFTOVER = auto()  # Split along the shorter leftover axis
    LONGER_LEFTOVER = auto()   # Split along the longer leftover axis
    SHORTER_AXIS = auto()      # Split along the shorter free rect axis
    LONGER_AXIS = auto()       # Split along the longer free rect axis
    HORIZONTAL = auto()        # Always split horizontally
    VERTICAL = auto()          # Always split vertically
    MIN_AREA = auto()          # Choose split that minimizes wasted area


class GuillotineChoice(Enum):
    """How to choose which free rect to place into."""
    BEST_AREA_FIT = auto()     # Smallest area free rect that fits
    BEST_SHORT_SIDE = auto()   # Smallest short side difference
    BEST_LONG_SIDE = auto()    # Smallest long side difference
    WORST_AREA_FIT = auto()    # Largest area free rect
    WORST_SHORT_SIDE = auto()  # Largest short side difference
    WORST_LONG_SIDE = auto()   # Largest long side difference


class GuillotineAlgorithm(BaseAlgorithm):
    """
    Guillotine packing algorithm.

    Divides the bin into rectangular regions using full guillotine cuts.
    Each time a rectangle is placed, the remaining space in that free
    rectangle is split into exactly two new free rectangles.
    """

    name = "guillotine"

    def __init__(
        self,
        choice: GuillotineChoice = GuillotineChoice.BEST_AREA_FIT,
        split: GuillotineSplit = GuillotineSplit.SHORTER_LEFTOVER,
        rotation: RotationPolicy = RotationPolicy.NONE,
        spacing: float = 0.0,
        merge: bool = True,
    ):
        super().__init__(rotation=rotation, spacing=spacing)
        self.choice = choice
        self.split = split
        self.merge = merge
        self._free_rects: List[FreeSpace] = []

    def pack_into_bin(
        self,
        rects: List[Rect],
        bin_obj: Bin,
    ) -> Tuple[List[Placement], List[Rect]]:
        self._free_rects = [FreeSpace(
            x=bin_obj.padding,
            y=bin_obj.padding,
            width=bin_obj.usable_width,
            height=bin_obj.usable_height,
        )]

        placed = []
        rejected = []

        for rect in rects:
            placement, free_idx = self._find_best_placement(rect)
            if placement is not None and free_idx is not None:
                self._split_free_rect(free_idx, placement)
                placed.append(placement)
                if self.merge:
                    self._merge_free_rects()
            else:
                rejected.append(rect)

        return placed, rejected

    def _find_best_placement(
        self,
        rect: Rect,
    ) -> Tuple[Optional[Placement], Optional[int]]:
        """Find best free rect for placement according to choice heuristic."""
        best_score = float('inf')
        best_placement = None
        best_idx = None

        ew = self._effective_width(rect)
        eh = self._effective_height(rect)

        for i, free_rect in enumerate(self._free_rects):
            # Try without rotation
            if free_rect.can_fit(ew, eh):
                score = self._score_choice(rect, free_rect, False)
                if score < best_score:
                    best_score = score
                    best_placement = Placement(
                        rect=rect, x=free_rect.x, y=free_rect.y, rotated=False
                    )
                    best_idx = i

            # Try with rotation
            if self._can_rotate(rect):
                ew_r = self._effective_width(rect, rotated=True)
                eh_r = self._effective_height(rect, rotated=True)
                if free_rect.can_fit(ew_r, eh_r):
                    score = self._score_choice(rect, free_rect, True)
                    if score < best_score:
                        best_score = score
                        best_placement = Placement(
                            rect=rect, x=free_rect.x, y=free_rect.y, rotated=True
                        )
                        best_idx = i

        return best_placement, best_idx

    def _score_choice(
        self,
        rect: Rect,
        free_rect: FreeSpace,
        rotated: bool,
    ) -> float:
        """Score a free rect choice. Lower is better."""
        pw = self._effective_width(rect, rotated)
        ph = self._effective_height(rect, rotated)

        if self.choice == GuillotineChoice.BEST_AREA_FIT:
            return free_rect.area - pw * ph

        elif self.choice == GuillotineChoice.BEST_SHORT_SIDE:
            leftover_h = abs(free_rect.width - pw)
            leftover_v = abs(free_rect.height - ph)
            return min(leftover_h, leftover_v)

        elif self.choice == GuillotineChoice.BEST_LONG_SIDE:
            leftover_h = abs(free_rect.width - pw)
            leftover_v = abs(free_rect.height - ph)
            return max(leftover_h, leftover_v)

        elif self.choice == GuillotineChoice.WORST_AREA_FIT:
            return -(free_rect.area - pw * ph)

        elif self.choice == GuillotineChoice.WORST_SHORT_SIDE:
            leftover_h = abs(free_rect.width - pw)
            leftover_v = abs(free_rect.height - ph)
            return -min(leftover_h, leftover_v)

        elif self.choice == GuillotineChoice.WORST_LONG_SIDE:
            leftover_h = abs(free_rect.width - pw)
            leftover_v = abs(free_rect.height - ph)
            return -max(leftover_h, leftover_v)

        return 0

    def _split_free_rect(self, free_idx: int, placement: Placement) -> None:
        """Split a free rect after placing a rectangle in it."""
        free_rect = self._free_rects.pop(free_idx)

        pw = placement.placed_width + self.spacing
        ph = placement.placed_height + self.spacing

        # Remaining space to the right
        right_w = free_rect.right - (free_rect.x + pw)
        # Remaining space below
        bottom_h = free_rect.bottom - (free_rect.y + ph)

        do_horizontal = self._choose_split_direction(
            free_rect, pw, ph, right_w, bottom_h
        )

        if do_horizontal:
            # Horizontal split: right piece gets full height, bottom piece is narrower
            if right_w > 1e-9:
                self._free_rects.append(FreeSpace(
                    x=free_rect.x + pw,
                    y=free_rect.y,
                    width=right_w,
                    height=free_rect.height,
                ))
            if bottom_h > 1e-9:
                self._free_rects.append(FreeSpace(
                    x=free_rect.x,
                    y=free_rect.y + ph,
                    width=pw,
                    height=bottom_h,
                ))
        else:
            # Vertical split: bottom piece gets full width, right piece is shorter
            if right_w > 1e-9:
                self._free_rects.append(FreeSpace(
                    x=free_rect.x + pw,
                    y=free_rect.y,
                    width=right_w,
                    height=ph,
                ))
            if bottom_h > 1e-9:
                self._free_rects.append(FreeSpace(
                    x=free_rect.x,
                    y=free_rect.y + ph,
                    width=free_rect.width,
                    height=bottom_h,
                ))

    def _choose_split_direction(
        self,
        free_rect: FreeSpace,
        pw: float,
        ph: float,
        right_w: float,
        bottom_h: float,
    ) -> bool:
        """Choose split direction. Returns True for horizontal, False for vertical."""
        if self.split == GuillotineSplit.HORIZONTAL:
            return True
        elif self.split == GuillotineSplit.VERTICAL:
            return False
        elif self.split == GuillotineSplit.SHORTER_LEFTOVER:
            return right_w < bottom_h
        elif self.split == GuillotineSplit.LONGER_LEFTOVER:
            return right_w >= bottom_h
        elif self.split == GuillotineSplit.SHORTER_AXIS:
            return free_rect.width < free_rect.height
        elif self.split == GuillotineSplit.LONGER_AXIS:
            return free_rect.width >= free_rect.height
        elif self.split == GuillotineSplit.MIN_AREA:
            # Choose the split that creates the largest single free rect
            h_area = max(right_w * free_rect.height, pw * bottom_h) if right_w > 0 or bottom_h > 0 else 0
            v_area = max(right_w * ph, free_rect.width * bottom_h) if right_w > 0 or bottom_h > 0 else 0
            return h_area >= v_area
        return True

    def _merge_free_rects(self) -> None:
        """Merge adjacent free rects that form a larger rectangle."""
        merged = True
        while merged:
            merged = False
            i = 0
            while i < len(self._free_rects):
                j = i + 1
                while j < len(self._free_rects):
                    fi = self._free_rects[i]
                    fj = self._free_rects[j]

                    new_rect = self._try_merge(fi, fj)
                    if new_rect is not None:
                        self._free_rects[i] = new_rect
                        self._free_rects.pop(j)
                        merged = True
                    else:
                        j += 1
                i += 1

    def _try_merge(
        self, a: FreeSpace, b: FreeSpace
    ) -> Optional[FreeSpace]:
        """Try to merge two free rects. Returns merged rect or None."""
        # Same width, vertically adjacent
        if (abs(a.x - b.x) < 1e-9 and abs(a.width - b.width) < 1e-9):
            if abs(a.bottom - b.y) < 1e-9:
                return FreeSpace(a.x, a.y, a.width, a.height + b.height)
            if abs(b.bottom - a.y) < 1e-9:
                return FreeSpace(b.x, b.y, b.width, a.height + b.height)

        # Same height, horizontally adjacent
        if (abs(a.y - b.y) < 1e-9 and abs(a.height - b.height) < 1e-9):
            if abs(a.right - b.x) < 1e-9:
                return FreeSpace(a.x, a.y, a.width + b.width, a.height)
            if abs(b.right - a.x) < 1e-9:
                return FreeSpace(b.x, b.y, a.width + b.width, b.height)

        return None
