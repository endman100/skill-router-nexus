#!/usr/bin/env python3
"""Launch one isolated Codex collection task; Python standard library only."""

import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import subprocess
import sys
import tempfile


DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_EFFORT = "high"
DEFAULT_TIMEOUT = 3600
OUTPUT_NOTE = (
    'Save the images in the current working directory and write sources.json '
    'there as a JSON list with each image\'s filename and source URL, '
    'for example [{"filename": "image.png", "source_url": "https://example.com/image.png"}].'
)
# Exact reference tuple/order; the only enabled exceptions are the shell tools.
DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "code_mode_host", "shell_snapshot", "apps",
    "plugins", "remote_plugin", "plugin_sharing", "browser_use",
    "browser_use_external", "browser_use_full_cdp_access", "computer_use",
    "in_app_browser", "hooks", "image_generation", "multi_agent",
    "workspace_dependencies", "skill_mcp_dependency_install",
    "tool_call_mcp_elicitation", "tool_suggest", "goals", "guardian_approval",
    "auth_elicitation", "personality",
)
ENABLED_EXCEPTIONS = ("shell_tool", "unified_exec")

# Classification, not validation: a recognized suffix OR signature suffices.
# No image parser, decoder, size check, or content inspection is used.
IMAGE_EXTENSIONS = frozenset((
    ".png", ".apng", ".jpg", ".jpeg", ".jpe", ".jfif", ".gif", ".webp",
    ".bmp", ".dib", ".tif", ".tiff", ".ico", ".cur", ".avif", ".avifs",
    ".heic", ".heics", ".heif", ".heifs", ".hif", ".jxl", ".jp2", ".j2k",
    ".jpf", ".jpx", ".jpm", ".mj2", ".svg", ".svgz", ".psd", ".psb",
    ".pbm", ".pgm", ".ppm", ".pnm", ".pam", ".pfm", ".tga", ".pcx",
    ".xbm", ".xpm", ".dds", ".exr", ".hdr", ".pic", ".qoi", ".raw",
    ".dng", ".cr2", ".cr3", ".nef", ".arw", ".orf", ".rw2", ".raf",
))


def make_prompt(query):
    return f"幫我收集 {query} 可以用來訓練 LoRA 的資料\n\n{OUTPUT_NOTE}"


def prepare_home(source, target, model=DEFAULT_MODEL):
    """Read only source auth/cache and prepare auth plus a one-model catalog."""
    target.mkdir(mode=0o700)
    shutil.copy2(source / "auth.json", target / "auth.json")
    (target / "auth.json").chmod(0o600)
    cache = json.loads((source / "models_cache.json").read_text(encoding="utf-8-sig"))
    entry = next((item for item in cache["models"] if item["slug"] == model), None)
    if entry is None:
        raise ValueError(f"Model {model!r} is absent from {source / 'models_cache.json'}")
    entry.update(
        input_modalities=["text", "image"],
        base_instructions=OUTPUT_NOTE,
        model_messages={
            "instructions_template": OUTPUT_NOTE,
            "instructions_variables": None,
            "approvals": None,
        },
        include_skills_usage_instructions=False,
        supports_reasoning_summaries=True,
        supports_parallel_tool_calls=False,
        supports_search_tool=True,
        experimental_supported_tools=[],
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


def command(codex, cwd, catalog, last_message,
            model=DEFAULT_MODEL, effort=DEFAULT_EFFORT):
    # codex-cli 0.163.0 exec --help accepts workspace-write. Use that legacy
    # sandbox configuration alone, without default_permissions/permissions.*:
    # mixing a named profile with sandbox_workspace_write can conflict. -C is
    # the sole writable root; both automatic temporary roots are excluded.
    value = [
        codex, "exec", "--json", "--output-last-message", str(last_message),
        "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config",
        "--skip-git-repo-check", "--model", model,
        "-c", f"model_reasoning_effort={json.dumps(effort)}",
        "-c", 'approval_policy="never"',
        "-c", "skills.include_instructions=false",
        "-c", "skills.bundled.enabled=false",
        "-c", "include_apps_instructions=false",
        "-c", "include_collaboration_mode_instructions=false",
        "-c", "include_environment_context=false",
        "-c", "include_permissions_instructions=false",
        "-c", 'web_search="live"',
        "--sandbox", "workspace-write",
        "-c", "sandbox_workspace_write.network_access=true",
        "-c", "sandbox_workspace_write.exclude_tmpdir_env_var=true",
        "-c", "sandbox_workspace_write.exclude_slash_tmp=true",
        "-c", f"model_catalog_json={json.dumps(str(catalog.resolve()))}",
    ]
    for feature in DISABLED_FEATURES:
        if feature not in ENABLED_EXCEPTIONS:
            value.extend(("--disable", feature))
    value.extend(("--disable", "memories", "-C", str(cwd), "-"))
    return value


def is_image(path):
    """Recognize extensions or magic bytes, without decoding an image."""
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return True
    with path.open("rb") as handle:
        header = handle.read(512)
    if header.startswith((
        b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"BM",
        b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+", b"\x00\x00\x01\x00",
        b"\x00\x00\x02\x00", b"8BPS", b"DDS ", b"\x76\x2f\x31\x01",
        b"#?RADIANCE", b"#?RGBE", b"qoif", b"\xff\x0a",
        b"\x00\x00\x00\x0cJXL \r\n\x87\n", b"\x00\x00\x00\x0cjP  \r\n\x87\n",
    )):
        return True
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return True
    if header[4:8] == b"ftyp" and any(
        header[offset:offset + 4] in (
            b"avif", b"avis", b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"
        ) for offset in range(8, min(len(header), 64), 4)
    ):
        return True
    if header[:2] in (b"P1", b"P2", b"P3", b"P4", b"P5", b"P6", b"P7", b"PF", b"Pf"):
        return header[2:3] in b" \t\r\n"
    return b"<svg" in header.lstrip(b"\xef\xbb\xbf \t\r\n")


def result_files(workdir):
    """Walk regular files in the workdir, preserving relative filenames.

    Every regular file is a result (images, captions, notes, ...); images are
    only *classified* for the counts, never filtered.
    """
    images, others = [], []
    for directory, dirs, files in os.walk(workdir, followlinks=False):
        parent = Path(directory)
        dirs[:] = sorted(name for name in dirs if not (parent / name).is_symlink())
        for name in sorted(files):
            path = parent / name
            if path.is_symlink() or not path.is_file() or path == workdir / "sources.json":
                continue
            (images if is_image(path) else others).append(path)
    manifest = workdir / "sources.json"
    if manifest.is_symlink() or not manifest.is_file():
        manifest = None
    return images, others, manifest


def copy_results(workdir, destination):
    """Copy every result file unmodified; fail on any name collision."""
    images, others, manifest = result_files(workdir)
    files = images + others + ([manifest] if manifest else [])
    destination.mkdir(parents=True, exist_ok=True)
    # Preflight the complete set before writing; exclusive creation also
    # protects existing files if another process creates one after preflight.
    for source in files:
        relative = source.relative_to(workdir)
        target = destination / relative
        if os.path.lexists(target):
            raise FileExistsError(f"Destination already exists: {target}; no files overwritten")
        for parent in target.parents:
            if parent == destination.parent:
                break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise FileExistsError(f"Destination directory is not a regular directory: {parent}")
    for source in files:
        target = destination / source.relative_to(workdir)
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as reader, target.open("xb") as writer:
            shutil.copyfileobj(reader, writer)

    entries, error = [], None
    if manifest:
        try:
            entries = json.loads(manifest.read_text(encoding="utf-8-sig"))
            if not isinstance(entries, list):
                raise ValueError("expected a JSON list")
        except (ValueError, UnicodeError) as exc:
            entries = []
            error = f"Invalid sources.json (copied unchanged): {exc}"
    names = {path.relative_to(workdir).as_posix() for path in images}
    recorded = set()
    missing = 0
    for entry in entries:
        filename = entry.get("filename") if isinstance(entry, dict) else None
        # Match only copied relative names; never follow manifest paths outside
        # the result set. Malformed/missing filenames count as missing files.
        name = str(PurePosixPath(filename)) if isinstance(filename, str) else None
        if name in names:
            recorded.add(name)
        else:
            missing += 1
    return {
        "images_copied": len(images),
        "other_files_copied": len(others),
        "source_entries": len(entries),
        "entries_missing_file": missing,
        "images_without_entry": len(names - recorded),
        "produced": bool(images or manifest),
        "error": error,
    }


def collect(query, save_dir, model=DEFAULT_MODEL, effort=DEFAULT_EFFORT,
            timeout=DEFAULT_TIMEOUT, codex="codex", keep_workdir=False):
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number of seconds")
    source_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    destination = Path(save_dir).expanduser().resolve() / "codex"
    root = Path(tempfile.mkdtemp(prefix="codex-collect-"))
    home, workdir = root / "home", root / "work"
    try:
        workdir.mkdir()
        if keep_workdir:
            print(f"Workdir: {workdir}", flush=True)
        catalog = prepare_home(source_home, home, model)
        argv = command(codex, workdir, catalog, root / "last-message.txt", model, effort)
        print(f"Argv: {shlex.join(argv)}", flush=True)
        status = 0
        try:
            # Exactly one exec call; no probing, retries, or follow-up model calls.
            run = subprocess.run(
                argv, input=make_prompt(query), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8",
                errors="replace", timeout=timeout, check=False,
                cwd=str(workdir), env=isolated_environment(home),
            )
            if run.stderr:
                print(run.stderr, file=sys.stderr, end="" if run.stderr.endswith("\n") else "\n")
            if run.returncode:
                print(f"Codex exited with status {run.returncode}", file=sys.stderr)
                status = run.returncode if run.returncode > 0 else 128 - run.returncode
        except subprocess.TimeoutExpired:
            print(f"Codex timed out after {timeout:g} seconds", file=sys.stderr)
            status = 124
        except OSError as exc:
            print(f"Could not launch Codex: {exc}", file=sys.stderr)
            status = 1

        print(f"Destination: {destination}", flush=True)
        try:
            report = copy_results(workdir, destination)
        except OSError:
            # Never lose collected results because the copy failed (e.g. a
            # name collision in an existing save dir): keep the temp root.
            keep_workdir = True
            print(f"Copy failed; results kept in workdir: {workdir}", file=sys.stderr)
            raise
        print(f"Image files copied: {report['images_copied']}")
        print(f"Other files copied: {report['other_files_copied']}")
        print(f"sources.json entries: {report['source_entries']}")
        print(f"Entries whose file is missing: {report['entries_missing_file']}")
        print(f"Image files without an entry: {report['images_without_entry']}")
        if report["error"]:
            print(report["error"], file=sys.stderr)
            status = status or 1
        if not report["produced"]:
            print("Nothing was produced (no images or sources.json).", file=sys.stderr)
            status = status or 1
        return status
    finally:
        if not keep_workdir:
            shutil.rmtree(root)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="work title and character name as one verbatim string")
    parser.add_argument("save_dir", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, metavar="SECONDS")
    parser.add_argument("--codex", default="codex", help="Codex executable path")
    parser.add_argument("--keep-workdir", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return collect(**vars(args))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
