from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


CANVAS = (2300, 1876)
RULER_X = 92
RULER_TOP = 0
RULER_MAX_CM = 200.0
BASELINE_Y = CANVAS[1] - 1
PIXELS_PER_CM = (BASELINE_Y - RULER_TOP) / RULER_MAX_CM
BODY_LEFT = 150
BODY_RIGHT = 1725
EXPRESSION_LEFT = BODY_RIGHT
BODY_PANEL_WIDTH = (BODY_RIGHT - BODY_LEFT) // 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose a character sheet; no rulers by default.")
    parser.add_argument("asset_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--config", required=True, type=Path)
    return parser.parse_args()


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def on_white(image: Image.Image) -> Image.Image:
    """Respect alpha before measuring or pasting; hidden RGB is not foreground."""
    rgba = image.convert("RGBA")
    white = Image.new("RGBA", image.size, "white")
    return Image.alpha_composite(white, rgba).convert("RGB")


def foreground_bbox(image: Image.Image, threshold: int = 6) -> tuple[int, int, int, int]:
    """Retain faint clothing edges while suppressing isolated near-white noise.

    Ignore the 0-5 channel-level background variation seen in generated white
    assets while retaining the pale edges discarded by the former threshold 18.
    This is white-margin detection, not semantic segmentation. Pure-white details
    indistinguishable from the background still require visual crop review.
    """
    rgb = on_white(image)
    channels = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white")).split()
    difference = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    faint = difference.point(lambda value: 255 if value > threshold else 0)
    strong = difference.point(lambda value: 255 if value > max(18, threshold) else 0)
    mask = ImageChops.lighter(faint.filter(ImageFilter.MedianFilter(3)), strong)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("No non-white subject found")
    return bbox


def crop_subject(path: Path) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as source:
        image = on_white(source)
    return image.crop(foreground_bbox(image))


def centered_x(left: int, right: int, width: int) -> int:
    return left + (right - left - width) // 2


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), text, font=font)


def draw_bottom_right_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
) -> None:
    _, _, right, bottom = box
    text_box = text_size(draw, text, font)
    width = text_box[2] - text_box[0]
    height = text_box[3] - text_box[1]
    draw.text((right - width, bottom - height - text_box[1]), text, font=font, fill="#111111")


def draw_bottom_right_tag(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
) -> tuple[int, int, int, int]:
    _, _, right, bottom = box
    text_box = text_size(draw, text, font)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    padding_x, padding_y = 10, 6
    tag_box = (
        right - text_width - padding_x * 2,
        bottom - text_height - padding_y * 2,
        right,
        bottom,
    )
    draw.rounded_rectangle(tag_box, radius=7, fill="white", outline="#b8b8b8", width=2)
    draw.text(
        (tag_box[0] + padding_x, tag_box[1] + padding_y - text_box[1]),
        text,
        font=font,
        fill="#111111",
    )
    return tag_box


def require_entries(config: dict[str, Any], key: str, count: int) -> list[dict[str, str]]:
    entries = config.get(key)
    if not isinstance(entries, list) or len(entries) != count:
        raise ValueError(f"config.{key} must contain exactly {count} entries")
    for entry in entries:
        if not isinstance(entry, dict) or not all(entry.get(field) for field in ("name", "file", "label")):
            raise ValueError(f"Every config.{key} entry needs name, file, and label")
    if len({entry["name"] for entry in entries}) != count:
        raise ValueError(f"config.{key} names must be unique")
    return entries


def draw_body_data(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    height_line_y: int,
    heading_font: ImageFont.ImageFont,
    body_font: ImageFont.ImageFont,
) -> None:
    if not lines:
        return
    rows = (len(lines) + 2) // 3
    content_bottom = 105 + max(0, rows - 1) * 70 + 42
    if content_bottom + 24 >= height_line_y:
        raise ValueError(
            "Body Data does not fit above the configured height line. "
            "Use an empty body_data list or create a separate measurement sheet."
        )
    draw.text((130, 40), "BODY DATA", font=heading_font, fill="#111111")
    columns = [lines[index * rows : (index + 1) * rows] for index in range(3)]
    for column_index, column in enumerate(columns):
        x = 140 + column_index * 510
        for line_index, line in enumerate(column):
            draw.text((x, 105 + line_index * 70), f"• {line}", font=body_font, fill="#222222")


def main() -> None:
    global CANVAS, BODY_RIGHT, EXPRESSION_LEFT, BODY_PANEL_WIDTH
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    mode = config.get("layout_mode", "unmeasured")
    if mode == "unmeasured":
        from compose_unmeasured_sheet import compose
        canvas, manifest = compose(args.asset_dir, config)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(args.output, optimize=True)
        manifest.update(output=str(args.output.resolve()), config=str(args.config.resolve()))
        manifest_path = args.output.with_name(f"{args.output.stem}.manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(args.output.resolve())
        print(manifest_path.resolve())
        return
    if mode != "measured":
        raise ValueError("layout_mode must be unmeasured or measured")
    views = require_entries(config, "views", 3)
    expressions = require_entries(config, "expressions", 3)
    height_cm = float(config.get("height_cm", 160.0))
    height_source = str(config.get("height_source", "default"))
    allowed_height_sources = {"user", "scale", "visual_estimate", "design_prior", "default"}
    if height_source not in allowed_height_sources:
        raise ValueError(
            "height_source must be one of: user, scale, visual_estimate, design_prior, default"
        )
    if not 0 < height_cm <= RULER_MAX_CM:
        raise ValueError("height_cm must be greater than 0 and no greater than 200")
    height_evidence = None
    if height_source == "design_prior":
        evidence_name = config.get("height_evidence_file")
        if not evidence_name:
            raise ValueError("design_prior requires height_evidence_file")
        evidence_path = args.asset_dir / evidence_name
        evidence_raw = evidence_path.read_bytes()
        evidence = json.loads(evidence_raw.decode("utf-8-sig"))
        if evidence.get("height_source") != height_source or evidence.get("height_cm") != height_cm:
            raise ValueError("Height evidence does not match compositor config")
        if evidence.get("physical_height_cm") is not None:
            raise ValueError("A design prior must not claim physical height")
        height_evidence = {"file": str(evidence_path.resolve()), "sha256": hashlib.sha256(evidence_raw).hexdigest()}
    body_data = config.get("body_data", [])
    if not isinstance(body_data, list) or not all(isinstance(item, str) for item in body_data):
        raise ValueError("body_data must be a list of strings")

    height_line_y = round(BASELINE_Y - height_cm * PIXELS_PER_CM)
    target_height = BASELINE_Y - height_line_y
    # Expand columns instead of changing a character's width-to-height ratio.
    if config.get("auto_expand_width", False):
        sizes = [crop_subject(args.asset_dir / entry["file"]).size for entry in views]
        BODY_PANEL_WIDTH = max(525, max(round(w * target_height / h) for w, h in sizes) + 24)
        BODY_RIGHT = BODY_LEFT + BODY_PANEL_WIDTH * 3
        EXPRESSION_LEFT = BODY_RIGHT
        CANVAS = (BODY_RIGHT + 575, CANVAS[1])
    args.output.parent.mkdir(parents=True, exist_ok=True)

    canvas = Image.new("RGB", CANVAS, "white")
    draw = ImageDraw.Draw(canvas)
    heading_font = load_font(30, bold=True)
    body_font = load_font(31)
    label_font = load_font(27, bold=True)
    ruler_font = load_font(25)
    draw_body_data(draw, body_data, height_line_y, heading_font, body_font)

    draw.line((RULER_X, RULER_TOP, RULER_X, BASELINE_Y), fill="#111111", width=4)
    for cm in range(0, int(RULER_MAX_CM) + 1, 5):
        y = round(BASELINE_Y - cm * PIXELS_PER_CM)
        major, medium = cm % 50 == 0, cm % 10 == 0
        tick = 36 if major else 25 if medium else 15
        width = 4 if major else 3 if medium else 2
        draw.line((RULER_X - tick, y, RULER_X + tick, y), fill="#111111", width=width)
        if major:
            label = str(cm)
            box = text_size(draw, label, ruler_font)
            text_height = box[3] - box[1]
            visible_top = max(0, min(y - text_height // 2, CANVAS[1] - text_height))
            draw.text((RULER_X - tick - 18 - (box[2] - box[0]), visible_top - box[1]), label, font=ruler_font, fill="#111111")

    draw.line((RULER_X, height_line_y, BODY_RIGHT, height_line_y), fill="#e00000", width=4)
    height_value = f"{height_cm:g}"
    height_label = f"{'~' if height_source in {'visual_estimate', 'design_prior'} else ''}{height_value} cm"
    if height_source == "design_prior":
        height_label += " (SET)"
    label_width = max(210, len(height_label) * 18)
    draw.rounded_rectangle((120, height_line_y - 52, 120 + label_width, height_line_y - 8), 8, fill="white")
    draw.text((135, height_line_y - 48), height_label, font=label_font, fill="#e00000")

    for divider in (BODY_LEFT, BODY_LEFT + BODY_PANEL_WIDTH, BODY_LEFT + 2 * BODY_PANEL_WIDTH):
        draw.line((divider, height_line_y, divider, BASELINE_Y), fill="#333333", width=3)
    draw.line((160, BASELINE_Y, BODY_RIGHT, BASELINE_Y), fill="#111111", width=4)

    placements: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(views):
        path = args.asset_dir / entry["file"]
        subject = crop_subject(path)
        width = round(subject.width * (target_height / subject.height))
        resized = subject.resize((width, target_height), Image.Resampling.LANCZOS)
        panel_left = BODY_LEFT + index * BODY_PANEL_WIDTH
        panel_right = BODY_LEFT + (index + 1) * BODY_PANEL_WIDTH
        x = centered_x(panel_left, panel_right, width)
        if x < panel_left or x + width > panel_right:
            raise ValueError(f"{entry['name']} becomes wider than its body panel at the configured height")
        canvas.paste(resized, (x, height_line_y))
        label_box = (panel_left + 18, height_line_y + 18, panel_right - 18, BASELINE_Y - 18)
        draw_bottom_right_text(draw, label_box, entry["label"], label_font)
        placements[entry["name"]] = {
            "source": str(path.resolve()),
            "panel_box": [panel_left, height_line_y, panel_right, BASELINE_Y],
            "placed_box": [x, height_line_y, x + width, BASELINE_Y],
            "height_px": target_height,
            "height_cm": height_cm,
            "label_box": list(label_box),
        }

    pixels = canvas.load()
    for y in range(max(0, height_line_y - 1), min(CANVAS[1], height_line_y + 2)):
        for x in range(RULER_X, BODY_RIGHT):
            red, green, blue = pixels[x, y]
            if red > 244 and green > 244 and blue > 244:
                pixels[x, y] = (224, 0, 0)

    expression_height = CANVAS[1] // 3
    expression_placements: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(expressions):
        cell_top = index * expression_height
        cell_bottom = CANVAS[1] if index == 2 else (index + 1) * expression_height
        if index > 0:
            draw.line((EXPRESSION_LEFT, cell_top, CANVAS[0], cell_top), fill="#333333", width=3)
        path = args.asset_dir / entry["file"]
        subject = crop_subject(path)
        available_width = CANVAS[0] - EXPRESSION_LEFT - 36
        available_height = cell_bottom - cell_top - 24
        scale = min(available_width / subject.width, available_height / subject.height)
        size = (round(subject.width * scale), round(subject.height * scale))
        resized = subject.resize(size, Image.Resampling.LANCZOS)
        x = centered_x(EXPRESSION_LEFT, CANVAS[0], size[0])
        y = cell_top + max(8, (available_height - size[1]) // 2)
        canvas.paste(resized, (x, y))
        label_box = draw_bottom_right_tag(
            draw,
            (EXPRESSION_LEFT + 14, cell_top + 14, CANVAS[0] - 14, cell_bottom - 14),
            entry["label"],
            label_font,
        )
        expression_placements[entry["name"]] = {
            "source": str(path.resolve()),
            "placed_box": [x, y, x + size[0], y + size[1]],
            "cell": [EXPRESSION_LEFT, cell_top, CANVAS[0], cell_bottom],
            "label_box": list(label_box),
        }

    draw.line((BODY_RIGHT, 0, BODY_RIGHT, CANVAS[1]), fill="#222222", width=4)
    for y in (expression_height, expression_height * 2):
        draw.line((EXPRESSION_LEFT, y, CANVAS[0], y), fill="#222222", width=3)

    canvas.save(args.output, optimize=True)
    manifest = {
        "layout_mode": "measured",
        "output": str(args.output.resolve()),
        "config": str(args.config.resolve()),
        "canvas": list(CANVAS),
        "height_evidence": height_evidence,
        "ruler": {
            "x": RULER_X,
            "max_cm": RULER_MAX_CM,
            "top_200_cm_y": RULER_TOP,
            "zero_y": BASELINE_Y,
            "pixels_per_cm": PIXELS_PER_CM,
            "height_line_cm": height_cm,
            "height_line_y": height_line_y,
            "height_source": height_source,
            "height_label": height_label,
        },
        "body_views": placements,
        "expressions": expression_placements,
    }
    manifest_path = args.output.with_name(f"{args.output.stem}.manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(manifest_path.resolve())


if __name__ == "__main__":
    main()
