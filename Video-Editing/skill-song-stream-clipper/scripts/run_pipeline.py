from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import run_manifest
from codex_runtime import DEFAULT_CODEX_MODEL, DEFAULT_SERVICE_TIER


@dataclass(frozen=True)
class StageSpec:
    name: str
    command: list[str]
    inputs: tuple[Path, ...]
    outputs: tuple[Path, ...]


def build_stage_commands(
    *,
    video: Path,
    run_dir: Path,
    python_executable: str,
    codex_model: str = DEFAULT_CODEX_MODEL,
    service_tier: str = DEFAULT_SERVICE_TIER,
    music_precision: str = "bf16",
    encoder: str = "auto",
    ranker_model: Path | None = None,
    ranker_metadata: Path | None = None,
) -> list[StageSpec]:
    scripts = Path(__file__).resolve().parent
    video = video.resolve()
    run_dir = run_dir.resolve()
    suffix = video.suffix.lower() or ".mp4"
    master = run_dir / "source" / f"master{suffix}"
    audio = run_dir / "source" / "audio_16k_mono.wav"
    waveform = run_dir / "source" / "waveform_20ms.json"
    asr_dir = run_dir / "asr"
    phrases = asr_dir / "qwen3_full_asr_phrases.csv"
    words = asr_dir / "qwen3_full_asr_words.csv"
    music_dir = run_dir / "music_detection"
    probabilities = music_dir / "music_probability_avg_by_second.csv"
    discovery_dir = run_dir / "song_discovery"
    labels = discovery_dir / "labels.txt"
    labeling_dir = run_dir / "phrase_labels"
    labeled_phrases = labeling_dir / "labeled_phrases.csv"
    intervals_dir = run_dir / "intervals"
    intervals = intervals_dir / "song_intervals.csv"
    starts_dir = run_dir / "boundaries" / "starts"
    intervals_with_starts = starts_dir / "song_intervals_with_starts.csv"
    ends_dir = run_dir / "boundaries" / "final"
    final_intervals = ends_dir / "song_cut_intervals.csv"
    clips_dir = run_dir / "clips"

    stages = [
        StageSpec(
            name="media_preparation",
            command=[
                python_executable,
                str(scripts / "prepare_media.py"),
                "--video",
                str(video),
                "--run-dir",
                str(run_dir),
            ],
            inputs=(video,),
            outputs=(
                run_dir / "media_preparation_summary.json",
                master,
                audio,
                waveform,
            ),
        ),
        StageSpec(
            name="asr",
            command=[
                python_executable,
                str(scripts / "validate_asr_artifacts.py"),
                "--asr-dir",
                str(asr_dir),
            ],
            inputs=(audio, phrases, words),
            outputs=(phrases, words, asr_dir / "qwen3_asr_run_summary.json"),
        ),
        StageSpec(
            name="music_detection",
            command=[
                python_executable,
                str(scripts / "run_music_detection.py"),
                "--audio",
                str(audio),
                "--output-dir",
                str(music_dir),
                "--window-seconds",
                "3",
                "--hop-seconds",
                "1",
                "--precision",
                music_precision,
            ],
            inputs=(audio,),
            outputs=(
                music_dir / "music_probability_windows.csv",
                probabilities,
                music_dir / "music_detection_summary.json",
            ),
        ),
        StageSpec(
            name="song_discovery",
            command=[
                python_executable,
                str(scripts / "discover_songs.py"),
                "--input-csv",
                str(phrases),
                "--output-dir",
                str(discovery_dir),
                "--workdir",
                str(run_dir),
                "--model",
                codex_model,
                "--service-tier",
                service_tier,
                "--reasoning-effort",
                "high",
            ],
            inputs=(phrases,),
            outputs=(
                discovery_dir / "discovered_song_titles.csv",
                labels,
                discovery_dir / "summary.json",
            ),
        ),
        StageSpec(
            name="phrase_labeling",
            command=[
                python_executable,
                str(scripts / "label_phrases.py"),
                "--input-csv",
                str(phrases),
                "--labels-file",
                str(labels),
                "--output-dir",
                str(labeling_dir),
                "--workdir",
                str(run_dir),
                "--model",
                codex_model,
                "--service-tier",
                service_tier,
                "--reasoning-effort",
                "medium",
            ],
            inputs=(phrases, labels),
            outputs=(labeled_phrases, labeling_dir / "summary.json"),
        ),
        StageSpec(
            name="interval_construction",
            command=[
                python_executable,
                str(scripts / "build_intervals.py"),
                "--input-csv",
                str(labeled_phrases),
                "--music-detection-csv",
                str(probabilities),
                "--output-dir",
                str(intervals_dir),
            ],
            inputs=(labeled_phrases, probabilities),
            outputs=(intervals, intervals_dir / "summary.json"),
        ),
        StageSpec(
            name="start_refinement",
            command=[
                python_executable,
                str(scripts / "refine_starts.py"),
                "--intervals-csv",
                str(intervals),
                "--phrases-csv",
                str(labeled_phrases),
                "--detection-csv",
                str(probabilities),
                "--waveform-json",
                str(waveform),
                "--output-dir",
                str(starts_dir),
            ],
            inputs=(intervals, labeled_phrases, probabilities, waveform),
            outputs=(intervals_with_starts, starts_dir / "summary.json"),
        ),
        StageSpec(
            name="end_refinement",
            command=[
                python_executable,
                str(scripts / "refine_ends.py"),
                "--intervals-csv",
                str(intervals_with_starts),
                "--phrases-csv",
                str(labeled_phrases),
                "--words-csv",
                str(words),
                "--detection-csv",
                str(probabilities),
                "--source-video",
                str(master),
                "--output-dir",
                str(ends_dir),
            ],
            inputs=(
                intervals_with_starts,
                labeled_phrases,
                words,
                probabilities,
                master,
            ),
            outputs=(final_intervals, ends_dir / "summary.json"),
        ),
        StageSpec(
            name="precision_cutting",
            command=[
                python_executable,
                str(scripts / "cut_clips.py"),
                "--video",
                str(master),
                "--intervals",
                str(final_intervals),
                "--output-dir",
                str(clips_dir),
                "--encoder",
                encoder,
            ],
            inputs=(master, final_intervals),
            outputs=(clips_dir / "clip_manifest.csv", clips_dir / "summary.json"),
        ),
    ]
    if ranker_model and ranker_metadata:
        end_stage = stages[7]
        stages[7] = StageSpec(
            name=end_stage.name,
            command=[
                *end_stage.command,
                "--ranker-model",
                str(ranker_model.resolve()),
                "--ranker-metadata",
                str(ranker_metadata.resolve()),
            ],
            inputs=(
                *end_stage.inputs,
                ranker_model.resolve(),
                ranker_metadata.resolve(),
            ),
            outputs=end_stage.outputs,
        )
    elif ranker_model or ranker_metadata:
        raise ValueError("Provide both ranker model and metadata")
    return stages


def selected_stages(
    stages: Sequence[StageSpec],
    start: str | None,
    stop: str | None,
) -> list[StageSpec]:
    names = [stage.name for stage in stages]
    first = names.index(start) if start else 0
    last = names.index(stop) + 1 if stop else len(stages)
    if first >= last:
        raise ValueError("--from-stage must not come after --stop-after")
    return list(stages[first:last])


def outputs_exist(stage: StageSpec) -> bool:
    return all(path.exists() for path in stage.outputs)


def command_text(command: Sequence[str]) -> str:
    return subprocess.list2cmdline(list(command))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the modular production song-stream clipping pipeline."
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--codex-model", default=DEFAULT_CODEX_MODEL)
    parser.add_argument("--service-tier", default=DEFAULT_SERVICE_TIER)
    parser.add_argument(
        "--music-precision", choices=("bf16", "fp16", "fp32"), default="bf16"
    )
    parser.add_argument(
        "--encoder", choices=("auto", "h264_nvenc", "libx264"), default="auto"
    )
    parser.add_argument("--ranker-model", type=Path)
    parser.add_argument("--ranker-metadata", type=Path)
    parser.add_argument("--from-stage", choices=run_manifest.STAGES[:-1])
    parser.add_argument("--stop-after", choices=run_manifest.STAGES[:-1])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video = args.video.resolve()
    run_dir = args.run_dir.resolve()
    if not video.is_file() and not args.dry_run:
        raise FileNotFoundError(video)
    stages = build_stage_commands(
        video=video,
        run_dir=run_dir,
        python_executable=args.python,
        codex_model=args.codex_model,
        service_tier=args.service_tier,
        music_precision=args.music_precision,
        encoder=args.encoder,
        ranker_model=args.ranker_model,
        ranker_metadata=args.ranker_metadata,
    )
    stages = selected_stages(stages, args.from_stage, args.stop_after)
    if args.dry_run:
        print(
            json.dumps(
                [
                    {
                        "stage": stage.name,
                        "command": stage.command,
                        "outputs": [str(path) for path in stage.outputs],
                    }
                    for stage in stages
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    manifest = run_dir / "run_manifest.json"
    if not manifest.exists():
        run_manifest.initialize(manifest, str(video))
    for stage in stages:
        if args.resume and outputs_exist(stage):
            run_manifest.record(
                manifest,
                stage.name,
                "skipped",
                [],
                [str(path) for path in stage.inputs],
                [str(path) for path in stage.outputs],
                ["resume: all declared outputs already exist"],
            )
            print(f"SKIP {stage.name}", flush=True)
            continue
        run_manifest.record(
            manifest,
            stage.name,
            "running",
            [command_text(stage.command)],
            [str(path) for path in stage.inputs],
            [],
            [],
        )
        print(f"RUN {stage.name}", flush=True)
        result = subprocess.run(stage.command, check=False)
        if result.returncode != 0:
            run_manifest.record(
                manifest,
                stage.name,
                "failed",
                [],
                [],
                [],
                [f"exit_code={result.returncode}"],
            )
            return result.returncode
        missing = [str(path) for path in stage.outputs if not path.exists()]
        if missing:
            run_manifest.record(
                manifest,
                stage.name,
                "failed",
                [],
                [],
                [],
                [f"missing outputs: {missing}"],
            )
            raise FileNotFoundError(f"{stage.name} did not create: {missing}")
        run_manifest.record(
            manifest,
            stage.name,
            "completed",
            [],
            [],
            [str(path) for path in stage.outputs],
            [],
        )
        if stage.name == "precision_cutting":
            run_manifest.record(
                manifest,
                "clip_verification",
                "completed",
                [],
                [str(stage.outputs[0])],
                [str(stage.outputs[1])],
                ["cut_clips.py probes every output before returning success"],
            )
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
