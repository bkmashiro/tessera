"""Tests for the CLI."""

import json
import os
import tempfile
import pytest
from tessera.cli import main, parse_dimensions, create_parser
from tessera.core import PackingProblem
from tessera.io.json_io import JsonIO


class TestParseDimensions:
    def test_basic(self):
        w, h = parse_dimensions("100x200")
        assert w == 100 and h == 200

    def test_float(self):
        w, h = parse_dimensions("10.5x20.3")
        assert w == 10.5 and h == 20.3

    def test_invalid(self):
        with pytest.raises(ValueError):
            parse_dimensions("100")

    def test_uppercase(self):
        w, h = parse_dimensions("100X200")
        assert w == 100 and h == 200


class TestCLI:
    def _make_problem_file(self):
        """Create a temp problem file."""
        problem = PackingProblem()
        problem.add_bin(100, 100)
        for i in range(5):
            problem.add_rect(20, 20, label=f"R{i}")

        f = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        json.dump(JsonIO.export_problem(problem), f)
        f.close()
        return f.name

    def test_no_args(self):
        ret = main([])
        assert ret == 0

    def test_solve(self):
        path = self._make_problem_file()
        try:
            ret = main(["solve", path])
            assert ret == 0
        finally:
            os.unlink(path)

    def test_solve_with_algorithm(self):
        path = self._make_problem_file()
        try:
            ret = main(["solve", path, "-a", "guillotine"])
            assert ret == 0
        finally:
            os.unlink(path)

    def test_solve_with_output(self):
        path = self._make_problem_file()
        output = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            ret = main(["solve", path, "-o", output])
            assert ret == 0
            assert os.path.exists(output)
            with open(output) as f:
                data = json.load(f)
            assert "placements" in data
        finally:
            os.unlink(path)
            os.unlink(output)

    def test_solve_with_svg(self):
        path = self._make_problem_file()
        svg_path = tempfile.NamedTemporaryFile(suffix=".svg", delete=False).name
        try:
            ret = main(["solve", path, "--svg", svg_path])
            assert ret == 0
            assert os.path.exists(svg_path)
            with open(svg_path) as f:
                content = f.read()
            assert "<svg" in content
        finally:
            os.unlink(path)
            os.unlink(svg_path)

    def test_solve_with_ascii(self):
        path = self._make_problem_file()
        try:
            ret = main(["solve", path, "--ascii"])
            assert ret == 0
        finally:
            os.unlink(path)

    def test_solve_with_stats(self):
        path = self._make_problem_file()
        try:
            ret = main(["solve", path, "--stats"])
            assert ret == 0
        finally:
            os.unlink(path)

    def test_solve_skyline(self):
        path = self._make_problem_file()
        try:
            ret = main(["solve", path, "-a", "skyline"])
            assert ret == 0
        finally:
            os.unlink(path)

    def test_solve_shelf(self):
        path = self._make_problem_file()
        try:
            ret = main(["solve", path, "-a", "shelf"])
            assert ret == 0
        finally:
            os.unlink(path)

    def test_benchmark(self):
        path = self._make_problem_file()
        try:
            ret = main(["benchmark", path])
            assert ret == 0
        finally:
            os.unlink(path)

    def test_quick(self):
        ret = main(["quick", "100x100", "--rects", "30x30,20x20,40x40"])
        assert ret == 0

    def test_quick_with_rotation(self):
        ret = main(["quick", "100x100", "--rects", "30x30,20x20", "-r"])
        assert ret == 0

    def test_generate(self):
        output = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            ret = main(["generate", "-n", "10", "--output", output, "--seed", "42"])
            assert ret == 0
            assert os.path.exists(output)
        finally:
            os.unlink(output)

    def test_solve_no_input(self):
        ret = main(["solve"])
        assert ret == 1
