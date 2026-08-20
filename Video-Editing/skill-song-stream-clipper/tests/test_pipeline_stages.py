from __future__ import annotations

import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from array import array
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ASR_ROUTER_SCRIPTS = ROOT.parents[1] / "Speech-Recognition" / "asr-router" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(name: str):
    path = (ASR_ROUTER_SCRIPTS if name == "qwen3_asr" else SCRIPTS) / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PipelineStageTests(unittest.TestCase):
    def test_prepare_media_builds_normalized_streaming_waveform(self) -> None:
        prepare_media = load_script("prepare_media")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audio.wav"
            sample_rate = 1_000
            samples = array("h", [0] * 20 + [16_384] * 20)
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate)
                handle.writeframes(samples.tobytes())

            payload = prepare_media.analyze_waveform(path, bucket_seconds=0.02)

            self.assertEqual(payload["sample_rate"], sample_rate)
            self.assertEqual(payload["bucket_seconds"], 0.02)
            self.assertEqual(len(payload["rms"]), 2)
            self.assertAlmostEqual(payload["rms"][0], 0.0, places=6)
            self.assertAlmostEqual(payload["rms"][1], 0.5, places=3)
            self.assertTrue(payload["normalized"])

    def test_prepare_media_rejects_stale_master_from_another_source(self) -> None:
        prepare_media = load_script("prepare_media")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.mp4"
            destination = root / "run" / "source" / "master.mp4"
            source.write_bytes(b"new source")
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"stale source")

            with self.assertRaisesRegex(ValueError, "different source"):
                prepare_media.stage_master(source, destination, "link", force=False)

    def test_qwen_chunk_plan_has_complete_nonduplicated_retention(self) -> None:
        qwen = load_script("qwen3_asr")
        chunks = qwen.chunk_plan(500.0, 240.0, 15.0)

        self.assertEqual([row["start_seconds"] for row in chunks], [0.0, 225.0, 450.0])
        self.assertEqual(chunks[0]["retain_start_seconds"], 0.0)
        self.assertEqual(
            chunks[0]["retain_end_seconds"], chunks[1]["retain_start_seconds"]
        )
        self.assertEqual(
            chunks[1]["retain_end_seconds"], chunks[2]["retain_start_seconds"]
        )
        self.assertEqual(chunks[-1]["retain_end_seconds"], 500.0)

    def test_music_windows_are_averaged_by_timeline_position(self) -> None:
        detection = load_script("run_music_detection")
        rows = [
            {
                "window_start_seconds": "0",
                "window_end_seconds": "3",
                "music_probability": "0.9",
            },
            {
                "window_start_seconds": "1",
                "window_end_seconds": "4",
                "music_probability": "0.3",
            },
        ]

        averaged = detection.average_windows_by_second(rows, duration_seconds=4.0)

        self.assertEqual(
            [row["covering_window_count"] for row in averaged], [1, 2, 2, 1]
        )
        values = [float(row["avg_music_probability"]) for row in averaged]
        for actual, expected in zip(values, [0.9, 0.6, 0.6, 0.3], strict=True):
            self.assertTrue(math.isclose(actual, expected, abs_tol=1e-6))

    def test_runner_wires_production_stages_without_training(self) -> None:
        runner = load_script("run_pipeline")
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            stages = runner.build_stage_commands(
                video=Path(temporary) / "source.mp4",
                run_dir=run_dir,
                python_executable="python",
            )

        names = [stage.name for stage in stages]
        self.assertEqual(
            names,
            [
                "media_preparation",
                "asr",
                "music_detection",
                "song_discovery",
                "phrase_labeling",
                "interval_construction",
                "start_refinement",
                "end_refinement",
                "precision_cutting",
            ],
        )
        command_text = "\n".join(" ".join(stage.command) for stage in stages).lower()
        self.assertNotIn("train", command_text)
        self.assertNotIn("fit_", command_text)


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required"
)
class MediaPreparationIntegrationTests(unittest.TestCase):
    def test_prepare_media_cli_creates_master_audio_waveform_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.mp4"
            run_dir = root / "run"
            created = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=320x180:r=30:d=1.2",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=1.2",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(source),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_media.py"),
                    "--video",
                    str(source),
                    "--run-dir",
                    str(run_dir),
                    "--master-mode",
                    "copy",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((run_dir / "source" / "master.mp4").is_file())
            self.assertTrue((run_dir / "source" / "audio_16k_mono.wav").is_file())
            waveform = json.loads(
                (run_dir / "source" / "waveform_20ms.json").read_text(encoding="utf-8")
            )
            summary = json.loads(
                (run_dir / "media_preparation_summary.json").read_text(encoding="utf-8")
            )
            self.assertTrue(waveform["normalized"])
            self.assertGreater(len(waveform["rms"]), 50)
            self.assertEqual(summary["source_sha256"], summary["master_sha256"])


if __name__ == "__main__":
    unittest.main()
