from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RefineBoundaryTests(unittest.TestCase):
    def test_start_selects_latest_qualifying_local_trough(self) -> None:
        starts = load_script("refine_starts")
        values = np.asarray([1.0, 0.20, 1.0, 0.10, 1.0], dtype=np.float64)

        choice = starts.choose_local_volume_trough(
            values,
            bucket_seconds=1.0,
            search=starts.Span(0.0, 4.0),
            percentile=50.0,
        )

        self.assertEqual(choice["mode"], "nearest_low_local_trough")
        self.assertEqual(choice["selected"], 3.5)

    def test_end_selects_earliest_stable_non_music_run(self) -> None:
        ends = load_script("refine_ends")
        probabilities = [
            {
                "second_start": second,
                "second_end": second + 1,
                "avg_music_probability": "0.1" if 10 <= second < 15 else "0.9",
            }
            for second in range(20)
        ]

        choice = ends.choose_boundary(
            boundary="end",
            search=ends.Span(10.0, 20.0),
            per_second_rows=probabilities,
            blocks=[],
            threshold=0.35,
            consecutive_seconds=2,
            plateau_margin_seconds=0.5,
            min_safe_gap_seconds=0.6,
        )

        self.assertEqual(choice["mode"], "stable_non_music_token_safe")
        self.assertAlmostEqual(choice["selected"], 12.5)

    def test_unvalidated_ranker_metadata_is_rejected(self) -> None:
        ends = load_script("refine_ends")
        compatible, reason = ends.ranker_metadata_is_compatible(
            {
                "schema_version": 1,
                "generalization_claim": False,
                "strategy": {"features": list(ends.FEATURE_NAMES)},
            }
        )

        self.assertFalse(compatible)
        self.assertIn("generalization", reason)

    def test_ranker_candidates_start_after_last_lyric(self) -> None:
        ends = load_script("refine_ends")

        candidates = ends.build_candidate_times(
            raw_end=10.0,
            next_song_start=11.0,
            search_seconds=30.0,
            step_seconds=0.25,
        )

        self.assertEqual(candidates[0], 10.25)


if __name__ == "__main__":
    unittest.main()
