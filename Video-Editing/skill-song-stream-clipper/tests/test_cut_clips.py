from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cut_clips.py"
SPEC = importlib.util.spec_from_file_location("cut_clips", SCRIPT)
assert SPEC and SPEC.loader
cut_clips = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cut_clips
SPEC.loader.exec_module(cut_clips)


class CutClipUnitTests(unittest.TestCase):
    def test_safe_filename_removes_windows_reserved_characters(self) -> None:
        self.assertEqual(cut_clips.safe_filename('A: B/C?* | D'), "A_B_C_D")

    def test_timestamp_is_millisecond_stable(self) -> None:
        self.assertEqual(cut_clips.filename_timestamp(3661.234), "01h01m01s234")

    def test_rejects_duplicate_interval_numbers(self) -> None:
        specs = [
            cut_clips.ClipSpec(1, "A", 0.0, 1.0),
            cut_clips.ClipSpec(1, "B", 1.0, 2.0),
        ]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            cut_clips.validate_specs(specs, duration=3.0, tolerance=0.1)

    def test_rejects_interval_after_source(self) -> None:
        specs = [cut_clips.ClipSpec(1, "A", 0.0, 4.0)]
        with self.assertRaisesRegex(ValueError, "after source duration"):
            cut_clips.validate_specs(specs, duration=3.0, tolerance=0.1)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class CutClipIntegrationTests(unittest.TestCase):
    def test_cli_cuts_and_verifies_two_clips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.mp4"
            intervals = root / "intervals.csv"
            output = root / "clips"
            create = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=blue:s=320x180:r=30:d=4",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=4",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(source),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            with intervals.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "interval_no",
                        "song_label",
                        "cut_start_seconds",
                        "cut_end_seconds",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "interval_no": 1,
                            "song_label": "First Song",
                            "cut_start_seconds": 0.25,
                            "cut_end_seconds": 1.75,
                        },
                        {
                            "interval_no": 2,
                            "song_label": "Second Song",
                            "cut_start_seconds": 2.0,
                            "cut_end_seconds": 3.5,
                        },
                    ]
                )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--video",
                    str(source),
                    "--intervals",
                    str(intervals),
                    "--output-dir",
                    str(output),
                    "--encoder",
                    "libx264",
                    "--workers",
                    "1",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            with (output / "summary.json").open(encoding="utf-8") as handle:
                summary = json.load(handle)
            self.assertEqual(summary["requested"], 2)
            self.assertEqual(summary["verified"], 2)
            self.assertEqual(len(list(output.glob("*.mp4"))), 2)


if __name__ == "__main__":
    unittest.main()
