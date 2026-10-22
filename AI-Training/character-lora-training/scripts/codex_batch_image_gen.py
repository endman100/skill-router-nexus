#!/usr/bin/env python3
"""Batch image generation through an isolated `codex exec` (stdlib only).

Generate keep_outfit N images, change_outfit 2N images:
  codex_batch_image_gen.py N <reference> <folder>

Top-up mode (change_outfit only, e.g. after missing.json reports a shortfall):
  codex_batch_image_gen.py --fill-existing <folder>/change_outfit --target 2N --reference <reference> [--dry-run]
Counts the valid PNGs already in that folder and asks Codex for only the missing
count with the change-outfit prompt (never the keep-outfit prompt). New files are
numbered after the highest existing number and created exclusively, so existing
images are never overwritten or regenerated; a returned image whose sha256 equals
an existing image is discarded. Updates <folder>/missing.json when present.
"""

import argparse
import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib


DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_COUNT = 30
DEFAULT_MAX_ROUNDS = 3
DEFAULT_EFFORT = "medium"
# Kept in the same order as reference_codex_judge.py. Image generation is the
# sole exception at command construction time; tests compare the entire tuple.
DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "code_mode_host", "shell_snapshot", "apps",
    "plugins", "remote_plugin", "plugin_sharing", "browser_use",
    "browser_use_external", "browser_use_full_cdp_access", "computer_use",
    "in_app_browser", "hooks", "image_generation", "multi_agent",
    "workspace_dependencies", "skill_mcp_dependency_install",
    "tool_call_mcp_elicitation", "tool_suggest", "goals", "guardian_approval",
    "auth_elicitation", "personality",
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


KEEP_OUTFIT_PROMPT = '幫我維持服裝設計與角色特徵 生成N張這個角色在不同背景 不同姿勢 不同動作 不同表情 不同長寬比的一張圖 採用乾淨的日系動畫賽璐璐上色，線稿俐落，色塊均勻，陰影簡潔，漸層平滑。皮膚與服裝表面乾淨，不添加膠片顆粒、紙張紋理、斑駁筆觸、細碎雜點或過度銳化。背景使用簡潔的動畫美術風格，避免密集零碎的材質細節。保留角色與服裝的必要細節。'

CHANGE_OUTFIT_PROMPT = "Generate N images of this character, maintaining strict consistency in the character's facial features, hairstyle, body proportions, distinctive traits, and overall art style, while featuring a different outfit in each image.\n\nDesign N unique outfits with diverse clothing styles, colors, combinations, and accessories. Each outfit should complement the character's original personality and aesthetic while preserving their recognizable identity.\n\nEach image should feature different backgrounds, poses, actions, facial expressions (including joy, anger, sadness, excitement, surprise, and calmness), aspect ratios, camera angles, and perspectives.\n\nUse a clean Japanese anime style with cel shading, crisp and precise linework, uniform color fills, simplified shadows, and smooth gradients.\n\nKeep the skin and clothing surfaces clean and smooth. Do not add film grain, paper textures, rough or blotchy brushstrokes, fine speckles, visual noise, or excessive sharpening.\n\nUse simple, clean anime-style background art, avoiding overly dense textures and unnecessary small details.\n\nPreserve all essential character details while allowing creative freedom in clothing design. Ensure the character remains visually recognizable and consistent across all N images, with each image showcasing a unique outfit, environment, pose, action, emotion, aspect ratio, and camera perspective.\n\n**Important:** Change the clothing in every image, but do not alter the character's face, hairstyle, eye color"

PROMPTS = (("keep_outfit", KEEP_OUTFIT_PROMPT), ("change_outfit", CHANGE_OUTFIT_PROMPT))


def fill_prompt(template, count, folder):
    """Replace the standalone N with the count and append the save folder."""
    text = re.sub(r"(?<![A-Za-z])N(?![A-Za-z])", str(count), template)
    return f"{text}\n\nSave folder: {folder}\n"


def generation_instructions(count):
    return (
        "Use only the provided reference image and the current user's prompt. "
        "Image generation is the only allowed capability. Never use other tools, "
        "files, skills, memory, or external information. "
        f"Generate {count} separate images, not a collage or sheet."
    )


def prepare_home(source, target, model=DEFAULT_MODEL, count=DEFAULT_COUNT):
    """Read only auth/cache from source; create only auth + one-model catalog."""
    target.mkdir(mode=0o700)
    shutil.copy2(source / "auth.json", target / "auth.json")
    (target / "auth.json").chmod(0o600)
    cache = json.loads((source / "models_cache.json").read_text(encoding="utf-8-sig"))
    entry = next((item for item in cache["models"] if item["slug"] == model), None)
    if entry is None:
        raise ValueError(f"Model {model!r} is absent from {source / 'models_cache.json'}")
    instructions = generation_instructions(count)
    entry.update(
        input_modalities=["text", "image"],
        base_instructions=instructions,
        model_messages={
            "instructions_template": instructions,
            "instructions_variables": None,
            "approvals": None,
        },
        include_skills_usage_instructions=False,
        supports_reasoning_summaries=True,
        supports_parallel_tool_calls=False,
        supports_search_tool=False,
        experimental_supported_tools=[],
        # Cached Sol catalogs can require code mode, whose host is deliberately
        # disabled by the judge. Expose image_gen directly without that host.
        tool_mode="direct",
    )
    catalog = target / "model_catalog.json"
    catalog.write_text(json.dumps({"models": [entry]}), encoding="utf-8")
    return catalog


def isolated_environment(home, source=None):
    source = os.environ if source is None else source
    env = {key: value for key, value in source.items()
           if not key.upper().startswith("CODEX_")}
    env["CODEX_HOME"] = str(home.resolve())
    return env


def command(codex, cwd, catalog, reference, last_message,
            model=DEFAULT_MODEL, effort=DEFAULT_EFFORT):
    """Mirror the judge, except image generation replaces the scoring schema."""
    value = [
        codex, "exec", "--json", "--output-last-message", str(last_message),
        "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config",
        "--skip-git-repo-check", "--model", model,
        "-c", f'model_reasoning_effort="{effort}"',
        "-c", 'approval_policy="never"',
        "-c", 'default_permissions="judge"',
        "-c", 'permissions.judge.filesystem={":minimal"="read"}',
        "-c", "permissions.judge.network.enabled=false",
        "-c", "skills.include_instructions=false",
        "-c", "skills.bundled.enabled=false",
        "-c", "include_apps_instructions=false",
        "-c", "include_collaboration_mode_instructions=false",
        "-c", "include_environment_context=false",
        "-c", "include_permissions_instructions=false",
        "-c", 'web_search="disabled"',
        "--sandbox", "danger-full-access",
        "-c", f"model_catalog_json={json.dumps(str(catalog.resolve()))}",
    ]
    for feature in DISABLED_FEATURES:
        if feature != "image_generation":
            value.extend(("--disable", feature))
    value.extend(("--enable", "image_generation", "-i", str(reference),
                  "-C", str(cwd), "-"))
    return value


def _event_objects(stream):
    """Walk JSONL items, including nested image-generation results."""
    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        yield from walk(event)


def _is_png(data):
    """Check PNG framing and CRCs, rather than renaming JPEG/WebP to .png."""
    if not data.startswith(PNG_SIGNATURE):
        return False
    offset = len(PNG_SIGNATURE)
    seen_header = seen_data = False
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        tag = data[offset + 4:offset + 8]
        end = offset + 8 + size
        if end + 4 > len(data):
            return False
        crc = struct.unpack_from(">I", data, end)[0]
        if zlib.crc32(data[offset + 4:end]) & 0xFFFFFFFF != crc:
            return False
        if not seen_header:
            if tag != b"IHDR" or size != 13:
                return False
            seen_header = True
        if tag == b"IDAT":
            seen_data = True
        if tag == b"IEND":
            return size == 0 and seen_data and end + 4 == len(data)
        offset = end + 4
    return False


def collect_images(home, stream):
    """Collect only this fresh round's home; never follow external event paths."""
    home = home.resolve()
    generated = home / "generated_images"
    paths = sorted(generated.rglob("*")) if generated.is_dir() else []
    objects = list(_event_objects(stream))
    for obj in objects:
        for key in ("savedPath", "saved_path"):
            value = obj.get(key)
            if isinstance(value, str):
                path = Path(value)
                paths.append(path if path.is_absolute() else home / path)

    seen_paths, seen_hashes = set(), set()

    def unique_png(data):
        if not _is_png(data):
            return False
        digest = hashlib.sha256(data).digest()
        if digest in seen_hashes:
            return False
        seen_hashes.add(digest)
        return True

    for path in paths:
        resolved = path.resolve()
        if home not in resolved.parents or resolved in seen_paths or not resolved.is_file():
            continue
        seen_paths.add(resolved)
        data = resolved.read_bytes()
        if unique_png(data):
            yield data

    for obj in objects:
        values = [obj.get("b64_json"), obj.get("image_base64")]
        if obj.get("type") == "image_generation_call":
            values.append(obj.get("result"))
        for value in values:
            if not isinstance(value, str):
                continue
            if value.startswith("data:image/png;base64,"):
                value = value.partition(",")[2]
            try:
                data = base64.b64decode(value, validate=True)
            except (ValueError, binascii.Error):
                continue
            if unique_png(data):
                yield data


def next_number(output):
    numbers = [int(match[1]) for path in output.iterdir()
               if (match := re.fullmatch(r"([0-9]+)\.png", path.name))]
    return max(numbers, default=0) + 1


@dataclass
class GenerationResult:
    written: list
    missing: int
    last_error: str = None


def generate(reference, template, output, count=DEFAULT_COUNT, model=DEFAULT_MODEL,
             max_rounds=DEFAULT_MAX_ROUNDS, codex="codex", timeout=900,
             effort=DEFAULT_EFFORT, skip_hashes=None):
    if count < 1 or max_rounds < 1 or timeout <= 0:
        raise ValueError("count, max-rounds, and timeout must be positive")
    reference = Path(reference).expanduser().resolve(strict=True)
    if not reference.is_file():
        raise ValueError("Reference must be an image file")
    executable = shutil.which(codex)
    if not executable:
        raise ValueError(f"Codex executable not found: {codex}")
    executable = str(Path(executable).resolve())
    source_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    output = Path(output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    number = next_number(output)
    written = []
    last_error = None
    for round_number in range(1, max_rounds + 1):
        remaining = count - len(written)
        prompt = fill_prompt(template, remaining, output)
        print(f"Round {round_number}/{max_rounds}: requesting {remaining} image(s)",
              file=sys.stderr, flush=True)
        # A fresh home each round prevents stale images, even when Codex reuses
        # filenames, and gives every call exactly the same isolation boundary.
        with tempfile.TemporaryDirectory(prefix="codex-batch-image-") as temporary:
            root = Path(temporary)
            home, cwd = root / "home", root / "work"
            catalog = prepare_home(source_home, home, model, remaining)
            cwd.mkdir()
            attached = cwd / ("reference" + reference.suffix.lower())
            shutil.copyfile(reference, attached)
            error = None
            try:
                run = subprocess.run(
                    command(executable, cwd, catalog, attached, root / "last-message.txt",
                            model=model, effort=effort),
                    input=prompt, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", timeout=timeout, check=False,
                    cwd=str(cwd), env=isolated_environment(home),
                )
                stdout, stderr = run.stdout, run.stderr
                returncode = run.returncode
            except subprocess.TimeoutExpired as exc:
                # TimeoutExpired may carry bytes even when text=True.
                stdout = exc.stdout or ""
                stderr = exc.stderr or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", errors="replace")
                returncode = None
                detail = (stderr or stdout or "no output").strip()[-2000:]
                error = f"Codex timed out after {timeout} seconds: {detail}"
            before = len(written)
            for data in collect_images(home, stdout):
                if skip_hashes is not None:
                    digest = hashlib.sha256(data).digest()
                    if digest in skip_hashes:
                        continue  # identical to an image already in the folder
                    skip_hashes.add(digest)
                destination = output / f"{number:02d}.png"
                # Exclusive creation protects existing output, including races.
                with destination.open("xb") as handle:
                    handle.write(data)
                written.append(destination)
                number += 1
                if len(written) == count:
                    break
            if returncode:
                detail = (stderr or stdout or "no output").strip()[-2000:]
                error = (
                    f"Codex failed with exit code {returncode}; kept {len(written)}/{count} "
                    f"image(s): {detail}"
                )
            if returncode == 0 and len(written) == before:
                last_message = root / "last-message.txt"
                detail = (last_message.read_text(encoding="utf-8-sig")
                          if last_message.is_file() else stderr or stdout)
                error = f"No PNG images returned: {detail.strip()[-2000:]}"
            if error:
                last_error = error
                print(error, file=sys.stderr, flush=True)
            print(f"Saved {len(written)}/{count} image(s)", file=sys.stderr, flush=True)
        if len(written) == count:
            return GenerationResult(written, 0, None)
    shortfall = (
        f"Only {len(written)}/{count} PNG images after {max_rounds} rounds; "
        "partial output was kept. Codex must have image_generation available "
        "and return separate PNG images."
    )
    print(shortfall, file=sys.stderr, flush=True)
    # Rounds that exit 0 with only some images record no error; still give the
    # report a reason instead of null for a short group.
    return GenerationResult(written, count - len(written), last_error or shortfall)


def existing_images(folder):
    """Valid / invalid PNG files already in folder (any *.png name)."""
    valid, invalid = [], []
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() == ".png":
            (valid if _is_png(path.read_bytes()) else invalid).append(path)
    return valid, invalid


def update_missing_json(folder, name, missing, last_error):
    """Update <parent>/missing.json for one group; delete it when nothing is missing."""
    path = folder.parent / "missing.json"
    if not path.is_file():
        if missing:
            path.write_text(json.dumps({"missing": {name: missing},
                                        "last_errors": {name: last_error}}, indent=2) + "\n",
                            encoding="utf-8")
        return path
    report = json.loads(path.read_text(encoding="utf-8"))
    report.setdefault("missing", {})[name] = missing
    report.setdefault("last_errors", {})[name] = last_error if missing else None
    if any(report["missing"].values()):
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    else:
        path.unlink()
    return path


def fill_existing(folder, target, reference, dry_run=False, generator=None, **options):
    """Top up a change_outfit folder to `target` valid images; returns (plan, result)."""
    folder = Path(folder).expanduser().resolve(strict=True)
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder}")
    valid, invalid = existing_images(folder)
    need = max(target - len(valid), 0)
    plan = {"folder": str(folder), "target": target, "existing_valid": len(valid),
            "existing_invalid": [p.name for p in invalid], "to_generate": need,
            "next_filename": f"{next_number(folder):02d}.png", "prompt": "change_outfit"}
    print(json.dumps(plan, ensure_ascii=False), file=sys.stderr, flush=True)
    if dry_run or need == 0:
        if need == 0 and not dry_run:
            update_missing_json(folder, folder.name, 0, None)
        return plan, None
    hashes = {hashlib.sha256(p.read_bytes()).digest() for p in valid}
    result = (generator or generate)(reference, CHANGE_OUTFIT_PROMPT, folder, need,
                                     skip_hashes=hashes, **options)
    update_missing_json(folder, folder.name, result.missing, result.last_error)
    return plan, result


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main_fill(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fill-existing", type=Path, required=True,
                        help="Existing change_outfit folder to top up")
    parser.add_argument("--target", type=positive_int, required=True,
                        help="Wanted number of valid change_outfit images (2N)")
    parser.add_argument("--reference", type=Path, required=True, help="Character sheet image path")
    parser.add_argument("--max-rounds", type=positive_int, default=DEFAULT_MAX_ROUNDS)
    parser.add_argument("--dry-run", action="store_true",
                        help="Only count existing images and print the plan; no Codex call")
    args = parser.parse_args(argv)
    try:
        plan, result = fill_existing(args.fill_existing, args.target, args.reference,
                                     dry_run=args.dry_run, max_rounds=args.max_rounds)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Error: {error}\n")
    if result is None:
        return 0
    for path in result.written:
        print(path)
    if result.missing:
        print(f"Error: {result.missing} image(s) still missing; see "
              f"{Path(plan['folder']).parent / 'missing.json'}", file=sys.stderr, flush=True)
        return 1
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if any(a == "--fill-existing" or a.startswith("--fill-existing=") for a in argv):
        return main_fill(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("n", type=positive_int,
                        help="keep_outfit N images, change_outfit 2N images")
    parser.add_argument("reference", type=Path, help="Character sheet image path")
    parser.add_argument("folder", type=Path, help="Save folder")
    args = parser.parse_args(argv)
    try:
        folder = args.folder.expanduser().resolve()
        reference = args.reference
        paths = []
        results = {}
        for name, template in PROMPTS:
            count = args.n * (2 if name == "change_outfit" else 1)
            result = generate(reference, template, folder / name, count)
            results[name] = result
            paths += result.written
        missing = {name: result.missing for name, result in results.items()}
        missing_path = folder / "missing.json"
        if any(missing.values()):
            missing_path.write_text(json.dumps({
                "missing": missing,
                "last_errors": {name: result.last_error for name, result in results.items()},
            }, indent=2) + "\n", encoding="utf-8")
        else:
            missing_path.unlink(missing_ok=True)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Error: {error}\n")
    for path in paths:
        print(path)
    if any(missing.values()):
        print(f"Error: {sum(missing.values())} image(s) still missing; see {missing_path}",
              file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
