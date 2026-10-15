"""Reusable 5-column by 3-row character-sheet layout with no metric assumptions."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PIL import Image, ImageDraw

from compose_turnaround_sheet import (
    centered_x, crop_subject, draw_bottom_right_tag, load_font,
    require_entries, text_size,
)


def positive_int(config, key, default, minimum=1):
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{key} must be an integer >= {minimum}")
    return value


def require_entry(config, key):
    entry = config.get(key)
    if not isinstance(entry, dict) or not all(entry.get(field) for field in ("name", "file", "label")):
        raise ValueError(f"config.{key} needs name, file, and label")
    return entry


def source_info(path, subject):
    return {
        "source": str(path.resolve()),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_crop_size": list(subject.size),
    }


def fit_asset(asset_dir, entry, cell, canvas, draw, font, inset=18):
    left, top, right, bottom = cell
    path = asset_dir / entry["file"]
    subject = crop_subject(path)
    label_width = text_size(draw, entry["label"], font)[2]
    if label_width + 48 > right - left:
        raise ValueError(f"{entry['name']}: label exceeds cell width")
    available_width = right - left - inset * 2
    available_height = bottom - top - 24
    scale = min(available_width / subject.width, available_height / subject.height)
    size = (max(1, round(subject.width * scale)), max(1, round(subject.height * scale)))
    x = centered_x(left, right, size[0])
    y = top + max(8, (bottom - top - size[1]) // 2)
    canvas.paste(subject.resize(size, Image.Resampling.LANCZOS), (x, y))
    label_box = draw_bottom_right_tag(
        draw, (left + 14, top + 14, right - 14, bottom - 14), entry["label"], font,
    )
    return dict(
        source_info(path, subject), cell=list(cell),
        placed_box=[x, y, x + size[0], y + size[1]],
        label=entry["label"], label_box=list(label_box),
    )


def compose(asset_dir: Path, config: dict) -> tuple[Image.Image, dict]:
    """Render nine accepted assets into the default 5-by-3 grid."""
    if config.get("layout_mode", "unmeasured") != "unmeasured":
        raise ValueError("This compositor only accepts unmeasured layout")
    views = require_entries(config, "views", 3)
    details = require_entries(config, "details", 3)
    expressions = require_entries(config, "expressions", 2)
    neutral = require_entry(config, "neutral_portrait")
    all_names = [entry["name"] for entry in views + details + expressions + [neutral]]
    if len(set(all_names)) != len(all_names):
        raise ValueError("All asset names across the config must be unique")

    height = positive_int(config, "canvas_height_px", 1876, 300)
    margin = positive_int(config, "body_margin_px", 20)
    padding = positive_int(config, "panel_side_padding_px", 16)
    minimum_column_width = positive_int(config, "grid_column_width_px", 575, 128)
    row_edges = [round(height * index / 3) for index in range(4)]
    body_top, body_bottom = row_edges[1], row_edges[3]
    target_height = body_bottom - body_top - 2 * margin
    if target_height < 64:
        raise ValueError("body_margin_px leaves insufficient space for the figures")

    body_subjects = [crop_subject(asset_dir / entry["file"]) for entry in views]
    font = load_font(min(27, max(14, minimum_column_width // 18)), bold=True)
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    single_cell_entries = views + details + expressions
    label_widths = [text_size(measure, entry["label"], font)[2] for entry in single_cell_entries]
    column_width = max(
        minimum_column_width,
        math.ceil(max(subject.width * target_height / subject.height for subject in body_subjects)) + 2 * padding,
        max(label_widths) + 28,
    )
    canvas = Image.new("RGB", (column_width * 5, height), "white")
    draw = ImageDraw.Draw(canvas)

    detail_placements = {}
    for index, entry in enumerate(details):
        cell = (index * column_width, row_edges[0], (index + 1) * column_width, row_edges[1])
        detail_placements[entry["name"]] = fit_asset(asset_dir, entry, cell, canvas, draw, font)

    expression_placements = {}
    for offset, entry in enumerate(expressions, start=3):
        cell = (offset * column_width, row_edges[0], (offset + 1) * column_width, row_edges[1])
        expression_placements[entry["name"]] = fit_asset(asset_dir, entry, cell, canvas, draw, font)

    body_placements = {}
    for index, (entry, subject) in enumerate(zip(views, body_subjects)):
        left, right = index * column_width, (index + 1) * column_width
        width = round(subject.width * target_height / subject.height)
        if width < 1 or width + 2 * padding > column_width:
            raise ValueError(f"{entry['name']}: body asset does not fit its grid column")
        x = centered_x(left, right, width)
        y = body_top + margin
        canvas.paste(subject.resize((width, target_height), Image.Resampling.LANCZOS), (x, y))
        label_box = draw_bottom_right_tag(
            draw, (left + 14, body_top + 14, right - 14, body_bottom - 14), entry["label"], font,
        )
        body_placements[entry["name"]] = dict(
            source_info(asset_dir / entry["file"], subject),
            panel_box=[left, body_top, right, body_bottom],
            placed_box=[x, y, x + width, y + target_height],
            height_px=target_height, label=entry["label"], label_box=list(label_box),
        )

    neutral_cell = (3 * column_width, body_top, 5 * column_width, body_bottom)
    neutral_placement = fit_asset(asset_dir, neutral, neutral_cell, canvas, draw, font, inset=28)

    for x in range(column_width, canvas.width, column_width):
        draw.line((x, 0, x, row_edges[1]), fill="#333333", width=3)
    draw.line((0, row_edges[1], canvas.width, row_edges[1]), fill="#333333", width=3)
    for x in range(column_width, 4 * column_width, column_width):
        draw.line((x, row_edges[1], x, height - 1), fill="#333333", width=3)

    anchor_path = asset_dir / config.get("identity_anchor", "identity-anchor.png")
    anchor_digest = hashlib.sha256(anchor_path.read_bytes()).hexdigest()
    if anchor_digest != neutral_placement["source_sha256"]:
        raise ValueError("NORMAL must remain byte-identical to the identity anchor")
    anchor = {"source": str(anchor_path.resolve()), "source_sha256": anchor_digest}

    ordered = details + expressions + views + [neutral]
    return canvas, {
        "layout_mode": "unmeasured", "canvas": list(canvas.size),
        "asset_dir": str(asset_dir.resolve()),
        "ruler": None, "body_data": [],
        "grid": {
            "columns": 5, "rows": 3, "column_width_px": column_width,
            "row_edges_px": row_edges,
        },
        "rendered_labels": [entry["label"] for entry in ordered],
        "alignment_y": [body_top + margin, body_bottom - margin],
        "details": detail_placements,
        "body_views": body_placements,
        "expressions": expression_placements,
        "neutral_portrait": neutral_placement,
        "identity_anchor": anchor,
        "asset_generation": "Reused accepted source assets; deterministic 5x3 layout only.",
    }
