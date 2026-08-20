from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from pipeline_utils import read_csv, seconds_to_timestamp, write_csv


MODEL_ID = "lab260/MusicDetection"
SAMPLE_RATE = 16_000


def average_windows_by_second(
    window_rows: Iterable[dict[str, Any]],
    duration_seconds: float,
) -> list[dict[str, Any]]:
    second_count = int(math.ceil(duration_seconds))
    sums = [0.0] * second_count
    counts = [0] * second_count
    starts: list[list[str]] = [[] for _ in range(second_count)]
    for row in window_rows:
        start = float(row["window_start_seconds"])
        end = float(row["window_end_seconds"])
        probability = float(row["music_probability"])
        first = max(0, int(math.floor(start)))
        last = min(second_count - 1, int(math.ceil(end)) - 1)
        for second in range(first, last + 1):
            if start < second + 1 and end > second:
                sums[second] += probability
                counts[second] += 1
                starts[second].append(f"{start:.3f}")
    output: list[dict[str, Any]] = []
    for second in range(second_count):
        probability = sums[second] / counts[second] if counts[second] else math.nan
        output.append(
            {
                "second_start": second,
                "second_end": min(second + 1, duration_seconds),
                "second_start_ts": seconds_to_timestamp(second),
                "second_end_ts": seconds_to_timestamp(
                    min(second + 1, duration_seconds)
                ),
                "avg_music_probability": (
                    f"{probability:.6f}" if not math.isnan(probability) else ""
                ),
                "covering_window_count": counts[second],
                "covering_window_starts": ";".join(starts[second]),
            }
        )
    return output


def resolve_model_repo(output_dir: Path, explicit_repo: Path | None) -> Path:
    if explicit_repo and (explicit_repo / "model.py").is_file():
        return explicit_repo.resolve()
    local_repo = output_dir / "model_repo"
    if (local_repo / "model.py").is_file():
        return local_repo.resolve()
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is required to download MusicDetection"
        ) from exc
    return Path(snapshot_download(MODEL_ID, local_dir=str(local_repo))).resolve()


def load_model(repo_dir: Path, device: str, precision: str, torch_module: Any) -> Any:
    try:
        from safetensors import safe_open
    except ImportError as exc:
        raise RuntimeError("safetensors is required for MusicDetection") from exc
    model_py = repo_dir / "model.py"
    spec = importlib.util.spec_from_file_location(
        "lab260_music_detection_model",
        model_py,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {model_py}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    model = module.WavLMForMusicDetection(batch_size=1, device=device)
    if precision == "bf16" and device.startswith("cuda"):
        model.convert_to_bf16()
    elif precision == "fp16" and device.startswith("cuda"):
        model.half()
        model.dtype = torch_module.float16
    else:
        model.float()
        model.dtype = torch_module.float32
    checkpoint_device = device if device.startswith("cuda") else "cpu"
    checkpoint = repo_dir / "music_detection.safetensors"
    with safe_open(str(checkpoint), framework="pt", device=checkpoint_device) as handle:
        state_dict = {key: handle.get_tensor(key) for key in handle.keys()}
    model.load_state_dict(state_dict)
    model.eval()
    return model


def build_windows(
    audio: Any,
    starts: list[float],
    window_seconds: float,
    np_module: Any,
) -> list[Any]:
    window_length = int(round(window_seconds * SAMPLE_RATE))
    windows: list[Any] = []
    for start in starts:
        first = int(round(start * SAMPLE_RATE))
        segment = audio[first : first + window_length]
        if len(segment) < window_length:
            segment = np_module.pad(segment, (0, window_length - len(segment)))
        windows.append(segment.astype(np_module.float32, copy=False))
    return windows


def score_batch(model: Any, windows: list[Any], torch_module: Any) -> list[float]:
    inputs = model.processor(
        windows,
        sampling_rate=model.target_sample_rate,
        return_tensors="pt",
        padding=True,
        truncation=False,
    )
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    with torch_module.inference_mode():
        probabilities = model.forward(**inputs).squeeze(-1)
    return [float(value) for value in probabilities.detach().cpu().tolist()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score a complete audio track with lab260/MusicDetection."
    )
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-repo", type=Path)
    parser.add_argument("--window-seconds", type=float, default=3.0)
    parser.add_argument("--hop-seconds", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=48)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--precision", choices=("bf16", "fp16", "fp32"), default="bf16")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint-batches", type=int, default=10)
    parser.add_argument("--limit-seconds", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.window_seconds <= 0 or args.hop_seconds <= 0:
        raise ValueError("window and hop sizes must be positive")
    if args.batch_size < 1:
        raise ValueError("batch size must be positive")
    audio_path = args.audio.resolve()
    if not audio_path.is_file():
        raise FileNotFoundError(audio_path)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        import librosa
        import numpy as np
        import torch
    except ImportError as exc:
        raise RuntimeError("MusicDetection requires librosa, numpy, and torch") from exc
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    precision = args.precision if device.startswith("cuda") else "fp32"
    repo = resolve_model_repo(output_dir, args.model_repo)
    model = load_model(repo, device, precision, torch)
    audio, sample_rate = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    if sample_rate != SAMPLE_RATE:
        raise RuntimeError(f"Unexpected sample rate: {sample_rate}")
    duration = len(audio) / SAMPLE_RATE
    limit = duration if args.limit_seconds <= 0 else min(duration, args.limit_seconds)
    windows_csv = output_dir / "music_probability_windows.csv"
    rows: list[dict[str, Any]] = []
    if args.resume and windows_csv.exists():
        rows = list(read_csv(windows_csv))
    completed = {
        round(float(row["window_start_seconds"]), 6)
        for row in rows
        if row.get("window_start_seconds") not in (None, "")
    }
    starts = [
        round(float(value), 6)
        for value in np.arange(0.0, limit, args.hop_seconds)
        if round(float(value), 6) not in completed
    ]
    fields = [
        "window_start_seconds",
        "window_end_seconds",
        "window_start_ts",
        "window_end_ts",
        "window_seconds",
        "hop_seconds",
        "music_probability",
        "music_pred_threshold",
    ]
    started = time.monotonic()
    for batch_offset in range(0, len(starts), args.batch_size):
        batch_starts = starts[batch_offset : batch_offset + args.batch_size]
        batch_windows = build_windows(audio, batch_starts, args.window_seconds, np)
        scores = score_batch(model, batch_windows, torch)
        for start, probability in zip(batch_starts, scores, strict=True):
            end = start + args.window_seconds
            rows.append(
                {
                    "window_start_seconds": f"{start:.3f}",
                    "window_end_seconds": f"{end:.3f}",
                    "window_start_ts": seconds_to_timestamp(start),
                    "window_end_ts": seconds_to_timestamp(end),
                    "window_seconds": f"{args.window_seconds:.3f}",
                    "hop_seconds": f"{args.hop_seconds:.3f}",
                    "music_probability": f"{probability:.6f}",
                    "music_pred_threshold": str(probability >= args.threshold),
                }
            )
        batch_no = batch_offset // args.batch_size + 1
        checkpoint = (
            args.checkpoint_batches > 0 and batch_no % args.checkpoint_batches == 0
        ) or batch_offset + args.batch_size >= len(starts)
        if checkpoint:
            rows.sort(key=lambda row: float(row["window_start_seconds"]))
            write_csv(windows_csv, rows, fields)
            print(
                f"scored {min(batch_offset + args.batch_size, len(starts))}/"
                f"{len(starts)} windows in {time.monotonic() - started:.1f}s",
                flush=True,
            )
    if not starts and rows:
        rows.sort(key=lambda row: float(row["window_start_seconds"]))
        write_csv(windows_csv, rows, fields)
    if not rows:
        raise ValueError("MusicDetection produced no windows")
    per_second = average_windows_by_second(rows, duration)
    per_second_fields = list(per_second[0].keys())
    write_csv(
        output_dir / "music_probability_avg_by_second.csv",
        per_second,
        per_second_fields,
    )
    probabilities = [float(row["music_probability"]) for row in rows]
    summary = {
        "audio": str(audio_path),
        "model": MODEL_ID,
        "model_repo": str(repo),
        "device": device,
        "precision": precision,
        "fp8_allowed": False,
        "window_seconds": args.window_seconds,
        "hop_seconds": args.hop_seconds,
        "threshold": args.threshold,
        "audio_duration_seconds": duration,
        "window_count": len(rows),
        "mean_probability": sum(probabilities) / len(probabilities),
        "windows_csv": str(windows_csv),
        "per_second_csv": str(output_dir / "music_probability_avg_by_second.csv"),
    }
    (output_dir / "music_detection_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
