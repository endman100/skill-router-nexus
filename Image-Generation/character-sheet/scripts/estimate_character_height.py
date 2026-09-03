"""Resolve height from explicit metric evidence or an explicit design prior."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def number(value: Any, name: str, minimum: float | None = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean")
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f"Invalid {name}: {value}")
    return result


def resolve(data: dict[str, Any]) -> dict[str, Any]:
    mode = data.get("mode")
    reason = data.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("An explicit reason/evidence description is required")
    result: dict[str, Any] = {
        "schema_version": 2, "mode": mode, "reason": reason,
        "height_cm": None, "height_source": None,
        "physical_height_cm": None, "physical_height_interval_cm": None,
        "reference_kind": data.get("reference_kind"),
    }
    landmarks = data.get("landmarks")
    body_span = None
    if landmarks is not None:
        top = number(landmarks["top_y"], "top_y")
        sole = number(landmarks["sole_y"], "sole_y")
        if sole <= top:
            raise ValueError("Expected top_y < sole_y")
        body_span = sole - top
        result.update(landmarks=dict(landmarks), body_span_px=body_span)
        if "chin_y" in landmarks:
            chin = number(landmarks["chin_y"], "chin_y")
            if not top < chin < sole:
                raise ValueError("Expected top_y < chin_y < sole_y")
            result["head_count"] = round(body_span / (chin - top), 6)
            result["head_count_role"] = "Dimensionless style descriptor; never a cm conversion."
    if mode == "unresolved":
        result["confidence"] = "unresolved"
        return result
    if mode == "design_prior":
        height = number(data["height_cm"], "height_cm", 0.000001)
        if height > 200:
            raise ValueError("Selected height exceeds the sheet's 200 cm ruler")
        result.update(height_cm=height, height_source="design_prior", confidence="not_measured")
        return result
    if mode != "scale":
        raise ValueError("mode must be scale, design_prior, or unresolved")
    if data.get("reference_kind") != "original":
        raise ValueError("Generated assets cannot supply independent physical scale evidence")
    if data.get("geometry") not in {"equal_scale", "rectified"}:
        raise ValueError("Metric ratios require documented equal-scale or rectified geometry")
    if body_span is None:
        raise ValueError("Scale mode requires original top and sole landmarks")
    reference_px = number(data["reference_span_px"], "reference_span_px", 0.000001)
    reference_cm = number(data["reference_cm"], "reference_cm", 0.000001)
    pixel_error = number(data.get("pixel_error", 1), "pixel_error", 0)
    reference_error = number(data.get("reference_cm_error", 0), "reference_cm_error", 0)
    if min(body_span, reference_px) <= 2 * pixel_error or reference_cm <= reference_error:
        raise ValueError("Uncertainty consumes the measured span")
    height = body_span / reference_px * reference_cm
    low = (body_span - 2 * pixel_error) / (reference_px + 2 * pixel_error) * (reference_cm - reference_error)
    high = (body_span + 2 * pixel_error) / (reference_px - 2 * pixel_error) * (reference_cm + reference_error)
    result.update(
        height_cm=round(height, 2), height_source="scale",
        physical_height_cm=round(height, 2),
        physical_height_interval_cm=[round(low, 2), round(high, 2)],
        confidence="conditional_on_reference_and_geometry",
        reference_span_px=reference_px, reference_cm=reference_cm,
        reference_cm_error=reference_error, pixel_error=pixel_error,
        geometry=data["geometry"],
        endpoint_definition=data.get("endpoint_definition", "topmost visible subject to sole"),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    result = resolve(data)
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    for key in ("reference_file", "landmark_asset"):
        if data.get(key):
            path = Path(data[key])
            if not path.is_absolute():
                path = args.input.parent / path
            result[key] = {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
