from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_intervals.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("build_intervals", SCRIPT)
assert SPEC and SPEC.loader
build_intervals = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_intervals
SPEC.loader.exec_module(build_intervals)


def detection_rows(duration: int, probability: float) -> list[dict[str, str]]:
    return [
        {
            "second_start": str(second),
            "second_end": str(second + 1),
            "avg_music_probability": str(probability),
        }
        for second in range(duration)
    ]


class BuildIntervalsTests(unittest.TestCase):
    def test_short_or_two_phrase_song_run_is_relabelled_to_talk(self) -> None:
        rows = [
            {
                "index": "0",
                "start_seconds": "0",
                "end_seconds": "12",
                "song_label": "短歌",
            },
            {
                "index": "1",
                "start_seconds": "13",
                "end_seconds": "25",
                "song_label": "短歌",
            },
            {
                "index": "2",
                "start_seconds": "26",
                "end_seconds": "30",
                "song_label": "talk",
            },
        ]

        filtered, rejected = build_intervals.suppress_short_song_runs(
            rows,
            label_key="song_label",
            talk_label="talk",
            start_column="start_seconds",
            end_column="end_seconds",
            min_song_run_duration_seconds=30.0,
            min_song_run_phrase_rows=3,
        )

        self.assertEqual(
            [row["song_label"] for row in filtered], ["talk", "talk", "talk"]
        )
        self.assertEqual(len(rejected), 1)
        self.assertIn("duration_lt_min", rejected[0]["rejected_reasons"])
        self.assertIn("phrase_rows_lt_min", rejected[0]["rejected_reasons"])

    def test_same_song_runs_merge_across_short_pause(self) -> None:
        strict_runs = [
            {
                "strict_run_no": 1,
                "song_label": "同一首歌",
                "start_seconds": "0",
                "end_seconds": "40",
                "first_phrase_index": "0",
                "last_phrase_index": "2",
                "phrase_rows": 3,
                "mean_label_confidence": "0.9",
                "min_label_confidence": "0.8",
            },
            {
                "strict_run_no": 2,
                "song_label": "同一首歌",
                "start_seconds": "45",
                "end_seconds": "85",
                "first_phrase_index": "4",
                "last_phrase_index": "6",
                "phrase_rows": 3,
                "mean_label_confidence": "0.9",
                "min_label_confidence": "0.8",
            },
        ]

        intervals = build_intervals.build_final_intervals(
            strict_runs,
            detection_rows=detection_rows(90, 0.8),
            same_label_pause_seconds=15.0,
            music_continuity_threshold=0.5,
            music_continuity_mean_threshold=0.6,
            max_music_interrupt_seconds=2.0,
        )

        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0]["strict_runs_merged"], 2)

    def test_different_song_titles_do_not_merge_from_music_alone(self) -> None:
        base = {
            "first_phrase_index": "0",
            "last_phrase_index": "2",
            "phrase_rows": 3,
            "mean_label_confidence": "0.9",
            "min_label_confidence": "0.8",
        }
        strict_runs = [
            {
                **base,
                "strict_run_no": 1,
                "song_label": "甲",
                "start_seconds": "0",
                "end_seconds": "40",
            },
            {
                **base,
                "strict_run_no": 2,
                "song_label": "乙",
                "start_seconds": "42",
                "end_seconds": "82",
            },
        ]

        intervals = build_intervals.build_final_intervals(
            strict_runs,
            detection_rows=detection_rows(90, 0.95),
            same_label_pause_seconds=15.0,
            music_continuity_threshold=0.5,
            music_continuity_mean_threshold=0.6,
            max_music_interrupt_seconds=2.0,
        )

        self.assertEqual([row["song_label"] for row in intervals], ["甲", "乙"])

    def test_low_mean_music_interval_is_rejected(self) -> None:
        intervals = [
            {
                "interval_no": 1,
                "song_label": "清唱",
                "start_seconds": "0",
                "end_seconds": "40",
            }
        ]

        kept, rejected, _ = build_intervals.filter_intervals_by_music_probability(
            intervals,
            detection_rows(40, 0.4),
            min_mean_music_probability=0.6,
        )

        self.assertEqual(kept, [])
        self.assertEqual(len(rejected), 1)

    def test_incomplete_music_timeline_is_rejected(self) -> None:
        intervals = [
            {
                "interval_no": 1,
                "song_label": "覆蓋不完整",
                "start_seconds": "0",
                "end_seconds": "40",
            }
        ]

        kept, rejected, _ = build_intervals.filter_intervals_by_music_probability(
            intervals,
            detection_rows(1, 0.95),
            min_mean_music_probability=0.6,
        )

        self.assertEqual(kept, [])
        self.assertEqual(
            rejected[0]["rejected_reason"], "music_probability_coverage_incomplete"
        )


if __name__ == "__main__":
    unittest.main()
