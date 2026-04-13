"""Tests for core data structures."""

import math
import pytest
from tessera.core import (
    Bin, FreeSpace, PackingProblem, PackingResult, Placement, Point,
    Rect, RotationPolicy, SortStrategy, sort_rects,
)


class TestPoint:
    def test_creation(self):
        p = Point(3.0, 4.0)
        assert p.x == 3.0
        assert p.y == 4.0

    def test_distance(self):
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        assert math.isclose(p1.distance_to(p2), 5.0)

    def test_add(self):
        p = Point(1, 2) + Point(3, 4)
        assert p.x == 4 and p.y == 6

    def test_sub(self):
        p = Point(5, 7) - Point(2, 3)
        assert p.x == 3 and p.y == 4

    def test_iter(self):
        x, y = Point(10, 20)
        assert x == 10 and y == 20

    def test_hash(self):
        s = {Point(1, 2), Point(1, 2), Point(3, 4)}
        assert len(s) == 2


class TestRect:
    def test_creation(self):
        r = Rect(width=10, height=20)
        assert r.width == 10
        assert r.height == 20
        assert r.rid  # auto-generated

    def test_invalid_dimensions(self):
        with pytest.raises(ValueError):
            Rect(width=0, height=10)
        with pytest.raises(ValueError):
            Rect(width=10, height=-1)

    def test_area(self):
        r = Rect(width=10, height=20)
        assert r.area == 200

    def test_perimeter(self):
        r = Rect(width=10, height=20)
        assert r.perimeter == 60

    def test_aspect_ratio(self):
        r = Rect(width=10, height=20)
        assert r.aspect_ratio == 2.0

    def test_aspect_ratio_inverse(self):
        r = Rect(width=20, height=10)
        assert r.aspect_ratio == 2.0

    def test_max_min_side(self):
        r = Rect(width=10, height=30)
        assert r.max_side == 30
        assert r.min_side == 10

    def test_is_square(self):
        assert Rect(width=10, height=10).is_square
        assert not Rect(width=10, height=11).is_square

    def test_rotated(self):
        r = Rect(width=10, height=20, rid="test", label="T")
        rot = r.rotated()
        assert rot.width == 20
        assert rot.height == 10
        assert rot.rid == "test"
        assert rot.label == "T"

    def test_fits_in(self):
        r = Rect(width=10, height=20)
        assert r.fits_in(10, 20)
        assert r.fits_in(15, 25)
        assert not r.fits_in(9, 20)
        assert not r.fits_in(10, 19)

    def test_rotated_fits_in(self):
        r = Rect(width=10, height=20)
        assert r.rotated_fits_in(20, 10)
        assert not r.rotated_fits_in(19, 10)

    def test_custom_rid(self):
        r = Rect(width=10, height=10, rid="custom_id")
        assert r.rid == "custom_id"

    def test_metadata(self):
        r = Rect(width=10, height=10, metadata={"texture": "stone"})
        assert r.metadata["texture"] == "stone"

    def test_repr(self):
        r = Rect(width=10, height=20, label="Test")
        s = repr(r)
        assert "10" in s
        assert "20" in s
        assert "Test" in s


class TestPlacement:
    def test_creation(self):
        r = Rect(width=10, height=20)
        p = Placement(rect=r, x=5, y=10)
        assert p.placed_width == 10
        assert p.placed_height == 20

    def test_rotated_placement(self):
        r = Rect(width=10, height=20)
        p = Placement(rect=r, x=0, y=0, rotated=True)
        assert p.placed_width == 20
        assert p.placed_height == 10

    def test_right_bottom(self):
        r = Rect(width=10, height=20)
        p = Placement(rect=r, x=5, y=10)
        assert p.right == 15
        assert p.bottom == 30

    def test_center(self):
        r = Rect(width=10, height=20)
        p = Placement(rect=r, x=0, y=0)
        c = p.center
        assert c.x == 5
        assert c.y == 10

    def test_area(self):
        r = Rect(width=10, height=20)
        p = Placement(rect=r, x=0, y=0)
        assert p.area == 200

    def test_corners(self):
        r = Rect(width=10, height=20)
        p = Placement(rect=r, x=5, y=10)
        tl, tr, br, bl = p.corners
        assert tl.x == 5 and tl.y == 10
        assert tr.x == 15 and tr.y == 10
        assert br.x == 15 and br.y == 30
        assert bl.x == 5 and bl.y == 30

    def test_overlaps(self):
        r1 = Rect(width=10, height=10, rid="a")
        r2 = Rect(width=10, height=10, rid="b")
        p1 = Placement(rect=r1, x=0, y=0)
        p2 = Placement(rect=r2, x=5, y=5)
        assert p1.overlaps(p2)

    def test_no_overlap_right(self):
        r1 = Rect(width=10, height=10, rid="a")
        r2 = Rect(width=10, height=10, rid="b")
        p1 = Placement(rect=r1, x=0, y=0)
        p2 = Placement(rect=r2, x=10, y=0)
        assert not p1.overlaps(p2)

    def test_no_overlap_below(self):
        r1 = Rect(width=10, height=10, rid="a")
        r2 = Rect(width=10, height=10, rid="b")
        p1 = Placement(rect=r1, x=0, y=0)
        p2 = Placement(rect=r2, x=0, y=10)
        assert not p1.overlaps(p2)

    def test_overlap_area(self):
        r1 = Rect(width=10, height=10, rid="a")
        r2 = Rect(width=10, height=10, rid="b")
        p1 = Placement(rect=r1, x=0, y=0)
        p2 = Placement(rect=r2, x=5, y=5)
        assert p1.overlap_area(p2) == 25

    def test_contains_point(self):
        r = Rect(width=10, height=10)
        p = Placement(rect=r, x=5, y=5)
        assert p.contains_point(Point(10, 10))
        assert not p.contains_point(Point(4, 10))

    def test_distance_to(self):
        r1 = Rect(width=10, height=10, rid="a")
        r2 = Rect(width=10, height=10, rid="b")
        p1 = Placement(rect=r1, x=0, y=0)
        p2 = Placement(rect=r2, x=20, y=0)
        assert math.isclose(p1.distance_to(p2), 10.0)

    def test_distance_to_overlapping(self):
        r1 = Rect(width=10, height=10, rid="a")
        r2 = Rect(width=10, height=10, rid="b")
        p1 = Placement(rect=r1, x=0, y=0)
        p2 = Placement(rect=r2, x=5, y=5)
        assert p1.distance_to(p2) == 0


class TestFreeSpace:
    def test_area(self):
        fs = FreeSpace(0, 0, 100, 200)
        assert fs.area == 20000

    def test_can_fit(self):
        fs = FreeSpace(0, 0, 100, 200)
        assert fs.can_fit(100, 200)
        assert fs.can_fit(50, 50)
        assert not fs.can_fit(101, 200)

    def test_overlaps_rect(self):
        fs = FreeSpace(0, 0, 100, 100)
        assert fs.overlaps_rect(50, 50, 100, 100)
        assert not fs.overlaps_rect(100, 0, 50, 50)


class TestBin:
    def test_creation(self):
        b = Bin(width=100, height=200)
        assert b.width == 100
        assert b.height == 200

    def test_invalid(self):
        with pytest.raises(ValueError):
            Bin(width=0, height=100)

    def test_area(self):
        b = Bin(width=100, height=200)
        assert b.area == 20000

    def test_padding(self):
        b = Bin(width=100, height=200, padding=10)
        assert b.usable_width == 80
        assert b.usable_height == 180
        assert b.usable_area == 80 * 180


class TestPackingResult:
    def _make_result(self):
        r1 = Rect(width=10, height=10, rid="a")
        r2 = Rect(width=20, height=20, rid="b")
        r3 = Rect(width=5, height=5, rid="c")
        p1 = Placement(rect=r1, x=0, y=0, bin_index=0)
        p2 = Placement(rect=r2, x=10, y=0, bin_index=0)
        result = PackingResult(
            placements=[p1, p2],
            rejected=[r3],
            bins_used=1,
            algorithm="test",
        )
        return result

    def test_counts(self):
        r = self._make_result()
        assert r.total_placed == 2
        assert r.total_rejected == 1

    def test_placed_area(self):
        r = self._make_result()
        assert r.placed_area == 100 + 400

    def test_all_placed(self):
        r = self._make_result()
        assert not r.all_placed

    def test_efficiency(self):
        r = self._make_result()
        bins = [Bin(width=100, height=100)]
        eff = r.efficiency(bins)
        assert math.isclose(eff, 500 / 10000)

    def test_bounding_box(self):
        r = self._make_result()
        bb = r.bounding_box(0)
        assert bb == (30, 20)

    def test_has_overlaps_false(self):
        r = self._make_result()
        assert not r.has_overlaps()

    def test_has_overlaps_true(self):
        r1 = Rect(width=10, height=10, rid="x")
        r2 = Rect(width=10, height=10, rid="y")
        result = PackingResult(
            placements=[
                Placement(rect=r1, x=0, y=0),
                Placement(rect=r2, x=5, y=5),
            ],
            bins_used=1,
        )
        assert result.has_overlaps()

    def test_summary(self):
        r = self._make_result()
        s = r.summary()
        assert "Placed: 2" in s
        assert "Rejected: 1" in s

    def test_placements_in_bin(self):
        r = self._make_result()
        assert len(r.placements_in_bin(0)) == 2
        assert len(r.placements_in_bin(1)) == 0

    def test_merge(self):
        r1 = self._make_result()
        r2 = PackingResult(
            placements=[Placement(rect=Rect(5, 5, rid="d"), x=0, y=0, bin_index=0)],
            bins_used=1,
        )
        merged = r1.merge(r2, bin_offset=1)
        assert merged.total_placed == 3


class TestPackingProblem:
    def test_add_rect(self):
        p = PackingProblem()
        r = p.add_rect(10, 20, label="test")
        assert len(p.rects) == 1
        assert r.width == 10

    def test_add_bin(self):
        p = PackingProblem()
        b = p.add_bin(100, 200)
        assert len(p.bins) == 1
        assert b.width == 100

    def test_total_areas(self):
        p = PackingProblem()
        p.add_rect(10, 10)
        p.add_rect(20, 20)
        p.add_bin(100, 100)
        assert p.total_rect_area == 500
        assert p.total_bin_area == 10000

    def test_theoretical_min_bins(self):
        p = PackingProblem()
        for _ in range(10):
            p.add_rect(10, 10)
        p.add_bin(100, 100)
        assert p.theoretical_min_bins == 1

    def test_validate_empty(self):
        p = PackingProblem()
        issues = p.validate()
        assert any("No rectangles" in i for i in issues)

    def test_validate_no_bins(self):
        p = PackingProblem()
        p.add_rect(10, 10)
        issues = p.validate()
        assert any("No bins" in i for i in issues)

    def test_validate_rect_too_large(self):
        p = PackingProblem()
        p.add_rect(200, 200)
        p.add_bin(100, 100)
        issues = p.validate()
        assert any("doesn't fit" in i for i in issues)

    def test_sorted_rects_area(self):
        p = PackingProblem(sort_strategy=SortStrategy.AREA_DESC)
        p.add_rect(5, 5, label="small")
        p.add_rect(20, 20, label="big")
        p.add_rect(10, 10, label="medium")
        sorted_r = p.sorted_rects()
        assert sorted_r[0].label == "big"
        assert sorted_r[2].label == "small"

    def test_sorted_rects_priority(self):
        p = PackingProblem(sort_strategy=SortStrategy.AREA_DESC)
        p.add_rect(5, 5, label="small_high", priority=10)
        p.add_rect(20, 20, label="big_low", priority=0)
        sorted_r = p.sorted_rects()
        assert sorted_r[0].label == "small_high"

    def test_sort_none(self):
        p = PackingProblem(sort_strategy=SortStrategy.NONE)
        p.add_rect(5, 5, label="a")
        p.add_rect(20, 20, label="b")
        sorted_r = p.sorted_rects()
        assert sorted_r[0].label == "a"


class TestSortRects:
    def test_area_desc(self):
        rects = [Rect(5, 5), Rect(20, 20), Rect(10, 10)]
        sorted_r = sort_rects(rects, SortStrategy.AREA_DESC)
        assert sorted_r[0].area == 400
        assert sorted_r[2].area == 25

    def test_width_desc(self):
        rects = [Rect(5, 100), Rect(20, 1), Rect(10, 50)]
        sorted_r = sort_rects(rects, SortStrategy.WIDTH_DESC)
        assert sorted_r[0].width == 20

    def test_height_desc(self):
        rects = [Rect(5, 100), Rect(20, 1), Rect(10, 50)]
        sorted_r = sort_rects(rects, SortStrategy.HEIGHT_DESC)
        assert sorted_r[0].height == 100

    def test_none(self):
        rects = [Rect(5, 5, rid="a"), Rect(20, 20, rid="b")]
        sorted_r = sort_rects(rects, SortStrategy.NONE)
        assert sorted_r[0].rid == "a"
