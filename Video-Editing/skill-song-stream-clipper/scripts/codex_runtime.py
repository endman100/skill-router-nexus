from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


DEFAULT_CODEX_MODEL = "gpt-5.6-terra"
DEFAULT_SERVICE_TIER = "default"
MINIMUM_CLI_VERSION = (0, 144, 0)


def codex_version(path: Path) -> tuple[int, int, int]:
    try:
        result = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return (0, 0, 0)
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", result.stdout + result.stderr)
    return tuple(int(part) for part in match.groups()) if match else (0, 0, 0)


def find_codex(explicit_path: str = "") -> str:
    candidates: list[Path] = []
    configured = explicit_path or os.environ.get("CODEX_CLI_PATH", "")
    if configured:
        candidates.append(Path(configured).expanduser())
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        bundled = Path(local_app_data) / "OpenAI" / "Codex" / "bin"
        if bundled.is_dir():
            candidates.extend(bundled.rglob("codex.exe"))
    for executable in ("codex.exe", "codex.cmd", "codex"):
        resolved = shutil.which(executable)
        if resolved:
            candidates.append(Path(resolved))
    unique = {
        str(path.resolve()).lower(): path.resolve()
        for path in candidates
        if path.is_file()
    }
    if not unique:
        raise FileNotFoundError("Could not find a Codex CLI executable")
    versions = [(path, codex_version(path)) for path in unique.values()]
    selected, version = max(versions, key=lambda item: item[1])
    if version < MINIMUM_CLI_VERSION:
        found = ", ".join(
            f"{path}={'.'.join(map(str, value))}" for path, value in versions
        )
        raise RuntimeError(
            f"GPT-5.6 requires Codex CLI 0.144.0 or newer. Detected: {found}"
        )
    return str(selected)


def build_exec_command(
    *,
    codex_exe: str,
    model: str,
    reasoning_effort: str,
    service_tier: str,
    workdir: Path,
    last_message_path: Path,
) -> list[str]:
    command = [
        codex_exe,
        "--model",
        model,
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
    ]
    if service_tier:
        command.extend(["-c", f'service_tier="{service_tier}"'])
    command.extend(
        [
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-C",
            str(workdir.resolve()),
            "-o",
            str(last_message_path.resolve()),
            "-",
        ]
    )
    return command
