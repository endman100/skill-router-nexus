from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops
from compose_turnaround_sheet import crop_subject


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify character turnaround sheet geometry.")
    parser.add_argument("image", type=Path)
    parser.add_argument("manifest", type=Path)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_unmeasured(image, data):
    """Check source geometry and compare exported pixels with a fresh render."""
    from compose_unmeasured_sheet import compose
    require(list(image.size) == data["canvas"], "Canvas size does not match manifest")
    require(data["ruler"] is None and data["body_data"] == [], "Unmeasured mode contains measurement data")
    top, bottom = data["alignment_y"]
    require(0 < top < bottom < image.height, "Invalid figure margins")
    require(top == image.height - bottom, "Top and sole margins differ")
    views, expressions = data["body_views"], data["expressions"]
    require(len(views) == len(expressions) == 3, "Expected three views and three expressions")
    previous_right = 0
    for name, p in views.items():
        x0, y0, x1, y1 = p["placed_box"]
        l, t, r, b = p["panel_box"]
        require(l == previous_right and t == 0 and b == image.height, f"{name}: header or gutter gap")
        require(l <= x0 < x1 <= r and y0 == top and y1 == bottom, f"{name}: incorrect body fit/alignment")
        require(y1 - y0 == p["height_px"], f"{name}: incorrect height_px")
        previous_right = r
    previous_bottom = 0
    for name, p in expressions.items():
        l, t, r, b = p["cell"]
        x0, y0, x1, y1 = p["placed_box"]
        require(l == previous_right and r == image.width and t == previous_bottom, f"{name}: expression gap")
        require(l <= x0 < x1 <= r and t <= y0 < y1 <= b, f"{name}: expression clipped")
        previous_bottom = b
    require(previous_bottom == image.height, "Expressions do not fill the full column")
    all_entries = list(views.items()) + list(expressions.items())
    require(data["rendered_labels"] == [p["label"] for _, p in all_entries], "Unexpected rendered labels")
    for name, p in all_entries:
        raw = Path(p["source"]).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == p["source_sha256"], f"{name}: source changed")
        subject = crop_subject(Path(p["source"]))
        require(list(subject.size) == p["source_crop_size"], f"{name}: incorrect crop dimensions")
        x0, y0, x1, y1 = p["placed_box"]
        # Both axes are rounded independently; tolerate <= half a pixel per axis.
        sw, sh = subject.size
        require(abs((x1-x0) * sh - (y1-y0) * sw) <= (sw+sh) / 2 + 1, f"{name}: distorted aspect ratio")
        l, t, r, b = p.get("panel_box", p.get("cell"))
        a, c, d, e = p["label_box"]
        require(l <= a < d <= r and t <= c < e <= b, f"{name}: label outside cell")
        require(d >= l + (r-l)*0.7 and e >= t + (b-t)*0.8, f"{name}: label is not lower-right")
    if "normal" in expressions:
        anchor = data["identity_anchor"]
        digest = hashlib.sha256(Path(anchor["source"]).read_bytes()).hexdigest()
        require(digest == anchor["source_sha256"] == expressions["normal"]["source_sha256"], "NORMAL is not the anchor")
    config = json.loads(Path(data["config"]).read_text(encoding="utf-8"))
    expected, fresh = compose(Path(data["asset_dir"]), config)
    for key in fresh:
        require(fresh[key] == data[key], f"Manifest mismatch: {key}")
    require(expected.size == image.size and ImageChops.difference(expected, image).getbbox() is None, "Exported pixels differ from deterministic source render")
    print(f"PASS: unmeasured canvas {image.width}x{image.height}; figures {bottom-top}px tall")
    print("PASS: no metric overlay or header; source aspect ratios and top/sole alignment preserved")
    print("PASS: three contiguous expressions; all labels lower-right; source hashes match")
    if "normal" in expressions:
        print("PASS: NORMAL is byte-identical to the accepted identity anchor")
    print("PASS: exported pixels match fresh deterministic rendering")


def main() -> None:
    args = parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    with Image.open(args.image).convert("RGB") as image:
        if data.get("layout_mode") == "unmeasured":
            verify_unmeasured(image, data)
            return
        require(data.get("layout_mode", "measured") == "measured", "Unknown layout mode")
        require(list(image.size) == data["canvas"], "Canvas size does not match manifest")
        require(image.height == 1876 and image.width >= 2300, f"Unexpected canvas: {image.size}")

        ruler = data["ruler"]
        require(ruler["max_cm"] == 200.0, "Ruler maximum is not 200 cm")
        require(
            ruler["height_source"] in {"user", "scale", "visual_estimate", "design_prior", "default"},
            "Unknown height source",
        )
        require(
            ruler["height_label"].startswith("~")
            if ruler["height_source"] in {"visual_estimate", "design_prior"}
            else not ruler["height_label"].startswith("~"),
            "Height label does not match height source",
        )
        require(
            ruler["height_label"].endswith(" (SET)") == (ruler["height_source"] == "design_prior"),
            "Design prior must be visibly identified as SET",
        )
        require(ruler["top_200_cm_y"] == 0, "200 cm is not flush with the top")
        require(ruler["zero_y"] == image.height - 1, "0 cm is not flush with the bottom")
        expected_scale = (image.height - 1) / 200.0
        require(abs(ruler["pixels_per_cm"] - expected_scale) < 1e-9, "Ruler scale is wrong")
        expected_height_y = round(
            ruler["zero_y"] - ruler["height_line_cm"] * ruler["pixels_per_cm"]
        )
        require(ruler["height_line_y"] == expected_height_y, "Height line position is wrong")
        if ruler["height_source"] == "design_prior":
            evidence_ref = data.get("height_evidence")
            require(bool(evidence_ref), "Design prior has no evidence record")
            raw = Path(evidence_ref["file"]).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == evidence_ref["sha256"], "Height evidence changed after composition")
            evidence = json.loads(raw.decode("utf-8-sig"))
            require(evidence["height_cm"] == ruler["height_line_cm"], "Evidence height mismatch")
            require(evidence["height_source"] == "design_prior" and evidence["physical_height_cm"] is None, "Design prior incorrectly claims physical height")

        views = data["body_views"]
        require(len(views) == 3, "Expected exactly three body views")
        for name, placement in views.items():
            left, top, right, bottom = placement["placed_box"]
            require(top == ruler["height_line_y"], f"{name}: top is not on the height line")
            require(bottom == ruler["zero_y"], f"{name}: soles are not on the zero line")
            require(bottom - top == placement["height_px"], f"{name}: height_px is inconsistent")
            subject = crop_subject(Path(placement["source"]))
            expected_width = round(subject.width * (bottom - top) / subject.height)
            require(abs((right - left) - expected_width) <= 1, f"{name}: source aspect ratio was distorted")
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
    print("PASS: body views preserve the input source aspect ratios")
    print("PASS: three expression rows are contiguous and fill the right column")
    print(f"PASS: red height-line coverage = {red_count}px")
    print(f"PASS: black zero-baseline coverage = {baseline_count}px")


if __name__ == "__main__":
    main()
