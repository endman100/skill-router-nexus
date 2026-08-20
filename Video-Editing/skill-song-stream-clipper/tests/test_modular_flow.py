from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_script(name: str, *arguments: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *(str(value) for value in arguments)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required"
)
class ModularFlowIntegrationTests(unittest.TestCase):
    def test_artifacts_flow_from_phrase_labels_through_verified_clip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.mp4"
            run_dir = root / "run"
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
                    "color=c=black:s=320x180:r=10:d=50",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=50",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(source),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            prepared = run_script(
                "prepare_media.py",
                "--video",
                source,
                "--run-dir",
                run_dir,
                "--master-mode",
                "copy",
            )
            self.assertEqual(prepared.returncode, 0, prepared.stderr)

            phrases = root / "labeled_phrases.csv"
            phrase_rows = [
                {
                    "index": 0,
                    "start_seconds": 2.0,
                    "end_seconds": 3.0,
                    "text": "talk before",
                    "repaired_text": "talk before",
                    "song_label": "talk",
                    "label_confidence": 0.9,
                },
                {
                    "index": 1,
                    "start_seconds": 8.0,
                    "end_seconds": 18.0,
                    "text": "line one",
                    "repaired_text": "line one",
                    "song_label": "測試歌曲",
                    "label_confidence": 0.9,
                },
                {
                    "index": 2,
                    "start_seconds": 18.2,
                    "end_seconds": 28.2,
                    "text": "line two",
                    "repaired_text": "line two",
                    "song_label": "測試歌曲",
                    "label_confidence": 0.9,
                },
                {
                    "index": 3,
                    "start_seconds": 28.5,
                    "end_seconds": 38.0,
                    "text": "line three",
                    "repaired_text": "line three",
                    "song_label": "測試歌曲",
                    "label_confidence": 0.9,
                },
                {
                    "index": 4,
                    "start_seconds": 41.0,
                    "end_seconds": 42.0,
                    "text": "talk after",
                    "repaired_text": "talk after",
                    "song_label": "talk",
                    "label_confidence": 0.9,
                },
            ]
            write_csv(phrases, phrase_rows)
            words = root / "words.csv"
            write_csv(
                words,
                [
                    {
                        "index": row["index"],
                        "start_seconds": row["start_seconds"],
                        "end_seconds": row["end_seconds"],
                        "text": row["text"],
                    }
                    for row in phrase_rows
                ],
            )
            detection = root / "music_probability_avg_by_second.csv"
            write_csv(
                detection,
                [
                    {
                        "second_start": second,
                        "second_end": second + 1,
                        "avg_music_probability": (0.9 if 5 <= second < 39 else 0.1),
                    }
                    for second in range(50)
                ],
            )

            intervals_dir = run_dir / "intervals"
            intervals = run_script(
                "build_intervals.py",
                "--input-csv",
                phrases,
                "--music-detection-csv",
                detection,
                "--output-dir",
                intervals_dir,
            )
            self.assertEqual(intervals.returncode, 0, intervals.stderr)

            starts_dir = run_dir / "boundaries" / "starts"
            starts = run_script(
                "refine_starts.py",
                "--intervals-csv",
                intervals_dir / "song_intervals.csv",
                "--phrases-csv",
                phrases,
                "--detection-csv",
                detection,
                "--waveform-json",
                run_dir / "source" / "waveform_20ms.json",
                "--output-dir",
                starts_dir,
            )
            self.assertEqual(starts.returncode, 0, starts.stderr)

            ends_dir = run_dir / "boundaries" / "final"
            ends = run_script(
                "refine_ends.py",
                "--intervals-csv",
                starts_dir / "song_intervals_with_starts.csv",
                "--phrases-csv",
                phrases,
                "--words-csv",
                words,
                "--detection-csv",
                detection,
                "--source-video",
                run_dir / "source" / "master.mp4",
                "--output-dir",
                ends_dir,
            )
            self.assertEqual(ends.returncode, 0, ends.stderr)

            clips_dir = run_dir / "clips"
            cut = run_script(
                "cut_clips.py",
                "--video",
                run_dir / "source" / "master.mp4",
                "--intervals",
                ends_dir / "song_cut_intervals.csv",
                "--output-dir",
                clips_dir,
                "--encoder",
                "libx264",
                "--workers",
                1,
            )
            self.assertEqual(cut.returncode, 0, cut.stdout + cut.stderr)
            summary = json.loads(
                (clips_dir / "summary.json").read_text(encoding="utf-8")
            )
            with (clips_dir / "clip_manifest.csv").open(
                encoding="utf-8-sig", newline=""
            ) as handle:
                manifest = list(csv.DictReader(handle))
            self.assertEqual(summary["verified"], 1)
            self.assertEqual(manifest[0]["status"], "verified")
            self.assertTrue(Path(manifest[0]["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
