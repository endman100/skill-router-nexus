from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def test_ranker_training_is_separate_from_production_pipeline(self) -> None:
        pipeline = (ROOT / "references" / "pipeline.md").read_text(encoding="utf-8")
        training = (ROOT / "references" / "end-boundary-ranker-training.md").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("ExtraTreesClassifier", pipeline)
        self.assertNotIn("min_samples_leaf", pipeline)
        self.assertNotIn("## 2. Collect Accepted End Ranges", pipeline)
        self.assertIn("## 2. Collect Accepted End Ranges", training)
        self.assertIn("ExtraTreesClassifier", training)

    def test_production_pipeline_has_no_ui_stage(self) -> None:
        pipeline = (ROOT / "references" / "pipeline.md").read_text(encoding="utf-8")

        self.assertNotIn("## 9. Inspection UI", pipeline)
        self.assertNotIn("## 9. Annotation UI", pipeline)
        self.assertIn("## 9. Precision Cutting", pipeline)

    def test_mv_lite_contract_disables_zoom_and_image_correction(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        pipeline = (ROOT / "references" / "pipeline.md").read_text(encoding="utf-8")

        self.assertIn("dynamic_zoom=false", pipeline)
        self.assertIn("Do not apply brightness, contrast, gamma", pipeline)
        self.assertIn("No color or tonal correction filter", skill)

    def test_modular_production_scripts_are_documented_and_present(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        pipeline = (ROOT / "references" / "pipeline.md").read_text(encoding="utf-8")
        scripts = [
            "prepare_media.py",
            "validate_asr_artifacts.py",
            "run_music_detection.py",
            "discover_songs.py",
            "label_phrases.py",
            "build_intervals.py",
            "refine_starts.py",
            "refine_ends.py",
            "run_pipeline.py",
            "cut_clips.py",
        ]

        self.assertIn("scripts/run_pipeline.py", skill)
        for script in scripts:
            self.assertTrue((ROOT / "scripts" / script).is_file(), script)
            self.assertIn(script, pipeline)

        router_schema = ROOT.parents[1] / "Speech-Recognition" / "asr-router" / "references" / "schema.md"
        self.assertTrue(router_schema.is_file())
        self.assertIn("`asr-router` (Agent boundary)", pipeline)

        runner = (ROOT / "scripts" / "run_pipeline.py").read_text(encoding="utf-8")
        self.assertNotIn("fit_end", runner)
        self.assertNotIn("train_ranker", runner)
        self.assertNotIn("locate_qwen", runner)

    def test_optional_mv_lite_scripts_are_documented_and_present(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        pipeline = (ROOT / "references" / "pipeline.md").read_text(encoding="utf-8")

        for script in ["render_mv_lite.py", "audit_mv_lite.py"]:
            self.assertTrue((ROOT / "scripts" / script).is_file(), script)
            self.assertIn(script, skill)
            self.assertIn(script, pipeline)

        self.assertIn("existing song intervals and phrase labels", pipeline)
        self.assertIn("does not call Codex", pipeline)


if __name__ == "__main__":
    unittest.main()
