"""Prepare or run one reference-conditioned Qwen 2.1 asset on local ComfyUI."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE_REQUIRED = {"profile", "back", "hands", "feet", "outfit", "happy", "angry", "repair"}


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request(base, route, data=None, content_type="application/json"):
    payload = json.dumps(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(base.rstrip("/") + route, data=payload)
    if payload is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if "json" in response.headers.get("Content-Type", "") else raw
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc


def upload(base, path):
    boundary = uuid.uuid4().hex
    name = f"qwen-sheet-{uuid.uuid4().hex}{path.suffix.lower()}"
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
            'Content-Type: application/octet-stream\r\n\r\n').encode()
    body += path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    result = request(base, "/upload/image", body, f"multipart/form-data; boundary={boundary}")
    return "/".join(x for x in [result.get("subfolder"), result["name"]] if x)


def build_graph(config, names, prompt, negative, prefix):
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": config["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": config["clip"], "type": config["clip_type"], "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": config["vae"]}},
        "4": {"class_type": "QwenImage21Cache", "inputs": {"model": ["1", 0], "device": config["cache_device"], "dtype": config["cache_dtype"]}},
        "5": {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "prompt": prompt, "negative_prompt": negative, "resolution": config["resolution"]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": config["width"], "height": config["height"], "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["5", 0], "negative": ["5", 1], "latent_image": ["6", 0], "seed": config["seed"], "steps": config["steps"], "cfg": config["cfg"], "sampler_name": config["sampler"], "scheduler": config["scheduler"], "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }
    for index, name in enumerate(names, 1):
        node_id = str(100 + index)
        graph[node_id] = {"class_type": "LoadImage", "inputs": {"image": name}}
        graph["5"]["inputs"][f"images.image_{index}"] = [node_id, 0]
    return graph


def validate(graph, schemas, uploaded=False):
    errors = []
    for node_id, node in graph.items():
        kind, values = node["class_type"], node["inputs"]
        if kind not in schemas:
            errors.append(f"{node_id}: missing node {kind}")
            continue
        schema = schemas[kind]
        specs = {**schema["input"].get("required", {}), **schema["input"].get("optional", {})}
        dynamic = set()
        for key, spec in list(specs.items()):
            if spec[0] == "COMFY_AUTOGROW_V3":
                opts = spec[1]
                dynamic.update(f"{key}.{name}" for name in opts["template"]["names"])
                continue
            if key in schema["input"].get("required", {}) and key not in values:
                errors.append(f"{node_id}: missing input {key}")
        for key, value in values.items():
            spec = specs.get(key, ["IMAGE"] if key in dynamic else None)
            if spec is None:
                errors.append(f"{node_id}: unknown input {key}")
                continue
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                source = graph.get(value[0])
                outputs = schemas.get(source["class_type"], {}).get("output", []) if source else []
                if not isinstance(value[1], int) or not 0 <= value[1] < len(outputs):
                    errors.append(f"{node_id}: invalid connection {key}")
                elif isinstance(spec[0], str) and spec[0] != outputs[value[1]]:
                    errors.append(f"{node_id}: wrong connection type {key}")
                continue
            options = spec[0] if isinstance(spec[0], list) else spec[1].get("options") if len(spec) > 1 else None
            if options is not None and value not in options and not (kind == "LoadImage" and not uploaded):
                errors.append(f"{node_id}: unavailable value {key}={value}")
            limits = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
            if spec[0] in ("INT", "FLOAT"):
                if not isinstance(value, (int, float)) or (spec[0] == "INT" and not isinstance(value, int)):
                    errors.append(f"{node_id}: invalid number {key}")
                elif value < limits.get("min", float('-inf')) or value > limits.get("max", float('inf')):
                    errors.append(f"{node_id}: out of range {key}")
    if errors:
        raise ValueError("\n".join(errors))


def monitor(base, prompt_id, output, timeout, log, log_path):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        histories = request(base, f"/history/{urllib.parse.quote(prompt_id, safe='')}")
        history = histories.get(prompt_id)
        if history:
            save(output.with_suffix(".history.json"), history)
            status = history.get("status", {})
            if status.get("status_str") == "error":
                log.update(state="failed", error=status.get("messages"))
                save(log_path, log)
                raise RuntimeError("ComfyUI execution failed; inspect .history.json")
            if status.get("completed"):
                images = history.get("outputs", {}).get("9", {}).get("images", [])
                if len(images) != 1:
                    raise RuntimeError(f"Expected one saved image; received {len(images)}")
                query = urllib.parse.urlencode({k: images[0][k] for k in ("filename", "subfolder", "type")})
                raw = request(base, "/view?" + query)
                from PIL import Image
                import io
                with Image.open(io.BytesIO(raw)) as image:
                    image.verify()
                output.write_bytes(raw)
                log.update(state="generated_needs_visual_review", output_sha256=digest(output))
                save(log_path, log)
                print(output)
                return
        time.sleep(3)
    log.update(state="timeout_job_retained")
    save(log_path, log)
    raise TimeoutError(f"Job retained: {prompt_id}; resume with --resume and same --output")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", type=Path, default=ROOT / "references/backend.json")
    parser.add_argument("--references", nargs="+", type=Path)
    parser.add_argument("--guide", type=Path, action="append", help="Repeat for accepted views, edit targets, or inspected crop guides")
    parser.add_argument("--asset", choices=["anchor", "front", "profile", "back", "hands", "feet", "outfit", "happy", "angry", "repair"])
    parser.add_argument("--instruction-file", type=Path)
    parser.add_argument("--outfit-reference", type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--timeout", type=float, default=1800)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    log_path = output.with_suffix(".request.json")
    if output.exists():
        parser.error("Output exists; use a new filename to retain accepted/rejected versions")
    if args.resume:
        log = json.loads(log_path.read_text(encoding="utf-8"))
        monitor(log["backend"]["base_url"], log["prompt_id"], output, args.timeout, log, log_path)
        return
    if not args.references or not args.asset:
        parser.error("--references and --asset are required except with --resume")
    if args.asset in GUIDE_REQUIRED and not args.guide:
        parser.error(f"{args.asset} requires an accepted guide or edit target")
    if args.asset == "repair" and not args.instruction_file:
        parser.error("repair requires --instruction-file")
    if args.outfit_reference is not None and not 1 <= args.outfit_reference <= len(args.references):
        parser.error("--outfit-reference must index an original reference")
    if log_path.exists() and json.loads(log_path.read_text(encoding="utf-8")).get("state") != "prepared":
        parser.error("Existing run log; inspect it or use --resume to avoid duplicate submission")
    config = json.loads(args.backend.read_text(encoding="utf-8-sig"))
    for key in ("width", "height", "seed"):
        if getattr(args, key) is not None:
            config[key] = getattr(args, key)
    for key in ("width", "height"):
        if config[key] < 32 or config[key] % 32:
            parser.error(f"{key} must be a positive multiple of 32")
    originals = [path.resolve(strict=True) for path in args.references]
    guides = [path.resolve(strict=True) for path in (args.guide or [])]
    paths = originals + guides
    if len(paths) > 16:
        parser.error("All originals plus required guide must fit in 16 slots")
    from PIL import Image
    for path in paths:
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) != 1:
                parser.error("References must be single-frame images")
            image.verify()
    base = config["base_url"]
    stats = request(base, "/system_stats")
    schemas = request(base, "/object_info")
    templates = json.loads((ROOT / "references/prompts.json").read_text(encoding="utf-8"))
    prompt = templates["common"] + f"\nImages 1 through {len(originals)} are ALL original references and define identity."
    if len(guides) == 1:
        prompt += f" Image {len(paths)} is the accepted guide or edit target, subordinate to originals for identity."
    elif guides:
        prompt += f" Images {len(originals)+1} through {len(paths)} are accepted continuity guides, edit targets, or crop guides; originals remain the identity authority."
    if args.outfit_reference:
        prompt += f" Use clothing and hairstyle exclusively from Image {args.outfit_reference}; other originals are identity references."
    prompt += "\n" + templates[args.asset]
    if args.instruction_file:
        prompt += "\n" + args.instruction_file.read_text(encoding="utf-8-sig")
    inventory = [{"path": str(path), "sha256": digest(path), "role": "original" if i < len(originals) else "guide_or_target", "image_index": i+1} for i, path in enumerate(paths)]
    prefix = "character-sheet-qwen/" + uuid.uuid4().hex
    names = [path.name for path in paths]
    graph = build_graph(config, names, prompt, templates["negative"], prefix)
    validate(graph, schemas)
    log = {"created_at": datetime.now(timezone.utc).isoformat(), "state": "prepared", "asset": args.asset, "backend": config, "runtime": stats, "references": inventory, "prompt": prompt, "negative_prompt": templates["negative"], "client_id": str(uuid.uuid4())}
    save(output.with_suffix(".inventory.json"), inventory)
    save(output.with_suffix(".api.json"), graph)
    save(log_path, log)
    if not args.run:
        print(f"Schema validated: {len(graph)} nodes, {len(paths)} references; no upload or queue submission")
        return
    for entry, path in zip(inventory, paths):
        entry["server_image"] = upload(base, path)
        save(log_path, log)
    graph = build_graph(config, [entry["server_image"] for entry in inventory], prompt, templates["negative"], prefix)
    validate(graph, request(base, "/object_info"), uploaded=True)
    save(output.with_suffix(".api.json"), graph)
    save(output.with_suffix(".inventory.json"), inventory)
    log["state"] = "submitting_outcome_unknown"
    save(log_path, log)
    result = request(base, "/prompt", {"prompt": graph, "client_id": log["client_id"]})
    log["submission"] = result
    log["prompt_id"] = result.get("prompt_id")
    log["state"] = "validation_failed" if result.get("node_errors") or not result.get("prompt_id") else "queued"
    save(log_path, log)
    if log["state"] == "validation_failed":
        raise RuntimeError(f"Prompt rejected: {result}")
    print(f"Queued {log['prompt_id']}", flush=True)
    monitor(base, log["prompt_id"], output, args.timeout, log, log_path)


if __name__ == "__main__":
    main()
