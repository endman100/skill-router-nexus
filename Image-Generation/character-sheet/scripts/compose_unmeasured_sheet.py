"""Reusable pixel-space layout; no metric assumptions or previous-sheet dependency."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PIL import Image, ImageDraw

from compose_turnaround_sheet import (
    centered_x, crop_subject, draw_bottom_right_tag, draw_bottom_right_text,
    load_font, require_entries, text_size,
)


def positive_int(config, key, default, minimum=1):
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{key} must be an integer >= {minimum}")
    return value


def source_info(path, subject):
    return {
        "source": str(path.resolve()),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_crop_size": list(subject.size),
    }


def compose(asset_dir: Path, config: dict) -> tuple[Image.Image, dict]:
    """Render from six accepted source images; ignore stale metric fields."""
    if config.get("layout_mode", "unmeasured") != "unmeasured":
        raise ValueError("This compositor only accepts unmeasured layout")
    views = require_entries(config, "views", 3)
    expressions = require_entries(config, "expressions", 3)
    height = positive_int(config, "canvas_height_px", 1876, 256)
    margin = positive_int(config, "body_margin_px", 20)
    padding = positive_int(config, "panel_side_padding_px", 16)
    expression_width = positive_int(config, "expression_column_width_px", 575, 128)
    target_height = height - 2 * margin
    if target_height < 64:
        raise ValueError("body_margin_px leaves insufficient space for the figures")
    subjects = [crop_subject(asset_dir / entry["file"]) for entry in views]
    font = load_font(27, bold=True)
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    label_widths = [text_size(measure, e["label"], font)[2] for e in views]
    panel_width = max(
        math.ceil(max(s.width * target_height / s.height for s in subjects)) + 2 * padding,
        max(label_widths) + 28,
    )
    body_right = panel_width * 3
    canvas = Image.new("RGB", (body_right + expression_width, height), "white")
    draw = ImageDraw.Draw(canvas)
    for y in (margin, height - margin):
        draw.line((0, y, body_right, y), fill="#dedede", width=1)
    placements = {}
    for index, (entry, subject) in enumerate(zip(views, subjects)):
        left, right = index * panel_width, (index + 1) * panel_width
        width = round(subject.width * target_height / subject.height)
        if width < 1:
            raise ValueError("Body asset is too narrow at this output size")
        x = centered_x(left, right, width)
        canvas.paste(subject.resize((width, target_height), Image.Resampling.LANCZOS), (x, margin))
        draw_bottom_right_text(draw, (left + 14, 14, right - 14, height - 10), entry["label"], font)
        tb = text_size(draw, entry["label"], font)
        label_box = [right - 14 - (tb[2] - tb[0]), height - 10 - (tb[3] - tb[1]), right - 14, height - 10]
        placements[entry["name"]] = dict(
            source_info(asset_dir / entry["file"], subject),
            panel_box=[left, 0, right, height],
            placed_box=[x, margin, x + width, height - margin],
            height_px=target_height, label=entry["label"], label_box=label_box,
        )
    for x in (panel_width, panel_width * 2, body_right):
        draw.line((x, 0, x, height - 1), fill="#444444", width=2)

    # Render locally so a layout-only change reproduces the accepted column exactly.
    column = Image.new("RGB", (expression_width, height), "white")
    face_draw = ImageDraw.Draw(column)
    row_height = height // 3
    face_placements = {}
    for index, entry in enumerate(expressions):
        top = index * row_height
        bottom = height if index == 2 else (index + 1) * row_height
        path = asset_dir / entry["file"]
        subject = crop_subject(path)
        if text_size(face_draw, entry["label"], font)[2] + 48 > expression_width:
            raise ValueError("Expression label exceeds column width")
        available_width, available_height = expression_width - 36, bottom - top - 24
        scale = min(available_width / subject.width, available_height / subject.height)
        size = (max(1, round(subject.width * scale)), max(1, round(subject.height * scale)))
        x = centered_x(0, expression_width, size[0])
        y = top + max(8, (available_height - size[1]) // 2)
        column.paste(subject.resize(size, Image.Resampling.LANCZOS), (x, y))
        lb = draw_bottom_right_tag(face_draw, (14, top + 14, expression_width - 14, bottom - 14), entry["label"], font)
        face_placements[entry["name"]] = dict(
            source_info(path, subject),
            cell=[body_right, top, canvas.width, bottom],
            placed_box=[body_right + x, y, body_right + x + size[0], y + size[1]],
            label=entry["label"], label_box=[body_right + lb[0], lb[1], body_right + lb[2], lb[3]],
        )
    face_draw.line((0, 0, 0, height), fill="#222222", width=4)
    for y in (row_height, row_height * 2):
        face_draw.line((0, y, expression_width, y), fill="#222222", width=3)
    canvas.paste(column, (body_right, 0))

    anchor = None
    if "normal" in face_placements:
        anchor_path = asset_dir / config.get("identity_anchor", "identity-anchor.png")
        digest = hashlib.sha256(anchor_path.read_bytes()).hexdigest()
        if digest != face_placements["normal"]["source_sha256"]:
            raise ValueError("NORMAL must remain byte-identical to the identity anchor")
        anchor = {"source": str(anchor_path.resolve()), "source_sha256": digest}
    return canvas, {
        "layout_mode": "unmeasured", "canvas": list(canvas.size),
        "asset_dir": str(asset_dir.resolve()),
        "ruler": None, "body_data": [],
        "rendered_labels": [e["label"] for e in views + expressions],
        "alignment_y": [margin, height - margin],
        "body_views": placements, "expressions": face_placements,
        "identity_anchor": anchor,
        "asset_generation": "Reused accepted source assets; deterministic layout only.",
    }
