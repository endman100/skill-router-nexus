from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np

from pipeline_utils import probe_media, sha256_file


def analyze_waveform(
    wav_path: Path,
    *,
    bucket_seconds: float = 0.02,
    buckets_per_block: int = 10_000,
) -> dict[str, Any]:
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be positive")
    with wave.open(str(wav_path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        frame_count = handle.getnframes()
        if channels != 1 or sample_width != 2:
            raise ValueError("Waveform analysis requires mono 16-bit PCM WAV")
        frames_per_bucket = max(1, int(round(sample_rate * bucket_seconds)))
        read_frames = frames_per_bucket * max(1, buckets_per_block)
        pending = np.empty(0, dtype=np.int16)
        rms_values: list[float] = []
        peak_values: list[float] = []
        while True:
            raw = handle.readframes(read_frames)
            if not raw:
                break
            samples = np.frombuffer(raw, dtype="<i2")
            if pending.size:
                samples = np.concatenate((pending, samples))
            full_buckets = samples.size // frames_per_bucket
            if full_buckets:
                split = full_buckets * frames_per_bucket
                matrix = (
                    samples[:split]
                    .reshape(full_buckets, frames_per_bucket)
                    .astype(np.float64)
                )
                rms_values.extend(
                    (np.sqrt(np.mean(np.square(matrix), axis=1)) / 32768.0).tolist()
                )
                peak_values.extend((np.max(np.abs(matrix), axis=1) / 32768.0).tolist())
                pending = samples[split:].copy()
            else:
                pending = samples.copy()
        if pending.size:
            values = pending.astype(np.float64)
            rms_values.append(float(np.sqrt(np.mean(np.square(values))) / 32768.0))
            peak_values.append(float(np.max(np.abs(values)) / 32768.0))

    return {
        "schema_version": 1,
        "audio": str(wav_path.resolve()),
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "duration_seconds": frame_count / sample_rate,
        "bucket_seconds": frames_per_bucket / sample_rate,
        "normalized": True,
        "normalization_divisor": 32768.0,
        "rms": rms_values,
        "peak": peak_values,
    }


def stage_master(source: Path, destination: Path, mode: str, force: bool) -> Path:
    source = source.resolve()
    if mode == "reference":
        return source
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not force:
            try:
                same_file = os.path.samefile(source, destination)
            except OSError:
                same_file = False
            same_content = (
                source.stat().st_size == destination.stat().st_size
                and sha256_file(source) == sha256_file(destination)
            )
            if same_file or same_content:
                return destination.resolve()
            raise ValueError(
                f"Staged master belongs to a different source: {destination}"
            )
        destination.unlink()
    if mode == "copy":
        shutil.copy2(source, destination)
    elif mode == "link":
        try:
            os.link(source, destination)
        except OSError:
            shutil.copy2(source, destination)
    else:
        raise ValueError(f"Unknown master mode: {mode}")
    return destination.resolve()


def extract_audio(video: Path, output: Path, force: bool) -> None:
    if output.exists() and not force:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output),
    ]
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage a source master and derive 16 kHz mono audio plus a 20 ms RMS waveform."
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--master-mode",
        choices=("link", "copy", "reference"),
        default="link",
    )
    parser.add_argument("--bucket-seconds", type=float, default=0.02)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise FileNotFoundError("ffmpeg and ffprobe must be available on PATH")
    source = args.video.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    run_dir = args.run_dir.resolve()
    source_dir = run_dir / "source"
    suffix = source.suffix.lower() or ".mp4"
    master = stage_master(
        source,
        source_dir / f"master{suffix}",
        args.master_mode,
        args.force,
    )
    audio = source_dir / "audio_16k_mono.wav"
    waveform_path = source_dir / "waveform_20ms.json"
    extract_audio(master, audio, args.force)
    if args.force or not waveform_path.exists():
        waveform = analyze_waveform(audio, bucket_seconds=args.bucket_seconds)
        waveform_path.write_text(
            json.dumps(waveform, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    source_probe = probe_media(master)
    summary = {
        "source_input": str(source),
        "staged_master": str(master),
        "master_mode": args.master_mode,
        "source_sha256": sha256_file(source),
        "master_sha256": sha256_file(master),
        "audio": str(audio.resolve()),
        "waveform": str(waveform_path.resolve()),
        "probe": source_probe,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "media_preparation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
