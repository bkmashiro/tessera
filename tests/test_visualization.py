"""Tests for visualization module."""

import pytest
from tessera.core import Bin, PackingResult, Placement, Rect
from tessera.visualization.ascii_renderer import AsciiRenderer
from tessera.visualization.svg_renderer import SvgRenderer
from tessera.visualization.stats import PackingStats


def make_result():
    r1 = Rect(width=30, height=30, rid="aaa", label="Alpha")
    r2 = Rect(width=20, height=30, rid="bbb", label="Beta")
    r3 = Rect(width=50, height=20, rid="ccc", label="Gamma")
    return PackingResult(
        placements=[
            Placement(rect=r1, x=0, y=0, bin_index=0),
            Placement(rect=r2, x=30, y=0, bin_index=0),
            Placement(rect=r3, x=0, y=30, bin_index=0),
        ],
        bins_used=1,
        algorithm="test",
        elapsed_ms=5.0,
    )


class TestAsciiRenderer:
    def test_render(self):
        renderer = AsciiRenderer(cell_width=10, cell_height=10)
        result = make_result()
        bins = [Bin(100, 100)]
        output = renderer.render(result, bins, 0)
        assert "Bin 0" in output
        assert "Alpha" in output

    def test_empty_result(self):
        renderer = AsciiRenderer()
        result = PackingResult(bins_used=1, algorithm="test")
        bins = [Bin(50, 50)]
        output = renderer.render(result, bins, 0)
        assert "0" in output

    def test_legend(self):
        renderer = AsciiRenderer(cell_width=10, cell_height=10)
        result = make_result()
        bins = [Bin(100, 100)]
        output = renderer.render(result, bins, 0)
        assert "Legend:" in output
        assert "Alpha" in output
        assert "Beta" in output

    def test_render_all_bins(self):
        renderer = AsciiRenderer(cell_width=10, cell_height=10)
        result = make_result()
        bins = [Bin(100, 100)]
        output = renderer.render_all_bins(result, bins)
        assert "Bin 0" in output

    def test_compact(self):
        renderer = AsciiRenderer()
        result = make_result()
        bins = [Bin(100, 100)]
        output = renderer.render_compact(result, bins, 0)
        assert "3 rects" in output

    def test_invalid_bin_index(self):
        renderer = AsciiRenderer()
        result = make_result()
        output = renderer.render(result, [Bin(100, 100)], 5)
        assert "no bin" in output


class TestSvgRenderer:
    def test_render(self):
        renderer = SvgRenderer()
        result = make_result()
        bins = [Bin(100, 100)]
        svg = renderer.render(result, bins, 0)
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "rect" in svg

    def test_render_with_labels(self):
        renderer = SvgRenderer(show_labels=True, scale=2.0)
        result = make_result()
        bins = [Bin(100, 100)]
        svg = renderer.render(result, bins, 0)
        assert "Alpha" in svg

    def test_render_with_dimensions(self):
        renderer = SvgRenderer(show_dimensions=True, scale=2.0)
        result = make_result()
        bins = [Bin(100, 100)]
        svg = renderer.render(result, bins, 0)
        assert "30x30" in svg or "dim" in svg

    def test_render_with_grid(self):
        renderer = SvgRenderer(show_grid=True)
        result = make_result()
        bins = [Bin(100, 100)]
        svg = renderer.render(result, bins, 0)
        assert "line" in svg

    def test_render_all_bins(self):
        renderer = SvgRenderer()
        result = make_result()
        bins = [Bin(100, 100)]
        svg = renderer.render_all_bins(result, bins)
        assert "<svg" in svg

    def test_empty_result(self):
        renderer = SvgRenderer()
        result = PackingResult(bins_used=1)
        bins = [Bin(100, 100)]
        svg = renderer.render(result, bins, 0)
        assert "<svg" in svg

    def test_custom_colors(self):
        renderer = SvgRenderer(colors=["#FF0000", "#00FF00"])
        result = make_result()
        bins = [Bin(100, 100)]
        svg = renderer.render(result, bins, 0)
        assert "#FF0000" in svg or "#00FF00" in svg

    def test_no_legend(self):
        renderer = SvgRenderer(show_legend=False)
        result = make_result()
        bins = [Bin(100, 100)]
        svg = renderer.render(result, bins, 0)
        assert "Legend" not in svg

    def test_invalid_bin_index(self):
        renderer = SvgRenderer()
        result = make_result()
        svg = renderer.render(result, [Bin(100, 100)], 5)
        assert "<svg>" in svg or "<svg" in svg


class TestPackingStats:
    def test_basic_stats(self):
        result = make_result()
        bins = [Bin(100, 100)]
        stats = PackingStats(result, bins)
        assert stats.total_placed == 3
        assert stats.total_rejected == 0
        assert stats.bins_used == 1

    def test_efficiency(self):
        result = make_result()
        bins = [Bin(100, 100)]
        stats = PackingStats(result, bins)
        eff = stats.overall_efficiency
        assert 0 < eff <= 1

    def test_waste_area(self):
        result = make_result()
        bins = [Bin(100, 100)]
        stats = PackingStats(result, bins)
        assert stats.waste_area > 0

    def test_per_bin_stats(self):
        result = make_result()
        bins = [Bin(100, 100)]
        stats = PackingStats(result, bins)
        bin_stats = stats.per_bin_stats()
        assert len(bin_stats) == 1
        assert bin_stats[0].placed_count == 3

    def test_size_distribution(self):
        result = make_result()
        bins = [Bin(100, 100)]
        stats = PackingStats(result, bins)
        dist = stats.size_distribution()
        total = sum(dist.values())
        assert total == 3

    def test_rotation_stats(self):
        result = make_result()
        bins = [Bin(100, 100)]
        stats = PackingStats(result, bins)
        rot = stats.rotation_stats()
        assert rot["rotated"] == 0
        assert rot["not_rotated"] == 3

    def test_summary(self):
        result = make_result()
        bins = [Bin(100, 100)]
        stats = PackingStats(result, bins)
        summary = stats.summary()
        assert "Placed: 3" in summary
        assert "efficiency" in summary.lower()

    def test_compare(self):
        result1 = make_result()
        result2 = make_result()
        bins = [Bin(100, 100)]
        stats1 = PackingStats(result1, bins)
        stats2 = PackingStats(result2, bins)
        comparison = stats1.compare(stats2)
        assert "Placed" in comparison
        assert "Efficiency" in comparison

    def test_has_overlaps_false(self):
        result = make_result()
        stats = PackingStats(result, [Bin(100, 100)])
        assert not stats.has_overlaps
