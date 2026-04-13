"""Tests for packing algorithms."""

import pytest
from tessera.core import Bin, Rect, RotationPolicy
from tessera.algorithms.maxrects import MaxRectsAlgorithm, MaxRectsHeuristic
from tessera.algorithms.guillotine import (
    GuillotineAlgorithm, GuillotineChoice, GuillotineSplit,
)
from tessera.algorithms.shelf import ShelfAlgorithm, ShelfChoice
from tessera.algorithms.skyline import SkylineAlgorithm, SkylineChoice


# Test fixtures

def make_bin(w=100, h=100):
    return Bin(width=w, height=h)


def make_rects(specs):
    """Create rects from (w, h) tuples."""
    return [Rect(width=w, height=h, label=f"R{i}") for i, (w, h) in enumerate(specs)]


# ===== MaxRects Tests =====

class TestMaxRects:
    def test_single_rect_fits(self):
        algo = MaxRectsAlgorithm()
        rects = make_rects([(50, 50)])
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 1
        assert len(rejected) == 0

    def test_single_rect_too_large(self):
        algo = MaxRectsAlgorithm()
        rects = make_rects([(200, 200)])
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 0
        assert len(rejected) == 1

    def test_exact_fit(self):
        algo = MaxRectsAlgorithm()
        rects = make_rects([(100, 100)])
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 1
        assert placed[0].x == 0 and placed[0].y == 0

    def test_two_rects_side_by_side(self):
        algo = MaxRectsAlgorithm()
        rects = make_rects([(50, 100), (50, 100)])
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2
        assert len(rejected) == 0

    def test_no_overlaps(self):
        algo = MaxRectsAlgorithm()
        rects = make_rects([(30, 30), (30, 30), (30, 30), (30, 30)])
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        for i, p1 in enumerate(placed):
            for p2 in placed[i+1:]:
                assert not p1.overlaps(p2)

    def test_within_bin(self):
        algo = MaxRectsAlgorithm()
        rects = make_rects([(30, 30), (20, 40), (50, 20)])
        b = make_bin()
        placed, _ = algo.pack_into_bin(rects, b)
        for p in placed:
            assert p.x >= 0 and p.y >= 0
            assert p.right <= b.width
            assert p.bottom <= b.height

    def test_bssf_heuristic(self):
        algo = MaxRectsAlgorithm(heuristic=MaxRectsHeuristic.BSSF)
        rects = make_rects([(30, 30), (20, 20), (40, 40)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 3

    def test_blsf_heuristic(self):
        algo = MaxRectsAlgorithm(heuristic=MaxRectsHeuristic.BLSF)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_baf_heuristic(self):
        algo = MaxRectsAlgorithm(heuristic=MaxRectsHeuristic.BAF)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_cp_heuristic(self):
        algo = MaxRectsAlgorithm(heuristic=MaxRectsHeuristic.CP)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_bl_heuristic(self):
        algo = MaxRectsAlgorithm(heuristic=MaxRectsHeuristic.BL)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2
        # BL should place at bottom-left
        assert placed[0].x == 0 and placed[0].y == 0

    def test_with_rotation(self):
        algo = MaxRectsAlgorithm(rotation=RotationPolicy.ORTHOGONAL)
        rects = make_rects([(90, 20)])
        b = Bin(width=30, height=100)
        placed, rejected = algo.pack_into_bin(rects, b)
        # 90x20 doesn't fit, but 20x90 does
        assert len(placed) == 1
        assert placed[0].rotated

    def test_with_spacing(self):
        algo = MaxRectsAlgorithm(spacing=5)
        # Each rect is 45x90, effective 50x95 with spacing, fits in 100x100
        rects = make_rects([(45, 90), (45, 90)])
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_many_small_rects(self):
        algo = MaxRectsAlgorithm()
        rects = make_rects([(10, 10)] * 100)
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 100
        assert len(rejected) == 0

    def test_multi_bin(self):
        algo = MaxRectsAlgorithm()
        # 3 rects of 50x50 each. First bin fits all 4 of 50x50, but let's use
        # larger rects: 70x70 only fits 1 per 100x100 bin
        rects = make_rects([(70, 70), (70, 70), (70, 70)])
        bins = [make_bin(), make_bin(), make_bin()]
        result = algo.pack(rects, bins, multi_bin=True)
        assert result.total_placed == 3
        assert result.bins_used == 3


# ===== Guillotine Tests =====

class TestGuillotine:
    def test_single_rect(self):
        algo = GuillotineAlgorithm()
        rects = make_rects([(50, 50)])
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 1

    def test_two_rects(self):
        algo = GuillotineAlgorithm()
        rects = make_rects([(50, 100), (50, 100)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_no_overlaps(self):
        algo = GuillotineAlgorithm()
        rects = make_rects([(25, 25)] * 16)
        placed, _ = algo.pack_into_bin(rects, make_bin())
        for i, p1 in enumerate(placed):
            for p2 in placed[i+1:]:
                assert not p1.overlaps(p2)

    def test_best_area_fit(self):
        algo = GuillotineAlgorithm(choice=GuillotineChoice.BEST_AREA_FIT)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_best_short_side(self):
        algo = GuillotineAlgorithm(choice=GuillotineChoice.BEST_SHORT_SIDE)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_worst_area_fit(self):
        algo = GuillotineAlgorithm(choice=GuillotineChoice.WORST_AREA_FIT)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_horizontal_split(self):
        algo = GuillotineAlgorithm(split=GuillotineSplit.HORIZONTAL)
        rects = make_rects([(50, 50), (30, 30)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_vertical_split(self):
        algo = GuillotineAlgorithm(split=GuillotineSplit.VERTICAL)
        rects = make_rects([(50, 50), (30, 30)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_min_area_split(self):
        algo = GuillotineAlgorithm(split=GuillotineSplit.MIN_AREA)
        rects = make_rects([(40, 40), (30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 3

    def test_with_merge(self):
        algo = GuillotineAlgorithm(merge=True)
        rects = make_rects([(50, 50), (50, 50)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_without_merge(self):
        algo = GuillotineAlgorithm(merge=False)
        rects = make_rects([(50, 50), (50, 50)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_with_rotation(self):
        algo = GuillotineAlgorithm(rotation=RotationPolicy.ORTHOGONAL)
        rects = make_rects([(90, 20)])
        b = Bin(width=30, height=100)
        placed, _ = algo.pack_into_bin(rects, b)
        assert len(placed) == 1

    def test_reject_too_large(self):
        algo = GuillotineAlgorithm()
        rects = make_rects([(200, 200)])
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(rejected) == 1


# ===== Shelf Tests =====

class TestShelf:
    def test_single_rect(self):
        algo = ShelfAlgorithm()
        rects = make_rects([(50, 50)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 1

    def test_same_height_rects(self):
        algo = ShelfAlgorithm()
        rects = make_rects([(20, 50), (30, 50), (40, 50)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        # Should all fit on one shelf
        assert len(placed) == 3

    def test_next_fit(self):
        algo = ShelfAlgorithm(choice=ShelfChoice.NEXT_FIT)
        rects = make_rects([(30, 30), (30, 30), (30, 30)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 3

    def test_first_fit(self):
        algo = ShelfAlgorithm(choice=ShelfChoice.FIRST_FIT)
        rects = make_rects([(30, 30), (30, 30), (30, 30)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 3

    def test_best_width_fit(self):
        algo = ShelfAlgorithm(choice=ShelfChoice.BEST_WIDTH_FIT)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_best_height_fit(self):
        algo = ShelfAlgorithm(choice=ShelfChoice.BEST_HEIGHT_FIT)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_no_overlaps(self):
        algo = ShelfAlgorithm()
        rects = make_rects([(20, 30), (25, 20), (15, 40), (30, 25)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        for i, p1 in enumerate(placed):
            for p2 in placed[i+1:]:
                assert not p1.overlaps(p2)

    def test_reject_too_large(self):
        algo = ShelfAlgorithm()
        rects = make_rects([(200, 200)])
        _, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(rejected) == 1

    def test_with_rotation(self):
        algo = ShelfAlgorithm(rotation=RotationPolicy.ORTHOGONAL)
        # 80x20 won't fit in width=50, but 20x80 will
        rects = make_rects([(80, 20)])
        b = Bin(width=50, height=100)
        placed, _ = algo.pack_into_bin(rects, b)
        assert len(placed) == 1


# ===== Skyline Tests =====

class TestSkyline:
    def test_single_rect(self):
        algo = SkylineAlgorithm()
        rects = make_rects([(50, 50)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 1

    def test_bottom_left(self):
        algo = SkylineAlgorithm(choice=SkylineChoice.BOTTOM_LEFT)
        rects = make_rects([(30, 30)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert placed[0].x == 0
        assert placed[0].y == 0

    def test_best_fit(self):
        algo = SkylineAlgorithm(choice=SkylineChoice.BEST_FIT)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_min_waste(self):
        algo = SkylineAlgorithm(choice=SkylineChoice.MIN_WASTE)
        rects = make_rects([(30, 30), (20, 20)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 2

    def test_no_overlaps(self):
        algo = SkylineAlgorithm()
        rects = make_rects([(20, 30), (25, 20), (15, 40), (30, 25)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        for i, p1 in enumerate(placed):
            for p2 in placed[i+1:]:
                assert not p1.overlaps(p2), f"{p1} overlaps {p2}"

    def test_within_bin(self):
        algo = SkylineAlgorithm()
        rects = make_rects([(20, 30), (25, 20), (15, 40)])
        b = make_bin()
        placed, _ = algo.pack_into_bin(rects, b)
        for p in placed:
            assert p.right <= b.width + 1e-9
            assert p.bottom <= b.height + 1e-9

    def test_many_rects(self):
        algo = SkylineAlgorithm()
        rects = make_rects([(10, 10)] * 50)
        placed, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(placed) + len(rejected) == 50

    def test_with_rotation(self):
        algo = SkylineAlgorithm(rotation=RotationPolicy.ORTHOGONAL)
        rects = make_rects([(90, 20)])
        b = Bin(width=30, height=100)
        placed, _ = algo.pack_into_bin(rects, b)
        assert len(placed) == 1

    def test_reject_too_large(self):
        algo = SkylineAlgorithm()
        rects = make_rects([(200, 200)])
        _, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(rejected) == 1


# ===== Cross-algorithm tests =====

class TestCrossAlgorithm:
    """Tests that apply to all algorithms."""

    ALGORITHMS = [
        MaxRectsAlgorithm(),
        GuillotineAlgorithm(),
        ShelfAlgorithm(),
        SkylineAlgorithm(),
    ]

    @pytest.mark.parametrize("algo", ALGORITHMS, ids=lambda a: a.name)
    def test_empty_rects(self, algo):
        placed, rejected = algo.pack_into_bin([], make_bin())
        assert len(placed) == 0
        assert len(rejected) == 0

    @pytest.mark.parametrize("algo", ALGORITHMS, ids=lambda a: a.name)
    def test_single_rect_placed(self, algo):
        rects = make_rects([(50, 50)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 1

    @pytest.mark.parametrize("algo", ALGORITHMS, ids=lambda a: a.name)
    def test_rect_too_large_rejected(self, algo):
        rects = make_rects([(200, 200)])
        _, rejected = algo.pack_into_bin(rects, make_bin())
        assert len(rejected) == 1

    @pytest.mark.parametrize("algo", ALGORITHMS, ids=lambda a: a.name)
    def test_exact_fit_bin(self, algo):
        rects = make_rects([(100, 100)])
        placed, _ = algo.pack_into_bin(rects, make_bin())
        assert len(placed) == 1

    @pytest.mark.parametrize("algo", ALGORITHMS, ids=lambda a: a.name)
    def test_no_overlaps_multiple(self, algo):
        rects = make_rects([(25, 25)] * 8)
        placed, _ = algo.pack_into_bin(rects, make_bin())
        for i, p1 in enumerate(placed):
            for p2 in placed[i+1:]:
                assert not p1.overlaps(p2), f"{algo.name}: {p1} overlaps {p2}"

    @pytest.mark.parametrize("algo", ALGORITHMS, ids=lambda a: a.name)
    def test_placements_within_bin(self, algo):
        rects = make_rects([(30, 30), (20, 40), (40, 20)])
        b = make_bin()
        placed, _ = algo.pack_into_bin(rects, b)
        for p in placed:
            assert p.x >= -1e-9, f"{algo.name}: {p} x out of bounds"
            assert p.y >= -1e-9, f"{algo.name}: {p} y out of bounds"
            assert p.right <= b.width + 1e-9, f"{algo.name}: {p} right out of bounds"
            assert p.bottom <= b.height + 1e-9, f"{algo.name}: {p} bottom out of bounds"

    @pytest.mark.parametrize("algo", ALGORITHMS, ids=lambda a: a.name)
    def test_pack_returns_result(self, algo):
        rects = make_rects([(30, 30)])
        result = algo.pack(rects, [make_bin()])
        assert result.total_placed == 1
        assert result.algorithm == algo.name
