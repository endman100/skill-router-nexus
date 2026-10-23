#!/usr/bin/env python3
"""Headless Grok Build calls, session artifacts, logs and retries."""
import argparse, io, json, os, re, subprocess, sys, uuid
from pathlib import Path
from PIL import Image

DEFAULT = "/home/box/.local/bin/grok"
DEFAULT = DEFAULT if Path(DEFAULT).exists() else "grok"
IMAGE_SCHEMA = {"type": "object", "properties": {"output_file": {"type": "string"}},
                "required": ["output_file"], "additionalProperties": False}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf-8")


def options(parser, only=False):
    parser.add_argument("--grok-bin", default=DEFAULT)
    parser.add_argument("--model", default="grok-4.7")
    parser.add_argument("--effort")
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    if only:
        parser.add_argument("--only", nargs="+", help="只處理指定檔名")


def run_grok(prompt, cwd, log_dir, name, *, schema=None, web=False,
             model=None, effort=None, timeout=3600, grok_bin=DEFAULT, extra_args=()):
    cwd, log_dir = Path(cwd).resolve(), Path(log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    # Keep logs from earlier invocations as well as retries.
    base = log_dir / name
    number = 2
    while Path(str(base) + ".prompt.md").exists():
        base = log_dir / f"{name}_{number}"
        number += 1
    def log(suffix, value):
        Path(str(base) + suffix).write_text(value, "utf-8")
    prompt_file = Path(str(base) + ".prompt.md")
    log(".prompt.md", prompt)
    session_id = str(uuid.uuid4())
    argv = [str(grok_bin), "--prompt-file", str(prompt_file), "--output-format", "json",
            "--cwd", str(cwd), "--always-approve", "--session-id", session_id]
    # Headless Grok Build rejects --add-dir; it can still read absolute paths outside cwd.
    if not web:
        argv.append("--disable-web-search")
    if model:
        argv += ["-m", model]
    if effort:
        argv += ["--reasoning-effort", effort]
    if schema is not None:
        argv += ["--json-schema", json.dumps(schema, ensure_ascii=False)]
    argv += list(extra_args)
    log(".argv.json", json.dumps(argv, ensure_ascii=False))
    try:
        run = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=timeout)
        status, stdout, stderr = run.returncode, run.stdout, run.stderr
    except subprocess.TimeoutExpired as exc:
        status, stdout, stderr = 124, exc.stdout or "", exc.stderr or ""
    except OSError as exc:
        status, stdout, stderr = 1, "", str(exc)
    def decoded(value):
        return value.decode("utf-8", "replace") if isinstance(value, bytes) else value
    stdout, stderr = decoded(stdout), decoded(stderr)
    log(".stdout.json", stdout); log(".stderr.txt", stderr); log(".exit.txt", str(status) + "\n")
    error, data = None, None
    try:
        data = json.loads(stdout)
        if not isinstance(data, dict):
            raise ValueError("stdout must be a JSON object")
    except ValueError as exc:
        error, data = str(exc), None
    root = Path(os.environ.get("GROK_SESSIONS_ROOT", str(Path.home() / ".grok/sessions"))).expanduser()
    session_dir = next(root.glob(f"*/{session_id}"), None)
    images, viewed = [], []
    if session_dir:
        images = sorted((session_dir / "images").glob("*.jpg"),
                        key=lambda p: (int(p.stem) if p.stem.isdigit() else 0, p.name))
        history = session_dir / "chat_history.jsonl"
        if history.exists():
            def strings(value):
                if isinstance(value, str):
                    yield value
                elif isinstance(value, dict):
                    for child in value.values():
                        yield from strings(child)
                elif isinstance(value, list):
                    for child in value:
                        yield from strings(child)
            for line in history.read_text("utf-8").splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                def tool_results(value):
                    if isinstance(value, dict):
                        if value.get("role") == "tool" or "tool" in str(value.get("type", "")).lower():
                            yield from strings(value)
                        else:
                            for child in value.values():
                                yield from tool_results(child)
                    elif isinstance(value, list):
                        for child in value:
                            yield from tool_results(child)
                for value in tool_results(event):
                    viewed += [Path(s.strip()).resolve() for s in re.findall(r"Read image file: ([^\n\r]+)", value)]
    return dict(returncode=status, stdout_json=data, structured=data.get("structuredOutput") if data else None,
                session_id=session_id, session_dir=session_dir, images=images,
                viewed_images=viewed, error=error, log=str(base))


def retry(prompt, cwd, log_dir, name, args, *, accept=None, **kwargs):
    last_error = "no attempts"
    for attempt in range(args.retries + 1):
        result = run_grok(prompt, cwd, log_dir, f"{name}_try{attempt + 1}",
                          grok_bin=args.grok_bin, model=args.model, effort=args.effort,
                          timeout=args.timeout, **kwargs)
        try:
            if result["returncode"] or result["error"]:
                raise ValueError(f"Grok exit={result['returncode']}: {result['error'] or 'see stderr'}")
            if kwargs.get("schema") is not None and result["structured"] is None:
                raise ValueError("Missing structuredOutput")
            return (accept(result) if accept else result), None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            last_error = str(exc)
            print(f"{name}: {last_error}", file=sys.stderr)
    return None, last_error


def generated_image(result):
    """Use only artifacts inside this call's fresh session."""
    value = (result["structured"] or {}).get("output_file")
    if value:
        path = Path(value)
        if not path.is_absolute() and result["session_dir"]:
            path = result["session_dir"] / path
        path = path.resolve()
        if result["session_dir"] and result["session_dir"].resolve() in path.parents and path.is_file():
            return path
        raise ValueError("output_file is not an image in this Grok session")
    raise ValueError("No final image path reported")


def png_bytes(path):
    buffer = io.BytesIO()
    with Image.open(path) as im:
        im.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def report(out, results):
    failed = [r for r in results if not r.get("ok")]
    write_json(out / "summary.json", dict(results=results, passed=len(results) - len(failed), failed=failed))
    write_json(out / "failed.json", failed)
    print(f"passed={len(results) - len(failed)} failed={len(failed)}")
    return int(bool(failed))


def entry(main):
    try:
        return main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
