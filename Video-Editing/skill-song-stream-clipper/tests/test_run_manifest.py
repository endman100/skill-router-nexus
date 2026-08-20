from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_manifest.py"
SPEC = importlib.util.spec_from_file_location("run_manifest", SCRIPT)
assert SPEC and SPEC.loader
run_manifest = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = run_manifest
SPEC.loader.exec_module(run_manifest)


class RunManifestTests(unittest.TestCase):
    def test_initialize_contains_every_stage_and_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run_manifest.json"
            payload = run_manifest.initialize(path, "https://example.invalid/video")
            self.assertTrue(path.is_file())
            self.assertEqual(payload["workflow"], "skill-song-stream-clipper")
            self.assertEqual(tuple(payload["stages"]), run_manifest.STAGES)
            self.assertFalse(payload["evidence_policy"]["youtube_comments_allowed"])
            self.assertEqual(payload["defaults"]["codex"]["model"], "gpt-5.6-terra")
            self.assertEqual(
                payload["defaults"]["media_preparation"]["waveform_bucket_seconds"],
                0.02,
            )
            self.assertTrue(
                payload["defaults"]["end_boundary"][
                    "ranker_requires_generalization_evidence"
                ]
            )

    def test_record_updates_stage_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run_manifest.json"
            run_manifest.initialize(path, "source.mp4")
            payload = run_manifest.record(
                path,
                "asr",
                "completed",
                ["python asr.py", "python asr.py"],
                ["audio.wav"],
                ["phrases.csv"],
                ["BF16"],
            )
            entry = payload["stages"]["asr"]
            self.assertEqual(entry["status"], "completed")
            self.assertEqual(entry["commands"], ["python asr.py"])
            self.assertEqual(entry["outputs"], ["phrases.csv"])


if __name__ == "__main__":
    unittest.main()
