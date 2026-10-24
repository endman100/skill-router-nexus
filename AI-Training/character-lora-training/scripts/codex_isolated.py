"""Isolated `codex exec` launcher (same isolation pattern as codex_clean.py). Used by codex_caption_v2.py and codex_upscale.py.

temp CODEX_HOME (auth.json copy + one-model catalog), --ephemeral, --ignore-user-config,
--ignore-rules, --strict-config, web_search disabled, workspace-write sandbox (-C workdir is the
only write root), network off, /tmp excluded, all extra features disabled.
"""
import json, os, shlex, shutil, subprocess, tempfile
from pathlib import Path

DEFAULT_MODEL = "gpt-6.1-sol"
DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "code_mode_host", "shell_snapshot", "apps",
    "plugins", "remote_plugin", "plugin_sharing", "browser_use",
    "browser_use_external", "browser_use_full_cdp_access", "computer_use",
    "in_app_browser", "hooks", "image_generation", "multi_agent",
    "workspace_dependencies", "skill_mcp_dependency_install",
    "tool_call_mcp_elicitation", "tool_suggest", "goals", "guardian_approval",
    "auth_elicitation", "personality",
)


def prepare_home(source, target, instructions, model=DEFAULT_MODEL):
    target.mkdir(mode=0o700)
    shutil.copy2(source / "auth.json", target / "auth.json")
    (target / "auth.json").chmod(0o600)
    cache = json.loads((source / "models_cache.json").read_text(encoding="utf-8-sig"))
    entry = next((item for item in cache["models"] if item["slug"] == model), None)
    if entry is None:
        raise ValueError(f"Model {model!r} is absent from models_cache.json")
    entry.update(
        input_modalities=["text", "image"], base_instructions=instructions,
        model_messages={"instructions_template": instructions,
                        "instructions_variables": None, "approvals": None},
        include_skills_usage_instructions=False, supports_reasoning_summaries=True,
        supports_parallel_tool_calls=False, supports_search_tool=False,
        experimental_supported_tools=[], tool_mode="direct",
    )
    catalog = target / "model_catalog.json"
    catalog.write_text(json.dumps({"models": [entry]}), encoding="utf-8")
    return catalog


def isolated_environment(home):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("CODEX_")}
    env["CODEX_HOME"] = str(home.resolve())
    return env


def command(codex, cwd, catalog, last_message, model, effort, image_generation):
    value = [
        codex, "exec", "--json", "--output-last-message", str(last_message),
        "--ephemeral", "--ignore-user-config", "--ignore-rules", "--strict-config",
        "--skip-git-repo-check", "--model", model,
        "-c", f"model_reasoning_effort={json.dumps(effort)}",
        "-c", 'approval_policy="never"',
        "-c", "skills.include_instructions=false", "-c", "skills.bundled.enabled=false",
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
    exceptions = ("shell_tool", "unified_exec") + (("image_generation",) if image_generation else ())
    for feature in DISABLED_FEATURES:
        if feature not in exceptions:
            value.extend(("--disable", feature))
    value.extend(("--disable", "memories"))
    if image_generation:
        value.extend(("--enable", "image_generation"))
    value.extend(("-C", str(cwd), "-"))
    return value


def run_isolated(prompt, instructions, inputs, effort="medium", model=DEFAULT_MODEL,
                 timeout=3600, image_generation=False, log_dir=None, label="call", codex="codex"):
    """inputs: list of (source_path, name_in_workdir_input). Returns (root, work, status, home)."""
    codex = str(Path(shutil.which(codex)).resolve())
    source_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    root = Path(tempfile.mkdtemp(prefix=f"codex-{label}-"))
    home, work = root / "home", root / "work"
    catalog = prepare_home(source_home, home, instructions, model)
    (work / "input").mkdir(parents=True)
    (work / "output").mkdir()
    for src, name in inputs:
        (work / "input" / name).parent.mkdir(parents=True, exist_ok=True)
        if Path(src).is_dir():
            shutil.copytree(src, work / "input" / name)
        else:
            shutil.copyfile(src, work / "input" / name)
    argv = command(codex, work, catalog, root / "last-message.txt", model, effort, image_generation)
    status, timed_out = 0, False
    try:
        run = subprocess.run(argv, input=prompt.replace("{CODEX_HOME}", str(home)),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             encoding="utf-8", errors="replace", timeout=timeout, check=False,
                             cwd=str(work), env=isolated_environment(home))
        stdout, stderr, status = run.stdout, run.stderr, run.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""; stderr = exc.stderr or ""; status, timed_out = 124, True
        stdout = stdout.decode("utf-8", "replace") if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr
    (root / "codex-events.jsonl").write_text(stdout or "", encoding="utf-8")
    (root / "codex-stderr.log").write_text(stderr or "", encoding="utf-8")
    if log_dir:
        d = Path(log_dir) / label
        d.mkdir(parents=True, exist_ok=True)
        (d / "argv.txt").write_text(shlex.join(argv) + "\n", encoding="utf-8")
        (d / "prompt.txt").write_text(prompt, encoding="utf-8")
        (d / "inputs.json").write_text(json.dumps([[str(s), n] for s, n in inputs], ensure_ascii=False, indent=1), encoding="utf-8")
        for n in ("codex-events.jsonl", "codex-stderr.log", "last-message.txt"):
            if (root / n).is_file():
                shutil.copyfile(root / n, d / n)
        (d / "status.json").write_text(json.dumps({"status": status, "timed_out": timed_out, "root": str(root)}), encoding="utf-8")
    return root, work, status, home
