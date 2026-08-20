from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CodexStageTests(unittest.TestCase):
    def test_song_discovery_uses_fixed_three_minute_windows(self) -> None:
        discovery = load_script("discover_songs")
        rows = [
            {"index": "0", "start_seconds": "10", "end_seconds": "20", "text": "A"},
            {"index": "1", "start_seconds": "179", "end_seconds": "181", "text": "B"},
            {"index": "2", "start_seconds": "359", "end_seconds": "361", "text": "C"},
        ]

        windows = discovery.build_windows(
            rows,
            text_column="text",
            start_column="start_seconds",
            end_column="end_seconds",
            window_seconds=180.0,
        )

        self.assertEqual(len(windows), 3)
        self.assertEqual(
            [row["window_start_seconds"] for row in windows],
            ["0.000", "180.000", "360.000"],
        )

    def test_phrase_validation_requires_one_allowed_label_per_input_row(self) -> None:
        labeling = load_script("label_phrases")
        rows = [
            {"index": "0", "start_seconds": "0", "end_seconds": "1", "text": "A"},
            {"index": "1", "start_seconds": "1", "end_seconds": "2", "text": "B"},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "labels.jsonl"
            output.write_text(
                "\n".join(
                    json.dumps(item, ensure_ascii=False)
                    for item in [
                        {"index": "0", "song_label": "talk"},
                        {"index": "1", "song_label": "unknown_song"},
                    ]
                ),
                encoding="utf-8",
            )
            valid, reason = labeling.validate_jsonl(
                path=output,
                input_rows=rows,
                labels={"talk", "歌曲甲"},
                id_column="index",
                label_key="song_label",
            )

        self.assertFalse(valid)
        self.assertIn("bad label", reason)

    def test_labels_file_must_be_talk_plus_concrete_titles(self) -> None:
        labeling = load_script("label_phrases")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "labels.txt"
            path.write_text("talk\n歌曲甲\nlyric\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "forbidden"):
                labeling.read_allowed_labels(path)


if __name__ == "__main__":
    unittest.main()
