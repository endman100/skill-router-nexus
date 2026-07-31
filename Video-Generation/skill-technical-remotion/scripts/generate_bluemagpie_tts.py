#!/usr/bin/env python3
"""Generate one BlueMagpie-TTS FLAC from the skill's canonical reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "references" / "bluemagpie-default-voice.json"
DELIBERATE_BOUNDARIES = set("，；：。！？")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str, *, timeout: float = 30.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def load_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        text = args.text
    else:
        text = args.text_file.read_text(encoding="utf-8-sig")
    text = text.strip()
    if not text:
        raise ValueError("generation text must not be empty")
    internal_boundaries = [
        character for character in text[:-1] if character in DELIBERATE_BOUNDARIES
    ]
    if internal_boundaries:
        raise ValueError(
            "generation text must contain exactly one pause unit; split at every ，；：。！？ boundary"
        )
    return text


def accepted_inputs(schema: dict[str, Any], node_name: str) -> set[str]:
    node = schema.get(node_name)
    if not isinstance(node, dict):
        raise RuntimeError(f"ComfyUI node is unavailable: {node_name}")
    inputs = node.get("input", {})
    return set(inputs.get("required", {})) | set(inputs.get("optional", {}))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate BlueMagpie speech with the canonical bundled reference audio."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--text-file", type=Path)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument(
        "--filename-prefix",
        default="BlueMagpie_Default_Voice/BlueMagpie_default_voice",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--cfg-value", type=float)
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--client-id", default="codex-bluemagpie-tts")
    args = parser.parse_args()

    if args.timeout_seconds <= 0 or args.poll_interval_seconds <= 0:
        raise ValueError("timeout and poll interval must be positive")
    text = load_text(args)
    profile_path = args.profile.resolve()
    profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    if profile.get("provider") != "comfyui-bluemagpie-tts":
        raise ValueError("profile provider must be comfyui-bluemagpie-tts")

    record = profile.get("assets", {}).get("cloning_audio", {})
    reference_path = (ROOT / record.get("path", "")).resolve()
    if not reference_path.is_file():
        raise FileNotFoundError(f"canonical reference is missing: {reference_path}")
    if reference_path.stat().st_size != record.get("bytes"):
        raise ValueError("canonical reference byte count does not match the profile")
    if file_sha256(reference_path) != record.get("sha256"):
        raise ValueError("canonical reference SHA-256 does not match the profile")

    comfyui = profile["comfyui"]
    base_url = f"http://{comfyui['host']}:{comfyui['port']}"
    loader_name = comfyui["loader_node"]
    tts_name = comfyui["node"]
    save_name = comfyui["save_node"]
    loader_schema = request_json(f"{base_url}/object_info/{loader_name}")
    tts_schema = request_json(f"{base_url}/object_info/{tts_name}")
    save_schema = request_json(f"{base_url}/object_info/{save_name}")
    accepted_inputs(loader_schema, loader_name)
    tts_inputs_available = accepted_inputs(tts_schema, tts_name)
    accepted_inputs(save_schema, save_name)

    generation = profile["generation"]
    cfg_value = generation["cfg_value"] if args.cfg_value is None else args.cfg_value
    approved_cfg_values = set(generation.get("candidate_cfg_values", [])) | {
        generation["cfg_value"]
    }
    if cfg_value not in approved_cfg_values:
        raise ValueError(
            f"cfg value {cfg_value} is not profile-approved: {sorted(approved_cfg_values)}"
        )
    tts_inputs: dict[str, Any] = {
        "model": ["1", 0],
        "text": text,
        "speaker": generation["speaker"],
        "cfg_value": cfg_value,
        "inference_timesteps": generation["inference_timesteps"],
        "max_len": generation["max_len"],
        "retry_badcase": generation["retry_badcase"],
        "reference_audio_path": str(reference_path),
    }
    missing_inputs = set(tts_inputs) - tts_inputs_available
    if missing_inputs:
        raise RuntimeError(
            f"live {tts_name} schema is missing required inputs: {sorted(missing_inputs)}"
        )
    seed_supported = "seed" in tts_inputs_available
    if args.seed is not None:
        if not seed_supported:
            raise RuntimeError("live BlueMagpieTTS schema does not expose a seed input")
        tts_inputs["seed"] = args.seed

    workflow = {
        "1": {
            "class_type": loader_name,
            "inputs": {"model_path": profile["model"], "device": "cuda"},
        },
        "2": {"class_type": tts_name, "inputs": tts_inputs},
        "3": {
            "class_type": save_name,
            "inputs": {"audio": ["2", 0], "filename_prefix": args.filename_prefix},
        },
    }
    queued = request_json(
        f"{base_url}/prompt",
        method="POST",
        payload={"prompt": workflow, "client_id": args.client_id},
    )
    if queued.get("node_errors"):
        raise RuntimeError(f"ComfyUI rejected the workflow: {queued['node_errors']}")
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI did not return a prompt_id: {queued}")

    deadline = time.monotonic() + args.timeout_seconds
    record_data: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        history = request_json(f"{base_url}/history/{prompt_id}")
        candidate = history.get(prompt_id)
        if candidate:
            record_data = candidate
            break
        time.sleep(args.poll_interval_seconds)
    if record_data is None:
        raise TimeoutError(f"BlueMagpie generation timed out: {prompt_id}")

    status = record_data.get("status", {})
    if status.get("status_str") != "success" or status.get("completed") is not True:
        raise RuntimeError(f"BlueMagpie generation failed: {status}")
    outputs = record_data.get("outputs", {}).get("3", {}).get("audio", [])
    if not outputs:
        raise RuntimeError("SaveAudio returned no audio output")
    descriptor = outputs[0]

    output_path: Path | None = None
    output_hash: str | None = None
    if args.output is not None:
        query = urllib.parse.urlencode(
            {
                "filename": descriptor["filename"],
                "subfolder": descriptor.get("subfolder", ""),
                "type": descriptor.get("type", "output"),
            }
        )
        audio_bytes = request_bytes(f"{base_url}/view?{query}")
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)
        output_hash = hashlib.sha256(audio_bytes).hexdigest()

    result = {
        "prompt_id": prompt_id,
        "provider": profile["provider"],
        "model": profile["model"],
        "node": tts_name,
        "voice_id": profile["voice_id"],
        "reference_audio": str(reference_path),
        "reference_sha256": record["sha256"],
        "seed_supported": seed_supported,
        "seed": args.seed,
        "cfg_value": cfg_value,
        "server_output": descriptor,
        "downloaded_output": str(output_path) if output_path else None,
        "downloaded_sha256": output_hash,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
