from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify character turnaround sheet geometry.")
    parser.add_argument("image", type=Path)
    parser.add_argument("manifest", type=Path)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    args = parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    with Image.open(args.image).convert("RGB") as image:
        require(list(image.size) == data["canvas"], "Canvas size does not match manifest")
        require(image.size == (2300, 1876), f"Unexpected canvas: {image.size}")

        ruler = data["ruler"]
        require(ruler["max_cm"] == 200.0, "Ruler maximum is not 200 cm")
        require(
            ruler["height_source"] in {"user", "scale", "visual_estimate", "default"},
            "Unknown height source",
        )
        require(
            ruler["height_label"].startswith("~")
            if ruler["height_source"] == "visual_estimate"
            else not ruler["height_label"].startswith("~"),
            "Height label does not match height source",
        )
        require(ruler["top_200_cm_y"] == 0, "200 cm is not flush with the top")
        require(ruler["zero_y"] == image.height - 1, "0 cm is not flush with the bottom")
        expected_scale = (image.height - 1) / 200.0
        require(abs(ruler["pixels_per_cm"] - expected_scale) < 1e-9, "Ruler scale is wrong")
        expected_height_y = round(
            ruler["zero_y"] - ruler["height_line_cm"] * ruler["pixels_per_cm"]
        )
        require(ruler["height_line_y"] == expected_height_y, "Height line position is wrong")

        views = data["body_views"]
        require(len(views) == 3, "Expected exactly three body views")
        for name, placement in views.items():
            left, top, right, bottom = placement["placed_box"]
            require(top == ruler["height_line_y"], f"{name}: top is not on the height line")
            require(bottom == ruler["zero_y"], f"{name}: soles are not on the zero line")
            require(bottom - top == placement["height_px"], f"{name}: height_px is inconsistent")
            require(abs(placement["height_cm"] - ruler["height_line_cm"]) < 1e-9, f"{name}: height_cm is inconsistent")
            panel_left, panel_top, panel_right, panel_bottom = placement["panel_box"]
            require(panel_left <= left < right <= panel_right, f"{name}: body is outside its panel")
            label_left, label_top, label_right, label_bottom = placement["label_box"]
            require(panel_left <= label_left < label_right <= panel_right, f"{name}: label exceeds panel width")
            require(panel_top <= label_top < label_bottom < panel_bottom, f"{name}: label exceeds panel height")

        expressions = data["expressions"]
        require(len(expressions) == 3, "Expected exactly three expressions")
        cells = [entry["cell"] for entry in expressions.values()]
        require(cells[0][1] == 0, "Expression column does not start at the top")
        require(cells[0][3] == cells[1][1], "Expression rows 1 and 2 have a gap")
        require(cells[1][3] == cells[2][1], "Expression rows 2 and 3 have a gap")
        require(cells[2][3] == image.height, "Expression column does not reach the bottom")
        expression_left = cells[0][0]
        require(
            all(cell[0] == expression_left and cell[2] == image.width for cell in cells),
            "Expression cell widths differ",
        )
        for name, placement in expressions.items():
            cell_left, cell_top, cell_right, cell_bottom = placement["cell"]
            label_left, label_top, label_right, label_bottom = placement["label_box"]
            require(cell_left <= label_left < label_right < cell_right, f"{name}: label exceeds cell width")
            require(cell_top <= label_top < label_bottom < cell_bottom, f"{name}: label exceeds cell height")

        pixels = image.load()
        line_y = ruler["height_line_y"]
        red_count = sum(
            1
            for x in range(ruler["x"], expression_left)
            if pixels[x, line_y][0] > 180 and pixels[x, line_y][1] < 60 and pixels[x, line_y][2] < 60
        )
        line_span = expression_left - ruler["x"]
        occluded_width = sum(
            max(
                0,
                min(expression_left, placement["placed_box"][2])
                - max(ruler["x"], placement["placed_box"][0]),
            )
            for placement in views.values()
        )
        minimum_red_count = line_span - occluded_width - 16
        require(
            red_count >= minimum_red_count,
            f"Height line coverage is too short: {red_count}px; expected at least {minimum_red_count}px",
        )

        baseline_count = sum(
            1
            for x in range(160, expression_left)
            if all(channel < 70 for channel in pixels[x, image.height - 1])
        )
        require(baseline_count > 1000, f"Zero baseline coverage is too short: {baseline_count}px")

        width, height = image.size

    print(f"PASS: canvas {width}x{height}")
    print("PASS: ruler runs from 200 cm at the top to 0 cm at the bottom")
    print(f"PASS: ruler scale = {ruler['pixels_per_cm']:.3f} px/cm")
    print(f"PASS: three body views align to {ruler['height_line_cm']:.1f} cm")
    print(f"PASS: height source = {ruler['height_source']} ({ruler['height_label']})")
    print("PASS: view and expression labels remain inside their cells")
    print("PASS: three expression rows are contiguous and fill the right column")
    print(f"PASS: red height-line coverage = {red_count}px")
    print(f"PASS: black zero-baseline coverage = {baseline_count}px")


if __name__ == "__main__":
    main()
