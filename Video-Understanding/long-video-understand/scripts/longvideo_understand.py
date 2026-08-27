#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path
from typing import Any

MODEL_ID = "MCG-NJU/VideoChat3-4B"
MODEL_REVISION = "37fa901ec5913f84bc31108ebc1e60ad1903634c"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Understand long videos with a pinned VideoChat3-4B model."
    )
    parser.add_argument("video", type=Path)
    parser.add_argument("--prompt", default="Create a timestamped summary and identify important events.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    parser.add_argument("--chunk-seconds", type=float, default=120.0)
    parser.add_argument("--nframes", type=int, default=8)
    parser.add_argument("--max-pixels", type=int, default=100352)
    parser.add_argument("--segment-tokens", type=int, default=192)
    parser.add_argument("--summary-tokens", type=int, default=512)
    parser.add_argument("--chapter-size", type=int, default=12)
    parser.add_argument(
        "--attention-backend",
        choices=("auto", "sdpa", "eager", "flash_attention_2"),
        default="auto",
    )
    parser.add_argument("--no-resume", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    args.video = args.video.expanduser().resolve()
    if not args.video.is_file():
        raise FileNotFoundError(args.video)
    if args.output is None:
        args.output = args.video.with_suffix(args.video.suffix + ".videochat3.json")
    else:
        args.output = args.output.expanduser().resolve()
    if args.chunk_seconds <= 0:
        raise ValueError("--chunk-seconds must be positive")
    if args.nframes < 2 or args.nframes % 2:
        raise ValueError("--nframes must be an even integer of at least 2")
    if args.max_pixels < 100352:
        raise ValueError("--max-pixels must be at least 100352 for qwen-vl-utils")
    if args.chapter_size < 2:
        raise ValueError("--chapter-size must be at least 2")


def video_duration(video: Path) -> float:
    from decord import VideoReader, cpu

    reader = VideoReader(str(video), ctx=cpu(0), num_threads=1)
    fps = float(reader.get_avg_fps())
    if fps <= 0 or len(reader) < 2:
        raise ValueError(f"Unable to determine a usable duration for {video}")
    return len(reader) / fps


def choose_attention_backend(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import flash_attn  # noqa: F401

        return "flash_attention_2"
    except ImportError:
        return "sdpa"


def load_runtime(args: argparse.Namespace, backend: str):
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoProcessor

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for practical VideoChat3-4B inference")
    config = AutoConfig.from_pretrained(
        args.model_id,
        revision=args.model_revision,
        trust_remote_code=True,
    )
    config.vision_config.attn_impl = backend
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        revision=args.model_revision,
        config=config,
        dtype="auto",
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    processor = AutoProcessor.from_pretrained(
        args.model_id,
        revision=args.model_revision,
        trust_remote_code=True,
    )
    return torch, model, processor


def model_inputs(torch, model, processor, messages: list[dict[str, Any]]):
    from qwen_vl_utils import process_vision_info

    chat_text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    images, videos, video_kwargs = process_vision_info(
        messages,
        image_patch_size=14,
        return_video_kwargs=True,
        return_video_metadata=True,
    )
    video_metadatas = None
    if videos is not None:
        videos, video_metadatas = zip(*videos)
        videos, video_metadatas = list(videos), list(video_metadatas)
    inputs = processor(
        text=chat_text,
        images=images,
        videos=videos,
        video_metadata=video_metadatas,
        do_resize=False,
        return_tensors="pt",
        **(video_kwargs or {}),
    )
    inputs = inputs.to(model.device)
    if hasattr(model, "dtype"):
        inputs = inputs.to(model.dtype)
    return inputs


def decode_generation(torch, model, processor, inputs, max_new_tokens: int) -> str:
    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
    trimmed = [
        output[len(source) :] for source, output in zip(inputs.input_ids, output_ids)
    ]
    return processor.tokenizer.batch_decode(
        trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0].strip()


def analyze_segment(torch, model, processor, args, start: float, end: float) -> str:
    segment_prompt = (
        f"The visible range is {format_time(start)} to {format_time(end)}. "
        f"User goal: {args.prompt}\n"
        "Describe only evidence visible in the sampled frames. Include temporal order, "
        "actions, scene changes, on-screen text, and uncertainty. Do not invent timestamps "
        "inside this segment; refer only to the provided start-to-end range."
    )
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "video",
                    "video": str(args.video),
                    "video_start": start,
                    "video_end": end,
                    "nframes": args.nframes,
                    "max_pixels": args.max_pixels,
                },
                {"type": "text", "text": segment_prompt},
            ],
        }
    ]
    inputs = model_inputs(torch, model, processor, messages)
    return decode_generation(torch, model, processor, inputs, args.segment_tokens)


def synthesize(torch, model, processor, source_text: str, instruction: str, tokens: int) -> str:
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": instruction + "\n\n" + source_text}],
        }
    ]
    inputs = model_inputs(torch, model, processor, messages)
    return decode_generation(torch, model, processor, inputs, tokens)


def format_time(seconds: float) -> str:
    total = max(0, round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def identity(args, duration: float, backend: str) -> dict[str, Any]:
    stat = args.video.stat()
    return {
        "video": str(args.video),
        "video_size": stat.st_size,
        "video_mtime_ns": stat.st_mtime_ns,
        "duration_seconds": round(duration, 3),
        "model_id": args.model_id,
        "model_revision": args.model_revision,
        "attention_backend": backend,
        "chunk_seconds": args.chunk_seconds,
        "nframes": args.nframes,
        "max_pixels": args.max_pixels,
        "prompt": args.prompt,
    }


def initial_state(run_identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run": run_identity,
        "segments": [],
        "chapters": [],
        "final_answer": None,
        "elapsed_seconds": 0.0,
        "peak_cuda_memory_gib": None,
    }


def load_or_create_state(args, run_identity: dict[str, Any]) -> dict[str, Any]:
    if args.output.exists() and not args.no_resume:
        state = json.loads(args.output.read_text(encoding="utf-8"))
        if state.get("run") != run_identity:
            raise ValueError(
                f"Checkpoint options do not match {args.output}; choose another --output or use --no-resume"
            )
        return state
    return initial_state(run_identity)


def segment_text(segment: dict[str, Any]) -> str:
    return f"[{segment['start_time']}–{segment['end_time']}] {segment['answer']}"


def main() -> int:
    args = parse_args()
    validate_args(args)
    # On Windows, import PyTorch before decord so their bundled runtime DLLs do not
    # initialize in an order that can make torch's c10.dll fail to load.
    import torch as _torch  # noqa: F401

    started = time.perf_counter()
    duration = video_duration(args.video)
    backend = choose_attention_backend(args.attention_backend)
    run_identity = identity(args, duration, backend)
    state = load_or_create_state(args, run_identity)
    if state.get("final_answer"):
        print(json.dumps({"output": str(args.output), "final_answer": state["final_answer"], "resumed": True}, ensure_ascii=False, indent=2))
        return 0

    torch, model, processor = load_runtime(args, backend)
    completed = {segment["index"] for segment in state["segments"]}
    segment_count = math.ceil(duration / args.chunk_seconds)
    for index in range(segment_count):
        if index in completed:
            continue
        start = index * args.chunk_seconds
        end = min(duration, (index + 1) * args.chunk_seconds)
        answer = analyze_segment(torch, model, processor, args, start, end)
        state["segments"].append(
            {
                "index": index,
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "start_time": format_time(start),
                "end_time": format_time(end),
                "answer": answer,
            }
        )
        state["segments"].sort(key=lambda item: item["index"])
        save_state(args.output, state)

    if len(state["segments"]) == 1:
        state["final_answer"] = state["segments"][0]["answer"]
    else:
        chapter_map = {chapter["index"]: chapter for chapter in state["chapters"]}
        chapter_count = math.ceil(len(state["segments"]) / args.chapter_size)
        for index in range(chapter_count):
            if index in chapter_map:
                continue
            group = state["segments"][index * args.chapter_size : (index + 1) * args.chapter_size]
            source = "\n".join(segment_text(segment) for segment in group)
            answer = synthesize(
                torch,
                model,
                processor,
                source,
                "Merge these sampled segment observations into a faithful chapter summary. Use only the bracketed segment ranges as timestamps; discard relative or sub-second timestamps inside model observations. Preserve uncertainty and do not invent unseen events.",
                args.summary_tokens,
            )
            state["chapters"].append(
                {
                    "index": index,
                    "start_time": group[0]["start_time"],
                    "end_time": group[-1]["end_time"],
                    "answer": answer,
                }
            )
            state["chapters"].sort(key=lambda item: item["index"])
            save_state(args.output, state)
        chapter_source = "\n\n".join(
            f"Chapter {chapter['index'] + 1} [{chapter.get('start_time', 'unknown')}–{chapter.get('end_time', 'unknown')}]: {chapter['answer']}"
            for chapter in state["chapters"]
        )
        state["final_answer"] = synthesize(
            torch,
            model,
            processor,
            chapter_source,
            f"Answer the user goal: {args.prompt}\nCreate one coherent final answer grounded only in the chapter summaries. Use only their explicit bracketed ranges as timestamps, never relative or invented sub-second times. Note sampling uncertainty.",
            args.summary_tokens,
        )

    state["elapsed_seconds"] = round(time.perf_counter() - started, 2)
    state["peak_cuda_memory_gib"] = round(torch.cuda.max_memory_allocated() / 1024**3, 2)
    save_state(args.output, state)
    print(json.dumps({"output": str(args.output), "final_answer": state["final_answer"], "elapsed_seconds": state["elapsed_seconds"], "peak_cuda_memory_gib": state["peak_cuda_memory_gib"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
