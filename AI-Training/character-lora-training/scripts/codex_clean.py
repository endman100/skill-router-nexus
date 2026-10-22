#!/usr/bin/env python3
"""Clean character images through exactly one isolated Codex task (stdlib only)."""

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile


DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_EFFORT = "high"
DEFAULT_TIMEOUT = 3600
DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "code_mode_host", "shell_snapshot", "apps",
    "plugins", "remote_plugin", "plugin_sharing", "browser_use",
    "browser_use_external", "browser_use_full_cdp_access", "computer_use",
    "in_app_browser", "hooks", "image_generation", "multi_agent",
    "workspace_dependencies", "skill_mcp_dependency_install",
    "tool_call_mcp_elicitation", "tool_suggest", "goals", "guardian_approval",
    "auth_elicitation", "personality",
)
ENABLED_EXCEPTIONS = ("shell_tool", "unified_exec", "image_generation")
IMAGE_EXTENSIONS = frozenset((
    ".png", ".apng", ".jpg", ".jpeg", ".jpe", ".jfif", ".gif", ".webp",
    ".bmp", ".dib", ".tif", ".tiff", ".ico", ".cur", ".avif", ".avifs",
    ".heic", ".heics", ".heif", ".heifs", ".hif", ".jxl", ".jp2", ".j2k",
    ".jpf", ".jpx", ".jpm", ".mj2", ".svg", ".svgz", ".psd", ".psb",
    ".pbm", ".pgm", ".ppm", ".pnm", ".pam", ".pfm", ".tga", ".pcx",
    ".xbm", ".xpm", ".dds", ".exr", ".hdr", ".pic", ".qoi", ".raw",
    ".dng", ".cr2", ".cr3", ".nef", ".arw", ".orf", ".rw2", ".raf",
))
REASON_LABELS = {
    "not_present": "角色不存在",
    "crop_failed": "裁切失敗",
    "text_removal_distorted": "去字失真",
    "low_quality": "品質過低",
    "lineart_or_monochrome": "線稿或黑白圖",
    "refused": "拒絕處理",
    "unprocessed": "未處理",
}
TASK_INSTRUCTIONS = (
    "Infer the target character's appearance from the work title, character name, and recurring "
    "character across all input images; write an appearance profile in the workdir. "
    "Pre-screen inputs as labeled 8-image contact sheets, then identify, crop, remove text, and reject low-quality, line-art, and black-and-white/monochrome images using that profile. "
    "Use the image viewer, shell tools, and image generation; write only in the workdir. "
    "Read generated images from CODEX_HOME/generated_images and copy chosen results into output. "
    "Account for every input in output images or rejected.json. No web access."
)


def prepare_home(source, target, model=DEFAULT_MODEL):
    """Reference isolation: source auth/cache only; fresh auth + one-model catalog."""
    target.mkdir(mode=0o700)
    shutil.copy2(source / "auth.json", target / "auth.json")
    (target / "auth.json").chmod(0o600)
    cache = json.loads((source / "models_cache.json").read_text(encoding="utf-8-sig"))
    entry = next((item for item in cache["models"] if item["slug"] == model), None)
    if entry is None:
        raise ValueError(f"Model {model!r} is absent from {source / 'models_cache.json'}")
    entry.update(
        input_modalities=["text", "image"],
        base_instructions=TASK_INSTRUCTIONS,
        model_messages={
            "instructions_template": TASK_INSTRUCTIONS,
            "instructions_variables": None,
            "approvals": None,
        },
        include_skills_usage_instructions=False,
        supports_reasoning_summaries=True,
        supports_parallel_tool_calls=False,
        supports_search_tool=False,
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
    # -C is the sole sandbox write root; do not mix named permissions profiles.
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
        "-c", 'web_search="disabled"',
        "--sandbox", "workspace-write",
        "-c", "sandbox_workspace_write.network_access=false",
        "-c", "sandbox_workspace_write.exclude_tmpdir_env_var=true",
        "-c", "sandbox_workspace_write.exclude_slash_tmp=true",
        "-c", f"model_catalog_json={json.dumps(str(catalog.resolve()))}",
    ]
    for feature in DISABLED_FEATURES:
        if feature not in ENABLED_EXCEPTIONS:
            value.extend(("--disable", feature))
    value.extend(("--disable", "memories", "--enable", "image_generation",
                  "-C", str(cwd), "-"))
    return value


def input_mapping(paths):
    """Reserve unique stems first, then disambiguate collisions deterministically."""
    counts = Counter(path.stem.casefold() for path in paths)
    used = {path.stem.casefold() for path in paths if counts[path.stem.casefold()] == 1}
    entries = []
    for path in paths:
        stem = path.stem
        if counts[stem.casefold()] > 1:
            base = f"{stem}__{path.suffix[1:].lower()}"
            stem, number = base, 2
            while stem.casefold() in used:
                stem = f"{base}__{number}"
                number += 1
            used.add(stem.casefold())
        entries.append({"filename": path.name, "input_filename": stem + path.suffix,
                        "output_filename": stem + ".png"})
    return entries


def build_prompt(target, inputs, home):
    inventory = json.dumps(inputs, ensure_ascii=False, indent=2)
    labels = json.dumps(REASON_LABELS, ensure_ascii=False)
    return f"""請清理以下目標（作品名稱與角色名稱）的圖片：
{target}
以下 JSON 是檔名對照表（filename 是原始檔名，input_filename 是工作副本，output_filename 是最終檔名）：
{inventory}

開始逐張處理前，必須先用圖片檢視工具開啟並瀏覽 ./input 的全部輸入圖片，
找出在整批圖片中反覆出現的角色。結合上述作品名稱與角色名稱，推斷目標角色的外觀，
辨識其臉、頭髮、眼睛、服裝、顏色等區別特徵，將推斷依據與外觀描述寫入
工作目錄的 ./character_profile.md（不可寫入 ./output），作為後續逐張辨識的依據。

第一段：拼圖初篩。用 shell 工具（Python/Pillow）把 ./input 的圖片每 8 張拼成一張拼圖，
存在工作目錄的 ./review/sheets/，每格都標上該圖的 input_filename。用圖片檢視工具逐張看拼圖，
一次判斷 8 格：與 ./character_profile.md 比較，角色不存在的記錄 not_present / 角色不存在；
線稿、草稿、黑白或單色圖記錄 lineart_or_monochrome / 線稿或黑白圖；明顯模糊或極度破損的
記錄 low_quality / 品質過低。拿不準的格子不可直接拒收，必須單獨開啟原圖再判斷。
只有初篩通過的圖片進入第二段。

第二段：逐張細處理。初篩通過的圖片一次只處理一張，必須逐張用圖片檢視工具開啟原圖：
(1) 角色辨識：確認原圖中確實有目標角色；若沒有，拒收並記錄 not_present / 角色不存在。
(2) 裁切：使用 shell 工具（例如可用的 Python/Pillow）裁切，只保留目標角色及少量邊界，
中間檔寫在工作目錄。無法完成裁切則記錄 crop_failed / 裁切失敗。
(3) 去字：若裁切圖含有文字、對話框、音效字或浮水印，必須使用圖片生成工具 image_generation
移除這些元素。將結果與原始裁切圖比較，確認僅移除文字，角色的臉、頭髮、眼睛、服裝、
顏色、姿勢及比例均保持不變。若角色失真，重新生成再比較；重做仍失敗就視為不可用，
記錄 text_removal_distorted / 去字失真。沒有文字的圖片跳過去字步驟。
(4) 品質檢查：拼圖看不出輕微模糊、壓縮雜訊和小字，必須在此用原圖再確認。逐張檢查來源、裁切圖及最終圖的品質。若解析度過低、模糊、
壓縮失真嚴重，或裁切後角色仍太小等，導致圖片品質過低，拒收並記錄
low_quality / 品質過低，不將該圖放入 ./output。
(5) 線稿與黑白圖：初篩漏掉的線稿、草稿、黑白或單色圖（沒有正常上色）一律拒收，記錄
lineart_or_monochrome / 線稿或黑白圖，不將該圖放入 ./output。
生成圖片位於 {home / 'generated_images'}（CODEX_HOME/generated_images）；
將選定結果複製到 ./output。每張最終圖必須是 PNG，儲存為 ./output/<source stem>.png，
其中 source stem 是工作副本 input_filename 的檔名主體，務必遵循對照表的 output_filename。
因其他原因無法處理時，記錄 refused / 拒絕處理。

全部處理後再次逐張檢查：每張輸出都要用圖片檢視工具開啟，與其來源及 ./character_profile.md 比較，
確認角色、裁切及去字均正確，品質足夠；品質過低則移除輸出並記錄 low_quality / 品質過低。
核對每一張輸入都有輸出或拒收紀錄，補完遺漏並修正問題，
確認工作真正完成後，撰寫 ./output/rejected.json，格式為 JSON 陣列，例如：
[{{"filename": "原始輸入檔名.png", "reason": "not_present", "reason_zh": "角色不存在", "detail": "具體說明"}}]
filename 必須使用對照表的原始 filename，不是重新命名的工作副本。沒有拒收時寫 []。
原因代碼與標籤：{labels}。unprocessed 由外層補記；請完成所有可處理圖片。
最終訊息彙總輸入、成功、各原因拒收的數量。
僅在工作目錄內寫入（含暫存檔），不得存取網路。
"""


def regular_file(path):
    """lstat never follows a symlink, including dangling links."""
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except FileNotFoundError:
        return False


def open_regular(path):
    """Open without following links and verify the opened descriptor is regular."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_NONBLOCK", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or path.is_symlink():
            raise OSError(f"Not a regular file: {path}")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def copy_regular(source, target):
    with open_regular(source) as reader, target.open("xb") as writer:
        shutil.copyfileobj(reader, writer)


def text_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def reconcile(inputs, filenames, raw_rejected):
    """Account for the current run only, without decoding any images."""
    notes, rejected = [], {}
    mapping = {entry["output_filename"][:-4]: entry["filename"] for entry in inputs}
    processed, extras = set(), []
    for filename in filenames:
        path = Path(filename)
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            original = mapping.get(path.stem)
            if original is None:
                extras.append(filename)
            else:
                processed.add(original)
    try:
        entries = json.loads(raw_rejected) if raw_rejected is not None else []
        if not isinstance(entries, list):
            raise ValueError("expected a JSON list")
    except (ValueError, UnicodeError) as exc:
        notes.append(f"Invalid rejected.json: {exc}; raw file retained if present")
        entries = []
    originals = {entry["filename"] for entry in inputs}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("filename"), str):
            notes.append("Ignored malformed rejection entry")
            continue
        name = entry["filename"]
        if name not in originals:
            notes.append(f"Ignored rejection for unknown input: {name!r}")
            continue
        if name in processed:
            notes.append(f"Kept output; dropped rejection for {name!r}")
            continue
        if name in rejected:
            notes.append(f"Ignored duplicate rejection for {name!r}")
            continue
        code = entry.get("reason")
        detail = entry.get("detail", "")
        if not isinstance(detail, str):
            detail = json.dumps(detail, ensure_ascii=False)
        if not isinstance(code, str) or code not in REASON_LABELS:
            detail = f"Unknown reason code: {json.dumps(code, ensure_ascii=False)}. {detail}"
            code = "refused"
        rejected[name] = {"filename": name, "reason": code,
                          "reason_zh": REASON_LABELS[code], "detail": detail}
    for entry in inputs:
        name = entry["filename"]
        if name not in processed and name not in rejected:
            rejected[name] = {"filename": name, "reason": "unprocessed",
                              "reason_zh": REASON_LABELS["unprocessed"],
                              "detail": "No output image or valid rejection entry was produced."}
    final = [rejected[entry["filename"]] for entry in inputs if entry["filename"] in rejected]
    return final, processed, extras, notes


def export_results(work, root, destination, inputs, status, returncode, timed_out):
    output = work / "output"
    if output.is_symlink() or not output.is_dir():
        raise OSError(f"Output directory is missing or is a symlink: {output}")
    files = [path for path in sorted(output.iterdir()) if regular_file(path)]
    raw = None
    manifest = output / "rejected.json"
    if manifest in files:
        with open_regular(manifest) as reader:
            raw = reader.read().decode("utf-8-sig", errors="replace")
    final, processed, extras, notes = reconcile(inputs, [p.name for p in files], raw)
    report = {
        "inputs": len(inputs), "processed": len(processed), "rejected": len(final),
        "rejected_by_reason": dict(Counter(entry["reason"] for entry in final)),
        "unprocessed": sum(entry["reason"] == "unprocessed" for entry in final),
        "extras": len(extras), "extra_files": extras, "codex_exit_status": status,
        "codex_returncode": returncode, "timed_out": timed_out,
        "filename_mapping": inputs, "notes": notes,
    }
    # Keep raw model metadata alongside the reconciled manifest, including invalid JSON.
    exports = [(path, "rejected.codex.json" if path.name == "rejected.json" else path.name)
               for path in files]
    logs = ("codex-events.jsonl", "codex-stderr.log", "last-message.txt")
    names = [name for _, name in exports] + list(logs) + ["rejected.json", "summary.json"]
    if len(set(names)) != len(names):
        raise FileExistsError("Inner output conflicts with a reserved report/log filename")
    # Check every ancestor before mkdir; never resolve an export destination symlink.
    for parent in (destination, *destination.parents):
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise FileExistsError(f"Destination is not a regular directory: {parent}")
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        if os.path.lexists(destination / name):
            raise FileExistsError(f"Destination already exists: {destination / name}; no files overwritten")
    for source, name in exports:
        copy_regular(source, destination / name)
    for name in logs:
        source = root / name
        if regular_file(source):
            copy_regular(source, destination / name)
        else:
            with (destination / name).open("x", encoding="utf-8"):
                pass
    for name, value in (("rejected.json", final), ("summary.json", report)):
        with (destination / name).open("x", encoding="utf-8") as writer:
            json.dump(value, writer, ensure_ascii=False, indent=2)
            writer.write("\n")
    return report


def clean(target, input_dir, output_dir,
          model=DEFAULT_MODEL, effort=DEFAULT_EFFORT, timeout=DEFAULT_TIMEOUT,
          codex="codex", keep_workdir=False):
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number of seconds")
    input_dir = Path(input_dir).expanduser().resolve(strict=True)
    if not input_dir.is_dir():
        raise ValueError("input_dir must be a directory")
    paths = [path for path in sorted(input_dir.iterdir())
             if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file()]
    inputs = input_mapping(paths)
    output_dir = Path(output_dir).expanduser().absolute()
    destination = output_dir / "codex_clean"
    executable = shutil.which(codex)
    if not executable:
        raise ValueError(f"Codex executable not found: {codex}")
    executable = str(Path(executable).resolve())
    source_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    root = Path(tempfile.mkdtemp(prefix="codex-clean-"))
    home, work = root / "home", root / "work"
    try:
        catalog = prepare_home(source_home, home, model)
        (work / "input").mkdir(parents=True)
        (work / "output").mkdir()
        for source, entry in zip(paths, inputs):
            shutil.copyfile(source, work / "input" / entry["input_filename"])
        if keep_workdir:
            print(f"Workdir: {work}", flush=True)
        argv = command(executable, work, catalog, root / "last-message.txt", model, effort)
        print(f"Argv: {shlex.join(argv)}", flush=True)
        stdout = stderr = ""
        status, returncode, timed_out = 0, None, False
        try:
            # Exactly one launch. No retries, probes, or follow-up calls.
            run = subprocess.run(
                argv, input=build_prompt(target, inputs, home), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                timeout=timeout, check=False, cwd=str(work), env=isolated_environment(home),
            )
            stdout, stderr, returncode = run.stdout, run.stderr, run.returncode
            status = returncode if returncode >= 0 else 128 - returncode
            if status:
                print(f"Codex exited with status {status}", file=sys.stderr)
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout, exc.stderr
            status, timed_out = 124, True
            print(f"Codex timed out after {timeout:g} seconds", file=sys.stderr)
        except OSError as exc:
            status, stderr = 1, f"Could not launch Codex: {exc}\n"
        for name, value in (("codex-events.jsonl", stdout), ("codex-stderr.log", stderr)):
            (root / name).write_text(text_value(value), encoding="utf-8")
        if stderr:
            print(text_value(stderr), file=sys.stderr, end="" if text_value(stderr).endswith("\n") else "\n")
        try:
            report = export_results(work, root, destination, inputs, status, returncode, timed_out)
        except (OSError, ValueError):
            keep_workdir = True
            print(f"Copy failed; results kept in workdir: {work}", file=sys.stderr)
            raise
        print(f"Destination: {destination}")
        print(f"Inputs: {report['inputs']}; processed: {report['processed']}; "
              f"rejected: {report['rejected']}; unprocessed: {report['unprocessed']}; extras: {report['extras']}")
        print(f"Rejected by reason: {json.dumps(report['rejected_by_reason'], ensure_ascii=False)}")
        print(f"Codex exit status: {status}")
        for note in report["notes"]:
            print(f"Note: {note}", file=sys.stderr)
        for name in report["extra_files"]:
            print(f"Extra image: {name}")
        return status
    finally:
        if keep_workdir:
            print(f"Kept temporary directory: {root} (workdir: {work})", file=sys.stderr)
        else:
            shutil.rmtree(root)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Work title and character name as one verbatim string")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, metavar="SECONDS")
    parser.add_argument("--codex", default="codex", help="Codex executable path")
    parser.add_argument("--keep-workdir", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return clean(**vars(args))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
