#!/usr/bin/env python3
"""Package a selected LoRA and validation metadata locally; never connects or publishes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


PARAMETERS = (
    "trigger", "negative", "strength", "workflow", "unet", "width", "height",
    "steps", "cfg", "sampler", "scheduler",
)


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checkpoint_images(meta, checkpoint):
    # lora_file is an absolute path written by eval_lora.py. Accept paths
    # from either OS when a workspace has moved between machines.
    return [entry for entry in meta["images"]
            if entry.get("lora_file") and
            str(entry["lora_file"]).replace("\\", "/").rsplit("/", 1)[-1] == checkpoint]


def generation_metadata(root, checkpoint):
    result = {}
    for test in ("reconstruction", "scenario"):
        relative = Path("07_validate") / test / "test_meta.json"
        meta = read_json(root / relative)
        images = checkpoint_images(meta, checkpoint)
        if not images:
            raise ValueError(f"No validation images for {checkpoint} in {relative}")
        for entry in images:
            for key in ("prompt", "seed", "case", "label", "output_path"):
                if key not in entry:
                    raise ValueError(f"Missing image field '{key}' in {relative}")
        result[test] = {
            "source": relative.as_posix(),
            **{key: meta[key] for key in PARAMETERS},
            "seeds": list(dict.fromkeys(entry["seed"] for entry in images)),
            "images": images,
        }
    return result


def showcase_metadata(root, checkpoint):
    images = []
    for variant in ("keep", "change"):
        source_dir = root / "07_validate" / f"showcase_{variant}"
        if variant == "change" and not source_dir.exists():
            source_dir = root / "07_validate" / "showcase"
        meta_path = source_dir / "test_meta.json"
        if not meta_path.exists():
            print(f"Warning: missing {variant} showcase metadata: {meta_path}", file=sys.stderr)
            continue
        meta = read_json(meta_path)
        settings = {key: meta[key] for key in PARAMETERS}
        for entry in checkpoint_images(meta, checkpoint):
            source = Path(entry["output_path"])
            images.append({
                "file": f"{variant}_{entry['case']}.png",
                "variant": variant, "case": entry["case"],
                "seed": entry["seed"], "prompt": entry["prompt"],
                "negative": meta["negative"],
                "settings": settings, "source_path": entry["output_path"],
                "sha256": sha256(source), "size": source.stat().st_size,
            })
    return sorted(images, key=lambda entry: (entry["case"], entry["variant"] != "keep"))


def package(workspace, dry_run=False):
    root = Path(workspace).expanduser().resolve()
    project = read_json(root / "project.json")
    checkpoint = project.get("release_ckpt")
    if (not isinstance(checkpoint, str) or not checkpoint
            or "/" in checkpoint or "\\" in checkpoint
            or Path(checkpoint).suffix != ".safetensors"):
        raise ValueError("Set project.json release_ckpt to the selected .safetensors filename")
    source = root / "06_train" / "models" / checkpoint
    digest = sha256(source)
    release_dir = root / "08_release"
    release_path = release_dir / "release.json"
    civitai = {"version_id": None, "version_url": None,
               "version_status": None, "showcase_status": None}
    if release_path.exists():
        previous = read_json(release_path)
        if previous.get("checkpoint", {}).get("sha256") == digest:
            civitai.update(previous.get("civitai", {}))
    release = {
        "work": project["work"], "character": project["character"],
        "trigger": project["trigger"], "release_ckpt": checkpoint,
        "checkpoint": {"source": f"06_train/models/{checkpoint}",
                       "file": checkpoint, "sha256": digest,
                       "file_size": source.stat().st_size},
        "generation": generation_metadata(root, checkpoint),
        "civitai": civitai,
    }
    showcase_dir = release_dir / "showcase"
    manifest_path = showcase_dir / "showcase_manifest.json"
    showcase = showcase_metadata(root, checkpoint)
    if not dry_run:
        release_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".package-", dir=release_dir) as temporary:
            staging = Path(temporary)
            shutil.copyfile(source, staging / checkpoint)
            if sha256(staging / checkpoint) != digest:
                raise ValueError("Checkpoint changed during packaging; run again")
            (staging / "release.json").write_text(
                json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(staging / checkpoint, release_dir / checkpoint)
            os.replace(staging / "release.json", release_path)
        showcase_dir.mkdir(parents=True, exist_ok=True)
        for entry in showcase:
            shutil.copyfile(entry["source_path"], showcase_dir / entry["file"])
        manifest_path.write_text(
            json.dumps(showcase, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"dry_run": dry_run, "output_dir": str(release_dir), "release": release,
            "showcase": {"output_dir": str(showcase_dir),
                         "manifest": str(manifest_path), "images": showcase}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Show package metadata without writing files")
    args = parser.parse_args(argv)
    try:
        result = package(args.workspace, args.dry_run)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
