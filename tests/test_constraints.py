"""Tests for the constraint system."""

import pytest
from tessera.core import Bin, Placement, Rect
from tessera.constraints.spatial import (
    AlignmentConstraint,
    FixedPositionConstraint,
    MarginConstraint,
    MinDistanceConstraint,
    RegionConstraint,
)
from tessera.constraints.grouping import GroupConstraint, GroupProximityConstraint
from tessera.constraints.ratio import AspectRatioConstraint, BinFillConstraint


def make_placement(rid, x, y, w, h, bin_index=0):
    r = Rect(width=w, height=h, rid=rid)
    return Placement(rect=r, x=x, y=y, bin_index=bin_index)


class TestMarginConstraint:
    def test_no_violation(self):
        c = MarginConstraint(inter_rect=5)
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 20, 0, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0

    def test_inter_rect_violation(self):
        c = MarginConstraint(inter_rect=10)
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 12, 0, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_bin_edge_violation(self):
        c = MarginConstraint(bin_edge=5)
        placements = [make_placement("a", 2, 2, 10, 10)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_bin_edge_ok(self):
        c = MarginConstraint(bin_edge=5)
        placements = [make_placement("a", 5, 5, 10, 10)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0

    def test_rect_ids_filter(self):
        c = MarginConstraint(inter_rect=10, rect_ids={"a"})
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 12, 0, 10, 10),
        ]
        # "b" is not in rect_ids, so only "a" is checked against others
        violations = c.evaluate(placements, [Bin(100, 100)])
        # With only "a" filtered, it has no partner to check against
        assert len(violations) == 0

    def test_is_satisfied(self):
        c = MarginConstraint(inter_rect=5)
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 20, 0, 10, 10),
        ]
        assert c.is_satisfied(placements, [Bin(100, 100)])


class TestAlignmentConstraint:
    def test_grid_x_aligned(self):
        c = AlignmentConstraint(grid_x=10)
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 20, 0, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0

    def test_grid_x_misaligned(self):
        c = AlignmentConstraint(grid_x=10)
        placements = [make_placement("a", 3, 0, 10, 10)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_grid_y_misaligned(self):
        c = AlignmentConstraint(grid_y=10)
        placements = [make_placement("a", 0, 7, 10, 10)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_axis_x_aligned(self):
        c = AlignmentConstraint(axis="x")
        placements = [
            make_placement("a", 5, 0, 10, 10),
            make_placement("b", 5, 20, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0

    def test_axis_x_misaligned(self):
        c = AlignmentConstraint(axis="x")
        placements = [
            make_placement("a", 5, 0, 10, 10),
            make_placement("b", 10, 20, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_axis_y_aligned(self):
        c = AlignmentConstraint(axis="y")
        placements = [
            make_placement("a", 0, 10, 10, 10),
            make_placement("b", 20, 10, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0


class TestRegionConstraint:
    def test_within_region(self):
        c = RegionConstraint(x=0, y=0, width=50, height=50, rect_ids={"a"})
        placements = [make_placement("a", 10, 10, 20, 20)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0

    def test_outside_region(self):
        c = RegionConstraint(x=0, y=0, width=50, height=50, rect_ids={"a"})
        placements = [make_placement("a", 40, 40, 20, 20)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_non_matching_rid_ignored(self):
        c = RegionConstraint(x=0, y=0, width=50, height=50, rect_ids={"a"})
        placements = [make_placement("b", 80, 80, 20, 20)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0


class TestFixedPositionConstraint:
    def test_correct_position(self):
        c = FixedPositionConstraint(positions={"a": (10, 20)})
        placements = [make_placement("a", 10, 20, 10, 10)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0

    def test_wrong_position(self):
        c = FixedPositionConstraint(positions={"a": (10, 20)})
        placements = [make_placement("a", 15, 25, 10, 10)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_unmatched_rid_ignored(self):
        c = FixedPositionConstraint(positions={"a": (10, 20)})
        placements = [make_placement("b", 0, 0, 10, 10)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0


class TestMinDistanceConstraint:
    def test_satisfied(self):
        c = MinDistanceConstraint(pairs=[("a", "b", 5)])
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 20, 0, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0

    def test_violated(self):
        c = MinDistanceConstraint(pairs=[("a", "b", 15)])
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 12, 0, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_missing_rect(self):
        c = MinDistanceConstraint(pairs=[("a", "c", 5)])
        placements = [make_placement("a", 0, 0, 10, 10)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0


class TestGroupConstraint:
    def test_same_bin_ok(self):
        c = GroupConstraint(groups={"g1": {"a", "b"}})
        placements = [
            make_placement("a", 0, 0, 10, 10, bin_index=0),
            make_placement("b", 20, 0, 10, 10, bin_index=0),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0

    def test_different_bin_violation(self):
        c = GroupConstraint(groups={"g1": {"a", "b"}})
        placements = [
            make_placement("a", 0, 0, 10, 10, bin_index=0),
            make_placement("b", 0, 0, 10, 10, bin_index=1),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_max_gap_ok(self):
        c = GroupConstraint(groups={"g1": {"a", "b"}}, max_gap=15)
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 20, 0, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0

    def test_max_gap_violation(self):
        c = GroupConstraint(groups={"g1": {"a", "b"}}, max_gap=5)
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 50, 0, 10, 10),
        ]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 1

    def test_single_member_no_violation(self):
        c = GroupConstraint(groups={"g1": {"a", "b"}})
        placements = [make_placement("a", 0, 0, 10, 10)]
        violations = c.evaluate(placements, [Bin(100, 100)])
        assert len(violations) == 0


class TestGroupProximityConstraint:
    def test_close_together(self):
        c = GroupProximityConstraint(groups={"g1": {"a", "b"}})
        placements = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 12, 0, 10, 10),
        ]
        penalty = c.penalty(placements, [Bin(100, 100)])
        assert penalty >= 0

    def test_far_apart_higher_penalty(self):
        c = GroupProximityConstraint(groups={"g1": {"a", "b"}})
        close = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 12, 0, 10, 10),
        ]
        far = [
            make_placement("a", 0, 0, 10, 10),
            make_placement("b", 80, 80, 10, 10),
        ]
        bins = [Bin(100, 100)]
        assert c.penalty(far, bins) > c.penalty(close, bins)


class TestAspectRatioConstraint:
    def test_square_ok(self):
        c = AspectRatioConstraint(target_ratio=1.0, tolerance=0.1)
        placements = [
            make_placement("a", 0, 0, 50, 50),
            make_placement("b", 0, 50, 50, 50),
        ]
        # Bounding box is 50x100, ratio 0.5 -- not square either
        # Use placements that form a square bounding box
        placements = [
            make_placement("a", 0, 0, 50, 50),
            make_placement("b", 50, 50, 50, 50),
        ]
        # BB = 100x100, ratio = 1.0
        violations = c.evaluate(placements, [Bin(200, 200)])
        assert len(violations) == 0

    def test_wide_violation(self):
        c = AspectRatioConstraint(target_ratio=1.0, tolerance=0.1)
        placements = [
            make_placement("a", 0, 0, 100, 10),
            make_placement("b", 0, 10, 100, 10),
        ]
        violations = c.evaluate(placements, [Bin(200, 200)])
        assert len(violations) == 1


class TestBinFillConstraint:
    def test_good_fill(self):
        c = BinFillConstraint(min_fill=0.5)
        placements = [make_placement("a", 0, 0, 80, 80)]
        bins = [Bin(100, 100)]
        violations = c.evaluate(placements, bins)
        assert len(violations) == 0

    def test_low_fill(self):
        c = BinFillConstraint(min_fill=0.5)
        placements = [make_placement("a", 0, 0, 10, 10)]
        bins = [Bin(100, 100)]
        violations = c.evaluate(placements, bins)
        assert len(violations) == 1
