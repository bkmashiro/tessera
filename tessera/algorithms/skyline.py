"""
Skyline algorithm for 2D bin packing.

Tracks the "skyline" — the upper contour of placed rectangles. New rectangles
are placed at the lowest point of the skyline. Produces very tight packings
with minimal wasted space, particularly for texture atlas generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

from tessera.core import Bin, Placement, Rect, RotationPolicy
from tessera.algorithms.base import BaseAlgorithm


class SkylineChoice(Enum):
    """How to choose placement position on the skyline."""
    BOTTOM_LEFT = auto()     # Lowest y, then leftmost x
    BEST_FIT = auto()        # Minimize wasted space below the rect
    MIN_WASTE = auto()       # Minimize total waste created


@dataclass
class SkylineNode:
    """A segment of the skyline contour."""
    x: float
    y: float
    width: float

    @property
    def right(self) -> float:
        return self.x + self.width

    def __repr__(self) -> str:
        return f"SkyNode({self.x}-{self.right}, y={self.y})"


class SkylineAlgorithm(BaseAlgorithm):
    """
    Skyline bottom-left packing algorithm.

    Maintains a skyline representing the top edge of placed rectangles.
    New rectangles are placed at the lowest point of the skyline, with
    various heuristics for tie-breaking.
    """

    name = "skyline"

    def __init__(
        self,
        choice: SkylineChoice = SkylineChoice.BOTTOM_LEFT,
        rotation: RotationPolicy = RotationPolicy.NONE,
        spacing: float = 0.0,
    ):
        super().__init__(rotation=rotation, spacing=spacing)
        self.choice = choice
        self._skyline: List[SkylineNode] = []

    def pack_into_bin(
        self,
        rects: List[Rect],
        bin_obj: Bin,
    ) -> Tuple[List[Placement], List[Rect]]:
        # Initialize skyline as a single segment at the bottom
        self._skyline = [SkylineNode(
            x=bin_obj.padding,
            y=bin_obj.padding,
            width=bin_obj.usable_width,
        )]
        self._bin = bin_obj

        placed = []
        rejected = []

        for rect in rects:
            placement = self._find_best_position(rect, bin_obj)
            if placement is not None:
                self._add_skyline_level(placement, bin_obj)
                placed.append(placement)
            else:
                rejected.append(rect)

        return placed, rejected

    def _find_best_position(
        self,
        rect: Rect,
        bin_obj: Bin,
    ) -> Optional[Placement]:
        """Find the best position on the skyline for a rectangle."""
        best_score = float('inf')
        best_score2 = float('inf')
        best_placement = None

        ew = self._effective_width(rect)
        eh = self._effective_height(rect)

        for i in range(len(self._skyline)):
            result = self._try_skyline_position(i, ew, eh, bin_obj)
            if result is not None:
                y, waste = result
                score, score2 = self._score_position(
                    self._skyline[i].x, y, ew, eh, waste, bin_obj
                )
                if score < best_score or (score == best_score and score2 < best_score2):
                    best_score = score
                    best_score2 = score2
                    best_placement = Placement(
                        rect=rect,
                        x=self._skyline[i].x,
                        y=y,
                        rotated=False,
                    )

        # Try rotated
        if self._can_rotate(rect):
            ew_r = self._effective_width(rect, rotated=True)
            eh_r = self._effective_height(rect, rotated=True)

            for i in range(len(self._skyline)):
                result = self._try_skyline_position(i, ew_r, eh_r, bin_obj)
                if result is not None:
                    y, waste = result
                    score, score2 = self._score_position(
                        self._skyline[i].x, y, ew_r, eh_r, waste, bin_obj
                    )
                    if score < best_score or (score == best_score and score2 < best_score2):
                        best_score = score
                        best_score2 = score2
                        best_placement = Placement(
                            rect=rect,
                            x=self._skyline[i].x,
                            y=y,
                            rotated=True,
                        )

        return best_placement

    def _try_skyline_position(
        self,
        index: int,
        width: float,
        height: float,
        bin_obj: Bin,
    ) -> Optional[Tuple[float, float]]:
        """
        Try placing a rect of given size starting at skyline node `index`.

        Returns (y_position, waste_area) or None if it doesn't fit.
        """
        x = self._skyline[index].x
        max_x = bin_obj.width - bin_obj.padding

        if x + width > max_x + 1e-9:
            return None

        # Find the maximum y across all skyline segments this rect would span
        y = 0.0
        waste = 0.0
        remaining_width = width
        i = index

        while remaining_width > 1e-9 and i < len(self._skyline):
            node = self._skyline[i]
            y = max(y, node.y)

            # Check vertical fit
            if y + height > bin_obj.height - bin_obj.padding + 1e-9:
                return None

            segment_width = min(remaining_width, node.width if i == index
                              else node.width)
            if i > index:
                segment_width = min(remaining_width, node.right - max(node.x, x))

            remaining_width -= segment_width
            i += 1

        if remaining_width > 1e-9:
            return None

        # Calculate waste (space between skyline and placed rect bottom)
        remaining_width = width
        i = index
        while remaining_width > 1e-9 and i < len(self._skyline):
            node = self._skyline[i]
            seg_w = min(remaining_width, node.right - max(node.x, x + width - remaining_width))
            if seg_w > 0:
                waste += seg_w * (y - node.y)
            remaining_width -= max(seg_w, 0)
            i += 1

        return (y, waste)

    def _score_position(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        waste: float,
        bin_obj: Bin,
    ) -> Tuple[float, float]:
        """Score a position. Returns (primary_score, secondary_score), lower is better."""
        if self.choice == SkylineChoice.BOTTOM_LEFT:
            return (y + height, x)
        elif self.choice == SkylineChoice.BEST_FIT:
            return (y + height, waste)
        elif self.choice == SkylineChoice.MIN_WASTE:
            return (waste, y + height)
        return (y, x)

    def _add_skyline_level(self, placement: Placement, bin_obj: Bin) -> None:
        """Update the skyline after placing a rectangle."""
        pw = placement.placed_width + self.spacing
        ph = placement.placed_height + self.spacing
        new_y = placement.y + ph

        new_node = SkylineNode(
            x=placement.x,
            y=new_y,
            width=pw,
        )

        # Find which skyline segments are affected
        new_skyline: List[SkylineNode] = []
        i = 0
        inserted = False

        while i < len(self._skyline):
            node = self._skyline[i]

            if not inserted and node.right > placement.x + 1e-9:
                # This node overlaps with the placement

                # Add portion before the placement
                if node.x < placement.x - 1e-9:
                    new_skyline.append(SkylineNode(
                        x=node.x,
                        y=node.y,
                        width=placement.x - node.x,
                    ))

                if not inserted:
                    new_skyline.append(new_node)
                    inserted = True

                # Skip nodes fully covered by the placement
                while i < len(self._skyline) and self._skyline[i].right <= placement.x + pw + 1e-9:
                    i += 1

                # Add portion after the placement
                if i < len(self._skyline):
                    node_after = self._skyline[i]
                    if node_after.x < placement.x + pw - 1e-9:
                        remaining = node_after.right - (placement.x + pw)
                        if remaining > 1e-9:
                            new_skyline.append(SkylineNode(
                                x=placement.x + pw,
                                y=node_after.y,
                                width=remaining,
                            ))
                        i += 1
                continue

            if not inserted or node.x >= placement.x + pw - 1e-9:
                new_skyline.append(node)
            i += 1

        if not inserted:
            new_skyline.append(new_node)

        # Merge adjacent nodes with same y
        self._skyline = self._merge_skyline(new_skyline)

    def _merge_skyline(self, nodes: List[SkylineNode]) -> List[SkylineNode]:
        """Merge adjacent skyline nodes with the same y value."""
        if not nodes:
            return nodes

        merged = [nodes[0]]
        for node in nodes[1:]:
            last = merged[-1]
            if abs(last.y - node.y) < 1e-9 and abs(last.right - node.x) < 1e-9:
                merged[-1] = SkylineNode(
                    x=last.x,
                    y=last.y,
                    width=last.width + node.width,
                )
            else:
                merged.append(node)
        return merged
