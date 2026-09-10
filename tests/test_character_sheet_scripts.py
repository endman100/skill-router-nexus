import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Image-Generation" / "character-sheet" / "scripts"


def make_subject(path: Path, size: tuple[int, int], box: tuple[int, int, int, int]) -> None:
    image = Image.new("RGB", size, "white")
    ImageDraw.Draw(image).rectangle(box, fill="black")
    image.save(path)


def test_verifier_accepts_valid_sheet_with_wide_body_views(tmp_path: Path) -> None:
    for filename in ("front.png", "profile.png", "back.png"):
        make_subject(tmp_path / filename, (300, 1600), (60, 0, 235, 1599))
    for filename in ("expression-1.png", "expression-2.png", "expression-3.png"):
        make_subject(tmp_path / filename, (300, 400), (60, 20, 240, 380))

    config = {
        "layout_mode": "measured",
        "height_cm": 160.0,
        "height_source": "default",
        "body_data": [],
        "views": [
            {"name": "front", "file": "front.png", "label": "FRONT"},
            {"name": "profile", "file": "profile.png", "label": "LEFT PROFILE"},
            {"name": "back", "file": "back.png", "label": "BACK"},
        ],
        "expressions": [
            {"name": "neutral", "file": "expression-1.png", "label": "NEUTRAL"},
            {"name": "smile", "file": "expression-2.png", "label": "SMILE"},
            {"name": "displeased", "file": "expression-3.png", "label": "DISPLEASED"},
        ],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    output_path = tmp_path / "sheet.png"
    manifest_path = tmp_path / "sheet.manifest.json"

    compose = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "compose_turnaround_sheet.py"),
            str(tmp_path),
            str(output_path),
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
    )
    assert compose.returncode == 0, compose.stderr

    verify = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "verify_turnaround_sheet.py"),
            str(output_path),
            str(manifest_path),
        ],
        capture_output=True,
        text=True,
    )
    assert verify.returncode == 0, verify.stderr
