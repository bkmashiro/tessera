"""Tests for I/O module."""

import json
import os
import tempfile
import pytest
from tessera.core import Bin, PackingProblem, PackingResult, Placement, Rect, RotationPolicy
from tessera.io.json_io import JsonIO
from tessera.io.csv_io import CsvIO


class TestJsonIO:
    def test_export_import_problem(self):
        problem = PackingProblem()
        problem.add_rect(10, 20, label="A", group="g1")
        problem.add_rect(30, 40, label="B")
        problem.add_bin(100, 200, label="Main")
        problem.rotation = RotationPolicy.ORTHOGONAL
        problem.spacing = 5.0

        data = JsonIO.export_problem(problem)
        restored = JsonIO.import_problem(data)

        assert len(restored.rects) == 2
        assert len(restored.bins) == 1
        assert restored.rects[0].width == 10
        assert restored.rects[0].label == "A"
        assert restored.rects[0].group == "g1"
        assert restored.bins[0].width == 100
        assert restored.rotation == RotationPolicy.ORTHOGONAL
        assert restored.spacing == 5.0

    def test_export_result(self):
        r = Rect(10, 20, rid="test_rect", label="T")
        result = PackingResult(
            placements=[Placement(rect=r, x=5, y=10, rotated=True, bin_index=0)],
            rejected=[Rect(100, 100, rid="big", label="Big")],
            bins_used=1,
            algorithm="maxrects",
            elapsed_ms=10.5,
        )
        data = JsonIO.export_result(result)

        assert data["algorithm"] == "maxrects"
        assert len(data["placements"]) == 1
        assert data["placements"][0]["rid"] == "test_rect"
        assert data["placements"][0]["rotated"] is True
        assert len(data["rejected"]) == 1
        assert data["stats"]["total_placed"] == 1

    def test_save_load_problem(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            problem = PackingProblem()
            problem.add_rect(10, 20, label="A")
            problem.add_bin(100, 100)

            JsonIO.save_problem(problem, path)
            loaded = JsonIO.load_problem(path)

            assert len(loaded.rects) == 1
            assert loaded.rects[0].width == 10
            assert len(loaded.bins) == 1
        finally:
            os.unlink(path)

    def test_save_load_result(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            r = Rect(10, 20, rid="r1")
            result = PackingResult(
                placements=[Placement(rect=r, x=0, y=0)],
                bins_used=1,
                algorithm="test",
            )

            JsonIO.save_result(result, path)
            loaded = JsonIO.load_result(path)

            assert loaded["algorithm"] == "test"
            assert len(loaded["placements"]) == 1
        finally:
            os.unlink(path)

    def test_roundtrip_metadata(self):
        problem = PackingProblem()
        problem.add_rect(10, 10, metadata={"source": "scanner"})
        problem.add_bin(100, 100)

        data = JsonIO.export_problem(problem)
        restored = JsonIO.import_problem(data)
        assert restored.rects[0].metadata["source"] == "scanner"


class TestCsvIO:
    def test_import_from_string(self):
        csv_data = "width,height,label\n10,20,A\n30,40,B\n"
        rects = CsvIO.import_rects_from_string(csv_data)
        assert len(rects) == 2
        assert rects[0].width == 10
        assert rects[0].height == 20
        assert rects[0].label == "A"

    def test_import_from_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("width,height,label,group\n")
            f.write("10,20,A,g1\n")
            f.write("30,40,B,g2\n")
            path = f.name

        try:
            rects = CsvIO.import_rects(path)
            assert len(rects) == 2
            assert rects[0].group == "g1"
        finally:
            os.unlink(path)

    def test_export_result_to_string(self):
        r = Rect(10, 20, rid="r1", label="T")
        result = PackingResult(
            placements=[Placement(rect=r, x=5, y=10, rotated=False)],
            bins_used=1,
        )
        csv_str = CsvIO.export_result_to_string(result)
        assert "rid" in csv_str
        assert "r1" in csv_str
        assert "10" in csv_str

    def test_export_result_to_file(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name

        try:
            r = Rect(10, 20, rid="r1", label="T")
            result = PackingResult(
                placements=[Placement(rect=r, x=5, y=10)],
                bins_used=1,
            )
            CsvIO.export_result(result, path)

            with open(path) as f:
                content = f.read()
            assert "r1" in content
        finally:
            os.unlink(path)

    def test_custom_delimiter(self):
        csv_data = "width\theight\tlabel\n10\t20\tA\n"
        rects = CsvIO.import_rects_from_string(csv_data, delimiter="\t")
        assert len(rects) == 1
        assert rects[0].width == 10

    def test_rotatable_field(self):
        csv_data = "width,height,rotatable\n10,20,true\n30,40,false\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write(csv_data)
            path = f.name

        try:
            rects = CsvIO.import_rects(path)
            assert rects[0].rotatable is True
            assert rects[1].rotatable is False
        finally:
            os.unlink(path)
