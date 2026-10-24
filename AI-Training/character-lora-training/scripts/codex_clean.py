#!/usr/bin/env python3
"""逐張以獨立 Codex 執行清理 SFW 圖片，參照角色設定圖並支援續跑。"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from ws import check_sheet_approved, parse_args

DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_EFFORT = "high"
DEFAULT_TIMEOUT = 480
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
    "timeout": "逾時",
    "codex_failed": "Codex 執行失敗",
    "moderation_blocked": "圖像生成遭 moderation 阻擋",
}
HANDOFF_REASONS = ("timeout", "codex_failed", "moderation_blocked")
TASK_INSTRUCTIONS = (
    "Clean the single input image using the supplied character sheet to identify the target. "
    "Check quality, reject line-art and monochrome, crop to the target, remove text with "
    "image generation and compare with the original. Use the image viewer and shell tools; "
    "write only in the workdir. Read generated images from CODEX_HOME/generated_images. "
    "Write either the output PNG or a rejection. No web access."
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


def build_prompt(target, source, home):
    return f"""請清理目標角色：{target}。
用圖片檢視工具開啟 ./input/source/{source.name} 與 ./input/character-sheet.png，
以角色設定圖比對，確認原圖中有目標角色；沒有則拒收 not_present。
檢查原圖品質：拒收線稿、草稿、黑白或單色圖（lineart_or_monochrome），
解析度過低、模糊、壓縮失真嚴重或角色太小則拒收 low_quality。
使用 shell 工具（例如 Python/Pillow）裁切至僅保留目標角色與少量邊界；失敗記錄 crop_failed。
若有文字、對話框、音效字或浮水印，使用 image_generation 移除，再與原圖及裁切圖比較，
確認臉、頭髮、眼睛、服裝、顏色、姿勢及比例保持不變；去字失真則拒收 text_removal_distorted。
沒有文字則跳過去字。其他無法處理的情況記錄 refused。
生成圖片位於 {home / 'generated_images'}（CODEX_HOME/generated_images）。
用圖片檢視工具檢查最終圖，與原圖及角色設定圖比較，確認角色、裁切、去字與品質均正確。
成功存為 ./output/{source.stem}.png（PNG）；拒收則寫 ./output/rejected.json，
格式為單筆物件或單筆陣列，例如：
[{{"filename": "{source.name}", "reason": "not_present", "reason_zh": "角色不存在", "detail": "具體說明"}}]
原因代碼與標籤：{json.dumps({k: v for k, v in REASON_LABELS.items() if k not in HANDOFF_REASONS}, ensure_ascii=False)}。
僅在工作目錄內寫入（含暫存檔），不得存取網路。
"""


def atomic_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf-8")
    temporary.replace(path)


def clean_image(source, sheet, target, destination, executable, source_home,
                model, effort, timeout, keep_workdir):
    root = Path(tempfile.mkdtemp(prefix="codex-clean-"))
    home, work = root / "home", root / "work"
    logs = destination / "logs" / source.stem
    logs.mkdir(parents=True, exist_ok=True)
    status, timed_out = None, False
    stdout = stderr = ""
    try:
        catalog = prepare_home(source_home, home, model)
        (work / "input/source").mkdir(parents=True)
        (work / "output").mkdir()
        shutil.copyfile(source, work / "input/source" / source.name)
        shutil.copyfile(sheet, work / "input/character-sheet.png")
        argv = command(executable, work, catalog, root / "last-message.txt", model, effort)
        prompt = build_prompt(target, source, home)
        (logs / "argv.txt").write_text(shlex.join(argv) + "\n", "utf-8")
        (logs / "prompt.txt").write_text(prompt, "utf-8")
        try:
            run = subprocess.run(
                argv, input=prompt, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", timeout=timeout,
                check=False, cwd=str(work), env=isolated_environment(home))
            stdout, stderr, status = run.stdout, run.stderr, run.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or "", exc.stderr or ""
            stdout = stdout.decode("utf-8", "replace") if isinstance(stdout, bytes) else stdout
            stderr = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr
            status, timed_out = 124, True
        last = root / "last-message.txt"
        last_message = last.read_text("utf-8", errors="replace") if last.is_file() else ""
        (logs / "codex-events.jsonl").write_text(stdout, "utf-8")
        (logs / "codex-stderr.log").write_text(stderr, "utf-8")
        (logs / "last-message.txt").write_text(last_message, "utf-8")
        atomic_json(logs / "status.json", dict(status=status, timed_out=timed_out, root=str(root)))
        output = work / "output" / (source.stem + ".png")
        reason, detail = None, ""
        if not timed_out and status == 0 and output.is_file():
            return output.read_bytes(), None
        if "moderation_blocked" in stdout + stderr + last_message:
            reason, detail = "moderation_blocked", "Codex 回報 moderation_blocked。"
        elif timed_out:
            reason, detail = "timeout", f"超過每張 {timeout} 秒。"
        elif status != 0:
            reason, detail = "codex_failed", f"Codex exit status: {status}"
        else:
            rejection = work / "output/rejected.json"
            if rejection.is_file():
                try:
                    record = json.loads(rejection.read_text("utf-8-sig"))
                    record = record[0] if isinstance(record, list) and record else record
                    if isinstance(record, dict) and record.get("reason") in REASON_LABELS:
                        reason, detail = record["reason"], record.get("detail", "")
                except (ValueError, UnicodeError):
                    pass
            if reason is None:
                reason, detail = "codex_failed", "未產生輸出圖片或拒收紀錄。"
        record = dict(filename=source.name, reason=reason, reason_zh=REASON_LABELS[reason], detail=detail)
        if reason in HANDOFF_REASONS:
            record["handoff"] = "grok"
        return None, record
    finally:
        if keep_workdir:
            print(f"Kept temporary directory: {root} (workdir: {work})", file=sys.stderr, flush=True)
        else:
            shutil.rmtree(root)


def clean(target, input_dir, output_dir, sheet,
          model=DEFAULT_MODEL, effort=DEFAULT_EFFORT, timeout=DEFAULT_TIMEOUT,
          jobs=3, codex="codex", keep_workdir=False, only=None):
    input_dir = Path(input_dir).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    destination = output_dir / "codex_clean"
    sheet = Path(sheet).expanduser().resolve()
    check_sheet_approved(sheet)
    paths = [p for p in sorted(input_dir.iterdir())
             if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS and (not only or p.name in only)]
    destination.mkdir(parents=True, exist_ok=True)
    rejected_file = destination / "rejected.json"
    rejected = json.loads(rejected_file.read_text("utf-8")) if rejected_file.exists() else []
    rejected_names = {e["filename"] for e in rejected}
    pending = [p for p in paths if not (destination / (p.stem + ".png")).is_file() and p.name not in rejected_names]
    executable = shutil.which(codex)
    if pending and not executable:
        raise ValueError(f"Codex executable not found: {codex}")
    executable = str(Path(executable).resolve()) if executable else codex
    source_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()

    def save_summary():
        atomic_json(rejected_file, rejected)
        atomic_json(destination / "summary.json", dict(
            inputs=len(paths),
            processed=sum((destination / (p.stem + ".png")).is_file() for p in paths),
            rejected=len(rejected), rejected_by_reason=dict(Counter(e["reason"] for e in rejected)),
            moderation_blocked=[e["filename"] for e in rejected if e["reason"] == "moderation_blocked"]))

    # Only this thread publishes outputs and manifests; workers own separate logs/workdirs.
    save_summary()
    done = len(paths) - len(pending)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(clean_image, p, sheet, target, destination, executable, source_home,
                               model, effort, timeout, keep_workdir): p for p in pending}
        for future in as_completed(futures):
            source = futures[future]
            try:
                image, record = future.result()
            except Exception as exc:
                image, record = None, dict(filename=source.name, reason="codex_failed",
                                           reason_zh=REASON_LABELS["codex_failed"], detail=str(exc), handoff="grok")
            if image is not None:
                temporary = destination / (source.stem + ".png.tmp")
                temporary.write_bytes(image)
                temporary.replace(destination / (source.stem + ".png"))
                result = "kept"
            else:
                rejected.append(record)
                result = f"handoff grok ({record['reason']})" if record.get("handoff") else f"rejected ({record['reason']})"
            save_summary()
            done += 1
            print(f"[{done}/{len(paths)}] {source.name}: {result}", flush=True)
    blocked = [e["filename"] for e in rejected if e["reason"] == "moderation_blocked"]
    print("moderation_blocked: " + (", ".join(blocked) or "（無）"), flush=True)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Work title and character name as one verbatim string")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--sheet", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, metavar="SECONDS")
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--codex", default="codex", help="Codex executable path")
    parser.add_argument("--keep-workdir", action="store_true")
    parser.add_argument("--only", nargs="+")
    return parser


def main(argv=None):
    args = parse_args(build_parser(), "clean", argv)
    try:
        return clean(**vars(args))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
