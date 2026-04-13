"""
ASCII art renderer for packing results.

Renders bin contents as text grids for terminal display.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from tessera.core import Bin, PackingResult, Placement


class AsciiRenderer:
    """
    Renders packing results as ASCII art.

    Each cell represents a configurable number of units. Rects are drawn
    with their first two label/rid characters for identification.
    """

    def __init__(
        self,
        cell_width: float = 1.0,
        cell_height: float = 1.0,
        max_cols: int = 120,
        max_rows: int = 60,
        empty_char: str = ".",
        border_char: str = "#",
    ):
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.max_cols = max_cols
        self.max_rows = max_rows
        self.empty_char = empty_char
        self.border_char = border_char

    def render(
        self,
        result: PackingResult,
        bins: List[Bin],
        bin_index: int = 0,
    ) -> str:
        """Render a single bin's contents as ASCII art."""
        if bin_index >= len(bins):
            return "(no bin to render)"

        bin_obj = bins[bin_index]
        placements = result.placements_in_bin(bin_index)

        # Calculate grid dimensions
        cols = min(int(bin_obj.width / self.cell_width), self.max_cols)
        rows = min(int(bin_obj.height / self.cell_height), self.max_rows)

        if cols <= 0 or rows <= 0:
            return "(bin too small to render)"

        # Build character grid
        grid = [[self.empty_char for _ in range(cols)] for _ in range(rows)]

        # Assign characters to rects
        chars = self._assign_chars(placements)

        # Draw placements
        for p in placements:
            ch = chars.get(p.rect.rid, "?")
            x1 = int(p.x / self.cell_width)
            y1 = int(p.y / self.cell_height)
            x2 = int(p.right / self.cell_width)
            y2 = int(p.bottom / self.cell_height)

            for r in range(max(0, y1), min(rows, y2)):
                for c in range(max(0, x1), min(cols, x2)):
                    grid[r][c] = ch

        # Build output
        lines = []
        # Top border
        lines.append(self.border_char * (cols + 2))
        for row in grid:
            lines.append(self.border_char + "".join(row) + self.border_char)
        # Bottom border
        lines.append(self.border_char * (cols + 2))

        # Legend
        lines.append("")
        lines.append(f"Bin {bin_index}: {bin_obj.width}x{bin_obj.height}")
        lines.append(f"Placements: {len(placements)}")
        eff = result.bin_efficiency(bin_index, bin_obj)
        lines.append(f"Efficiency: {eff:.1%}")
        lines.append("")
        lines.append("Legend:")
        for p in placements:
            ch = chars.get(p.rect.rid, "?")
            label = p.rect.label or p.rect.rid[:8]
            rot = " (rotated)" if p.rotated else ""
            lines.append(
                f"  {ch} = {label} ({p.placed_width}x{p.placed_height}"
                f" at {p.x},{p.y}){rot}"
            )

        return "\n".join(lines)

    def render_all_bins(
        self,
        result: PackingResult,
        bins: List[Bin],
    ) -> str:
        """Render all bins."""
        parts = []
        for i in range(result.bins_used):
            if i < len(bins):
                parts.append(self.render(result, bins, i))
                parts.append("")
        return "\n".join(parts)

    def _assign_chars(self, placements: List[Placement]) -> Dict[str, str]:
        """Assign a unique character to each placement."""
        chars = {}
        available = (
            list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            + list("abcdefghijklmnopqrstuvwxyz")
            + list("0123456789")
            + list("@$%&*+=~")
        )

        for i, p in enumerate(placements):
            if i < len(available):
                chars[p.rect.rid] = available[i]
            else:
                chars[p.rect.rid] = "?"

        return chars

    def render_compact(
        self,
        result: PackingResult,
        bins: List[Bin],
        bin_index: int = 0,
    ) -> str:
        """Render a compact summary line for a bin."""
        if bin_index >= len(bins):
            return ""

        bin_obj = bins[bin_index]
        placements = result.placements_in_bin(bin_index)
        eff = result.bin_efficiency(bin_index, bin_obj)

        return (
            f"Bin {bin_index} [{bin_obj.width}x{bin_obj.height}]: "
            f"{len(placements)} rects, {eff:.1%} efficiency"
        )
