"""
CSV import/export for Tessera.

Allows importing rectangle lists from CSV files (e.g., from spreadsheets
or manufacturing systems) and exporting placement results.
"""

from __future__ import annotations

import csv
import io
from typing import List, Optional

from tessera.core import Bin, PackingResult, Rect


class CsvIO:
    """Import and export rectangles and results via CSV."""

    @staticmethod
    def import_rects(
        path: str,
        width_col: str = "width",
        height_col: str = "height",
        label_col: Optional[str] = "label",
        group_col: Optional[str] = "group",
        delimiter: str = ",",
    ) -> List[Rect]:
        """
        Import rectangles from a CSV file.

        Expected columns: width, height, and optionally label, group, priority.
        """
        rects = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                kwargs = {
                    "width": float(row[width_col]),
                    "height": float(row[height_col]),
                }

                if label_col and label_col in row:
                    kwargs["label"] = row[label_col]
                if group_col and group_col in row:
                    kwargs["group"] = row[group_col]
                if "priority" in row:
                    kwargs["priority"] = int(row["priority"])
                if "rid" in row:
                    kwargs["rid"] = row["rid"]
                if "rotatable" in row:
                    kwargs["rotatable"] = row["rotatable"].lower() in ("true", "1", "yes")

                rects.append(Rect(**kwargs))

        return rects

    @staticmethod
    def import_rects_from_string(
        content: str,
        width_col: str = "width",
        height_col: str = "height",
        delimiter: str = ",",
    ) -> List[Rect]:
        """Import rectangles from a CSV string."""
        rects = []
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        for row in reader:
            kwargs = {
                "width": float(row[width_col]),
                "height": float(row[height_col]),
            }
            if "label" in row:
                kwargs["label"] = row["label"]
            if "group" in row:
                kwargs["group"] = row["group"]
            if "rid" in row:
                kwargs["rid"] = row["rid"]
            rects.append(Rect(**kwargs))
        return rects

    @staticmethod
    def export_result(
        result: PackingResult,
        path: str,
        delimiter: str = ",",
    ) -> None:
        """Export placement results to CSV."""
        fieldnames = [
            "rid", "label", "x", "y", "width", "height",
            "original_width", "original_height", "rotated", "bin_index",
        ]

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()

            for p in result.placements:
                writer.writerow({
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
                })

    @staticmethod
    def export_result_to_string(
        result: PackingResult,
        delimiter: str = ",",
    ) -> str:
        """Export placement results to a CSV string."""
        output = io.StringIO()
        fieldnames = [
            "rid", "label", "x", "y", "width", "height",
            "original_width", "original_height", "rotated", "bin_index",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()

        for p in result.placements:
            writer.writerow({
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
            })

        return output.getvalue()
