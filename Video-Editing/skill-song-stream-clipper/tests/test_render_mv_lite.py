from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_mv_lite.py"


def load_module():
    if not SCRIPT.exists():
        raise AssertionError(f"Missing renderer: {SCRIPT}")
    spec = importlib.util.spec_from_file_location("render_mv_lite", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class RenderMvLiteTests(unittest.TestCase):
    def test_load_jobs_selects_song_rows_and_converts_traditional(self) -> None:
        renderer = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intervals = root / "intervals.csv"
            phrases = root / "phrases.csv"
            write_csv(
                intervals,
                [
                    {
                        "interval_no": 2,
                        "song_label": "愛情一首歌",
                        "source_song_labels": "爱情一首歌",
                        "cut_start_seconds": 10.0,
                        "cut_end_seconds": 50.0,
                    }
                ],
            )
            write_csv(
                phrases,
                [
                    {
                        "index": 1,
                        "start_seconds": 8.0,
                        "end_seconds": 9.0,
                        "song_label": "talk",
                        "repaired_text": "開始說話",
                    },
                    {
                        "index": 2,
                        "start_seconds": 15.0,
                        "end_seconds": 19.0,
                        "song_label": "爱情一首歌",
                        "repaired_text": "后来联系",
                    },
                    {
                        "index": 3,
                        "start_seconds": 21.0,
                        "end_seconds": 25.0,
                        "song_label": "爱情一首歌",
                        "repaired_text": "随风回来",
                    },
                ],
            )

            jobs = renderer.load_jobs(intervals, phrases, {2})

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "愛情一首歌")
        self.assertEqual(
            [event.text for event in jobs[0].lyrics], ["後來聯繫", "隨風回來"]
        )
        self.assertEqual(jobs[0].lyrics[0].relative_start, 5.0)
        self.assertEqual(jobs[0].duration, 40.0)

    def test_camera_keys_cover_clip_and_remain_monotonic(self) -> None:
        renderer = load_module()
        job = renderer.SongJob(
            interval_no=2,
            title="測試歌曲",
            clip_start=10.0,
            clip_end=80.0,
            lyrics=(
                renderer.LyricEvent(20.0, 25.0, "第一句", 10.0),
                renderer.LyricEvent(50.0, 55.0, "第二句", 10.0),
            ),
        )

        keys = renderer.build_camera_keys(job)

        self.assertEqual(keys[0].time_seconds, 0.0)
        self.assertEqual(keys[-1].time_seconds, job.duration)
        self.assertTrue(
            all(
                left.time_seconds < right.time_seconds
                for left, right in zip(keys, keys[1:])
            )
        )

    def test_filter_graph_uses_fixed_scale_xy_motion_without_color_correction(
        self,
    ) -> None:
        renderer = load_module()
        job = renderer.SongJob(
            interval_no=2,
            title="測試歌曲",
            clip_start=10.0,
            clip_end=80.0,
            lyrics=(renderer.LyricEvent(20.0, 25.0, "第一句", 10.0),),
        )
        graph = renderer.build_filter_graph(
            job=job,
            camera_keys=renderer.build_camera_keys(job),
            base_x=960.0,
            base_y=540.0,
            crop_width=1792,
            crop_height=1008,
            subtitle_path=Path("captions.ass"),
            fonts_dir=Path("fonts"),
        )

        self.assertIn("crop_w=1792:crop_h=1008", graph)
        self.assertIn("ass=filename=", graph)
        self.assertNotIn("brightness", graph)
        self.assertNotIn("contrast", graph)
        self.assertNotIn("saturation", graph)
        self.assertNotIn("gamma", graph)
        self.assertNotIn("zoompan", graph)

    def test_subtitle_wrapping_keeps_all_text(self) -> None:
        renderer = load_module()
        source = "這是一句很長而且需要完整顯示不能截斷的字幕文字"

        wrapped = renderer.wrap_subtitle_text(source, max_columns=12)

        self.assertEqual(wrapped.replace(r"\N", ""), source)
        self.assertIn(r"\N", wrapped)

    def test_reuse_output_rejects_an_unprobeable_partial_file(self) -> None:
        renderer = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "partial.mp4"
            output.write_bytes(b"not a complete MP4")

            reusable = renderer.can_reuse_output(output, expected_duration=10.0)

        self.assertFalse(reusable)


if __name__ == "__main__":
    unittest.main()
