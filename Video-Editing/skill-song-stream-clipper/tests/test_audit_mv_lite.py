from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_mv_lite.py"


def load_module():
    if not SCRIPT.exists():
        raise AssertionError(f"Missing auditor: {SCRIPT}")
    spec = importlib.util.spec_from_file_location("audit_mv_lite", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AuditMvLiteTests(unittest.TestCase):
    def test_sample_positions_stay_inside_clip(self) -> None:
        auditor = load_module()
        positions = auditor.sample_positions(100.0)

        self.assertEqual(len(positions), 3)
        self.assertTrue(all(0.0 <= value <= 98.0 for value in positions))
        self.assertEqual(positions, sorted(positions))

    def test_subtitle_audit_detects_overlap_and_invalid_intervals(self) -> None:
        auditor = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "lyrics.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["relative_start", "relative_end", "text"],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {"relative_start": 1.0, "relative_end": 3.0, "text": "one"},
                        {"relative_start": 2.5, "relative_end": 4.0, "text": "two"},
                        {"relative_start": 9.0, "relative_end": 11.0, "text": "bad"},
                    ]
                )

            result = auditor.subtitle_audit(path, expected_duration=10.0)

        self.assertEqual(result["overlap_count"], 1)
        self.assertEqual(result["invalid_interval_count"], 1)

    def test_pass_gate_requires_core_checks(self) -> None:
        auditor = load_module()
        report = {
            "checks": {
                "duration_error_seconds": 0.01,
                "has_video": True,
                "has_audio": True,
                "resolution_ok": True,
                "fps_ok": True,
                "audio_rate_ok": True,
                "dynamic_zoom": False,
                "image_correction": "none",
            },
            "audio_alignment": [
                {"absolute_lag_seconds": 0.005, "normalized_correlation": 0.99}
            ],
            "subtitles": {"overlap_count": 0, "invalid_interval_count": 0},
            "motion": {"all_sampled_frames_identical": False},
            "black_frames": {"black_event_count": 0},
        }

        self.assertTrue(auditor.passes_core_gate(report))
        report["checks"]["image_correction"] = "contrast"
        self.assertFalse(auditor.passes_core_gate(report))


if __name__ == "__main__":
    unittest.main()
