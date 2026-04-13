"""
JSON import/export for Tessera.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TextIO, Union

from tessera.core import (
    Bin, PackingProblem, PackingResult, Placement, Rect,
    RotationPolicy, SortStrategy,
)


class JsonIO:
    """Import and export packing problems and results as JSON."""

    @staticmethod
    def export_problem(problem: PackingProblem) -> Dict[str, Any]:
        """Convert a PackingProblem to a JSON-serializable dict."""
        return {
            "version": "1.0",
            "rects": [
                {
                    "width": r.width,
                    "height": r.height,
                    "rid": r.rid,
                    "label": r.label,
                    "rotatable": r.rotatable,
                    "group": r.group,
                    "priority": r.priority,
                    "color": r.color,
                    "metadata": r.metadata,
                }
                for r in problem.rects
            ],
            "bins": [
                {
                    "width": b.width,
                    "height": b.height,
                    "bid": b.bid,
                    "label": b.label,
                    "padding": b.padding,
                }
                for b in problem.bins
            ],
            "rotation": problem.rotation.name,
            "sort_strategy": problem.sort_strategy.name,
            "spacing": problem.spacing,
            "multi_bin": problem.multi_bin,
        }

    @staticmethod
    def import_problem(data: Dict[str, Any]) -> PackingProblem:
        """Create a PackingProblem from a JSON dict."""
        problem = PackingProblem()

        for rd in data.get("rects", []):
            problem.rects.append(Rect(
                width=rd["width"],
                height=rd["height"],
                rid=rd.get("rid", ""),
                label=rd.get("label", ""),
                rotatable=rd.get("rotatable", True),
                group=rd.get("group", ""),
                priority=rd.get("priority", 0),
                color=rd.get("color", ""),
                metadata=rd.get("metadata", {}),
            ))

        for bd in data.get("bins", []):
            problem.bins.append(Bin(
                width=bd["width"],
                height=bd["height"],
                bid=bd.get("bid", ""),
                label=bd.get("label", ""),
                padding=bd.get("padding", 0.0),
            ))

        rot_name = data.get("rotation", "NONE")
        problem.rotation = RotationPolicy[rot_name]

        sort_name = data.get("sort_strategy", "AREA_DESC")
        problem.sort_strategy = SortStrategy[sort_name]

        problem.spacing = data.get("spacing", 0.0)
        problem.multi_bin = data.get("multi_bin", False)

        return problem

    @staticmethod
    def export_result(result: PackingResult) -> Dict[str, Any]:
        """Convert a PackingResult to a JSON-serializable dict."""
        return {
            "version": "1.0",
            "algorithm": result.algorithm,
            "placements": [
                {
                    "rid": p.rect.rid,
                    "label": p.rect.label,
                    "x": p.x,
                    "y": p.y,
                    "width": p.placed_width,
                    "height": p.placed_height,
                    "original_width": p.rect.width,
                    "original_height": p.rect.height,
                    "rotated": p.rotated,
                    "bin_index": p.bin_index,
                }
                for p in result.placements
            ],
            "rejected": [
                {
                    "rid": r.rid,
                    "label": r.label,
                    "width": r.width,
                    "height": r.height,
                }
                for r in result.rejected
            ],
            "stats": {
                "total_placed": result.total_placed,
                "total_rejected": result.total_rejected,
                "bins_used": result.bins_used,
                "placed_area": result.placed_area,
                "elapsed_ms": result.elapsed_ms,
                "iterations": result.iterations,
            },
            "metadata": result.metadata,
        }

    @staticmethod
    def save_problem(problem: PackingProblem, path: str) -> None:
        """Save a problem to a JSON file."""
        data = JsonIO.export_problem(problem)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_problem(path: str) -> PackingProblem:
        """Load a problem from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return JsonIO.import_problem(data)

    @staticmethod
    def save_result(result: PackingResult, path: str) -> None:
        """Save a result to a JSON file."""
        data = JsonIO.export_result(result)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_result(path: str) -> Dict[str, Any]:
        """Load a result from a JSON file."""
        with open(path) as f:
            return json.load(f)
