"""
SVG renderer for packing results.

Generates publication-quality SVG images of bin packing layouts with
colors, labels, dimensions, and a legend.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

from tessera.core import Bin, PackingResult, Placement


# Color palette inspired by seed numbers
_PALETTE = [
    "#4B8A3E",  # 4823 -> forest green
    "#1E6FA1",  # 1619 -> ocean blue
    "#C44536",  # 4365 -> brick red
    "#6B52A3",  # 6527 -> purple
    "#D4A03E",  # 3520 -> gold
    "#56A65E",  # 5646 -> spring green
    "#3298B5",  # 3219 -> teal
    "#9B5FA3",  # 3798 -> lavender
    "#E87F4F",  # 9818 -> coral
    "#2E8B6E",  # 6971 -> sea green
    "#5264A4",  # 5244 -> steel blue
    "#A13D6B",  # 8161 -> rose
    "#C97B2E",  # 9980 -> amber
    "#4E9E84",  # 9584 -> jade
    "#7B4FA0",  # 1582 -> violet
    "#6E9343",  # 6563 -> olive
]


class SvgRenderer:
    """
    Generates SVG visualizations of packing results.

    Features:
    - Color-coded rectangles with labels
    - Dimension annotations
    - Free space visualization
    - Legend with rect details
    - Hover tooltips
    """

    def __init__(
        self,
        scale: float = 1.0,
        padding: int = 40,
        show_labels: bool = True,
        show_dimensions: bool = False,
        show_legend: bool = True,
        show_grid: bool = False,
        grid_spacing: float = 10.0,
        font_size: int = 11,
        rect_opacity: float = 0.85,
        colors: Optional[List[str]] = None,
    ):
        self.scale = scale
        self.padding = padding
        self.show_labels = show_labels
        self.show_dimensions = show_dimensions
        self.show_legend = show_legend
        self.show_grid = show_grid
        self.grid_spacing = grid_spacing
        self.font_size = font_size
        self.rect_opacity = rect_opacity
        self.colors = colors or _PALETTE

    def render(
        self,
        result: PackingResult,
        bins: List[Bin],
        bin_index: int = 0,
    ) -> str:
        """Render a single bin as SVG."""
        if bin_index >= len(bins):
            return "<svg></svg>"

        bin_obj = bins[bin_index]
        placements = result.placements_in_bin(bin_index)
        colors = self._assign_colors(placements)

        # Calculate SVG dimensions
        legend_width = 250 if self.show_legend else 0
        svg_w = bin_obj.width * self.scale + 2 * self.padding + legend_width
        svg_h = bin_obj.height * self.scale + 2 * self.padding + 30
        eff = result.bin_efficiency(bin_index, bin_obj)

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_w}" height="{svg_h}" '
            f'viewBox="0 0 {svg_w} {svg_h}">',
            '<defs>',
            '  <style>',
            f'    text {{ font-family: monospace; font-size: {self.font_size}px; }}',
            '    .label {{ text-anchor: middle; dominant-baseline: central; fill: white; font-weight: bold; }}',
            '    .dim {{ text-anchor: middle; dominant-baseline: central; fill: #333; font-size: 9px; }}',
            '    .legend {{ font-size: 10px; fill: #333; }}',
            '    .title {{ font-size: 14px; font-weight: bold; fill: #333; }}',
            '  </style>',
            '</defs>',
            '',
            f'<!-- Bin {bin_index}: {bin_obj.width}x{bin_obj.height}, efficiency: {eff:.1%} -->',
            '',
            # Background
            f'<rect x="{self.padding}" y="{self.padding}" '
            f'width="{bin_obj.width * self.scale}" '
            f'height="{bin_obj.height * self.scale}" '
            f'fill="#f5f5f5" stroke="#999" stroke-width="2"/>',
        ]

        # Grid
        if self.show_grid:
            parts.append(self._render_grid(bin_obj))

        # Placements
        for p in placements:
            parts.append(self._render_placement(p, colors, bin_obj))

        # Title
        parts.append(
            f'<text x="{self.padding}" y="{self.padding - 10}" class="title">'
            f'Bin {bin_index} ({bin_obj.width}x{bin_obj.height}) — '
            f'{len(placements)} rects, {eff:.1%} efficient</text>'
        )

        # Legend
        if self.show_legend:
            parts.append(self._render_legend(
                placements, colors, bin_obj
            ))

        parts.append('</svg>')
        return '\n'.join(parts)

    def render_all_bins(
        self,
        result: PackingResult,
        bins: List[Bin],
    ) -> str:
        """Render all bins as a single SVG with stacked bins."""
        total_height = 0
        bin_svgs = []

        for i in range(result.bins_used):
            if i < len(bins):
                svg = self.render(result, bins, i)
                bin_svgs.append((svg, total_height))
                total_height += bins[i].height * self.scale + 2 * self.padding + 50

        if not bin_svgs:
            return "<svg></svg>"

        max_width = max(
            bins[i].width * self.scale + 2 * self.padding + 300
            for i in range(min(result.bins_used, len(bins)))
        )

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{max_width}" height="{total_height}">',
        ]

        for svg_content, y_offset in bin_svgs:
            # Extract inner content (strip svg wrapper)
            inner = svg_content
            inner = inner.split('>', 1)[1] if '>' in inner else inner
            inner = inner.rsplit('</svg>', 1)[0] if '</svg>' in inner else inner
            parts.append(f'<g transform="translate(0,{y_offset})">')
            parts.append(inner)
            parts.append('</g>')

        parts.append('</svg>')
        return '\n'.join(parts)

    def _render_placement(
        self,
        p: Placement,
        colors: Dict[str, str],
        bin_obj: Bin,
    ) -> str:
        """Render a single placement rectangle."""
        x = self.padding + p.x * self.scale
        y = self.padding + p.y * self.scale
        w = p.placed_width * self.scale
        h = p.placed_height * self.scale
        color = colors.get(p.rect.rid, "#888")

        label = p.rect.label or p.rect.rid[:6]
        rot_info = " (R)" if p.rotated else ""

        parts = [
            f'<g>',
            f'  <title>{label}: {p.placed_width}x{p.placed_height} at ({p.x},{p.y}){rot_info}</title>',
            f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{color}" opacity="{self.rect_opacity}" '
            f'stroke="#333" stroke-width="1"/>',
        ]

        if self.show_labels and w > 20 and h > 14:
            cx = x + w / 2
            cy = y + h / 2
            display_label = label[:8] if len(label) > 8 else label
            parts.append(
                f'  <text x="{cx}" y="{cy}" class="label">{display_label}</text>'
            )

        if self.show_dimensions and w > 35 and h > 25:
            cx = x + w / 2
            parts.append(
                f'  <text x="{cx}" y="{y + h - 4}" class="dim">'
                f'{p.placed_width}x{p.placed_height}</text>'
            )

        parts.append('</g>')
        return '\n'.join(parts)

    def _render_grid(self, bin_obj: Bin) -> str:
        """Render a grid overlay."""
        parts = ['<g opacity="0.15" stroke="#666" stroke-width="0.5">']

        x_start = self.padding
        y_start = self.padding
        x_end = self.padding + bin_obj.width * self.scale
        y_end = self.padding + bin_obj.height * self.scale

        x = x_start
        while x <= x_end:
            parts.append(f'  <line x1="{x}" y1="{y_start}" x2="{x}" y2="{y_end}"/>')
            x += self.grid_spacing * self.scale

        y = y_start
        while y <= y_end:
            parts.append(f'  <line x1="{x_start}" y1="{y}" x2="{x_end}" y2="{y}"/>')
            y += self.grid_spacing * self.scale

        parts.append('</g>')
        return '\n'.join(parts)

    def _render_legend(
        self,
        placements: List[Placement],
        colors: Dict[str, str],
        bin_obj: Bin,
    ) -> str:
        """Render a legend of all placed rects."""
        x_offset = self.padding + bin_obj.width * self.scale + 20
        y_offset = self.padding + 5

        parts = [
            f'<text x="{x_offset}" y="{y_offset}" class="title">Legend</text>',
        ]

        for i, p in enumerate(placements[:30]):  # Limit legend entries
            y = y_offset + 20 + i * 18
            color = colors.get(p.rect.rid, "#888")
            label = p.rect.label or p.rect.rid[:8]
            rot = "R" if p.rotated else ""

            parts.append(
                f'<rect x="{x_offset}" y="{y - 8}" width="12" height="12" '
                f'fill="{color}" opacity="{self.rect_opacity}" stroke="#333" stroke-width="0.5"/>'
            )
            parts.append(
                f'<text x="{x_offset + 16}" y="{y + 2}" class="legend">'
                f'{label} {p.placed_width}x{p.placed_height} {rot}</text>'
            )

        if len(placements) > 30:
            y = y_offset + 20 + 30 * 18
            parts.append(
                f'<text x="{x_offset}" y="{y}" class="legend">'
                f'... and {len(placements) - 30} more</text>'
            )

        return '\n'.join(parts)

    def _assign_colors(self, placements: List[Placement]) -> Dict[str, str]:
        """Assign colors to placements."""
        colors = {}
        for i, p in enumerate(placements):
            if p.rect.color:
                colors[p.rect.rid] = p.rect.color
            elif p.rect.group:
                # Same group = same color
                group_hash = int(hashlib.md5(p.rect.group.encode()).hexdigest()[:8], 16)
                colors[p.rect.rid] = self.colors[group_hash % len(self.colors)]
            else:
                colors[p.rect.rid] = self.colors[i % len(self.colors)]
        return colors
