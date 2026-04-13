"""
Shelf algorithm for 2D bin packing.

One of the simplest packing approaches: rectangles are placed on horizontal
"shelves" (rows). When a rect doesn't fit on the current shelf, a new shelf
is started. Fast and simple, works well for similarly-sized items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

from tessera.core import Bin, Placement, Rect, RotationPolicy
from tessera.algorithms.base import BaseAlgorithm


class ShelfChoice(Enum):
    """How to choose which shelf to place a rectangle on."""
    NEXT_FIT = auto()       # Always use the current (last) shelf
    FIRST_FIT = auto()      # First shelf that fits
    BEST_WIDTH_FIT = auto() # Shelf with least remaining width
    BEST_HEIGHT_FIT = auto() # Shelf with closest height match
    WORST_WIDTH_FIT = auto() # Shelf with most remaining width (spread out)


@dataclass
class Shelf:
    """A horizontal shelf within a bin."""
    y: float
    height: float
    bin_width: float
    spacing: float = 0.0
    used_width: float = 0.0
    items: List[Placement] = field(default_factory=list)

    @property
    def remaining_width(self) -> float:
        return self.bin_width - self.used_width

    def can_fit(self, width: float, height: float) -> bool:
        return (width + self.spacing <= self.remaining_width + 1e-9 and
                height <= self.height + 1e-9)


class ShelfAlgorithm(BaseAlgorithm):
    """
    Shelf-based packing algorithm.

    Organizes rectangles into horizontal shelves. The height of each shelf
    is determined by the tallest item placed on it. Various heuristics
    control which shelf receives each rectangle.
    """

    name = "shelf"

    def __init__(
        self,
        choice: ShelfChoice = ShelfChoice.FIRST_FIT,
        rotation: RotationPolicy = RotationPolicy.NONE,
        spacing: float = 0.0,
        waste_threshold: float = 0.5,
    ):
        super().__init__(rotation=rotation, spacing=spacing)
        self.choice = choice
        self.waste_threshold = waste_threshold

    def pack_into_bin(
        self,
        rects: List[Rect],
        bin_obj: Bin,
    ) -> Tuple[List[Placement], List[Rect]]:
        shelves: List[Shelf] = []
        placed: List[Placement] = []
        rejected: List[Rect] = []

        usable_w = bin_obj.usable_width
        usable_h = bin_obj.usable_height
        padding = bin_obj.padding

        current_y = padding

        for rect in rects:
            ew = self._effective_width(rect)
            eh = self._effective_height(rect)

            best_shelf, rotated = self._choose_shelf(
                rect, shelves, usable_w
            )

            if best_shelf is not None:
                pw = self._effective_width(rect, rotated)
                ph = self._effective_height(rect, rotated)
                actual_w = rect.height if rotated else rect.width
                actual_h = rect.width if rotated else rect.height

                p = Placement(
                    rect=rect,
                    x=padding + best_shelf.used_width,
                    y=best_shelf.y,
                    rotated=rotated,
                )
                best_shelf.items.append(p)
                best_shelf.used_width += pw
                placed.append(p)
                continue

            # Try to create a new shelf
            new_shelf_h = eh
            if self._can_rotate(rect):
                ew_r = self._effective_width(rect, rotated=True)
                eh_r = self._effective_height(rect, rotated=True)
                # Prefer orientation that creates shorter shelf
                if ew_r <= usable_w + 1e-9 and eh_r < new_shelf_h:
                    new_shelf_h = eh_r

            remaining_h = padding + usable_h - current_y

            if new_shelf_h <= remaining_h + 1e-9:
                # Determine if we need to rotate for the new shelf
                use_rotated = False
                if ew > usable_w + 1e-9 and self._can_rotate(rect):
                    ew_r = self._effective_width(rect, rotated=True)
                    eh_r = self._effective_height(rect, rotated=True)
                    if ew_r <= usable_w + 1e-9 and eh_r <= remaining_h + 1e-9:
                        use_rotated = True
                elif self._can_rotate(rect):
                    ew_r = self._effective_width(rect, rotated=True)
                    eh_r = self._effective_height(rect, rotated=True)
                    if ew_r <= usable_w + 1e-9 and eh_r < eh:
                        use_rotated = True

                actual_ew = self._effective_width(rect, use_rotated)
                actual_eh = self._effective_height(rect, use_rotated)

                if actual_ew <= usable_w + 1e-9 and actual_eh <= remaining_h + 1e-9:
                    shelf = Shelf(
                        y=current_y,
                        height=actual_eh,
                        bin_width=usable_w + padding,
                        spacing=self.spacing,
                    )
                    p = Placement(
                        rect=rect,
                        x=padding,
                        y=current_y,
                        rotated=use_rotated,
                    )
                    shelf.items.append(p)
                    shelf.used_width = padding + actual_ew
                    shelves.append(shelf)
                    placed.append(p)
                    current_y += actual_eh
                    continue

            rejected.append(rect)

        return placed, rejected

    def _choose_shelf(
        self,
        rect: Rect,
        shelves: List[Shelf],
        usable_w: float,
    ) -> Tuple[Optional[Shelf], bool]:
        """Choose a shelf for the rect. Returns (shelf, rotated) or (None, False)."""
        if not shelves:
            return None, False

        candidates: List[Tuple[Shelf, bool, float]] = []

        for shelf in (shelves if self.choice != ShelfChoice.NEXT_FIT else shelves[-1:]):
            ew = self._effective_width(rect)
            eh = self._effective_height(rect)

            if shelf.can_fit(ew, eh):
                score = self._score_shelf(rect, shelf, False)
                candidates.append((shelf, False, score))

            if self._can_rotate(rect):
                ew_r = self._effective_width(rect, rotated=True)
                eh_r = self._effective_height(rect, rotated=True)
                if shelf.can_fit(ew_r, eh_r):
                    score = self._score_shelf(rect, shelf, True)
                    candidates.append((shelf, True, score))

        if not candidates:
            return None, False

        best = min(candidates, key=lambda c: c[2])
        return best[0], best[1]

    def _score_shelf(self, rect: Rect, shelf: Shelf, rotated: bool) -> float:
        """Score a shelf placement. Lower is better."""
        pw = self._effective_width(rect, rotated)
        ph = self._effective_height(rect, rotated)

        if self.choice == ShelfChoice.NEXT_FIT:
            return 0  # Always use current shelf
        elif self.choice == ShelfChoice.FIRST_FIT:
            return 0  # First that fits
        elif self.choice == ShelfChoice.BEST_WIDTH_FIT:
            return shelf.remaining_width - pw
        elif self.choice == ShelfChoice.BEST_HEIGHT_FIT:
            return abs(shelf.height - ph)
        elif self.choice == ShelfChoice.WORST_WIDTH_FIT:
            return -(shelf.remaining_width - pw)
        return 0
