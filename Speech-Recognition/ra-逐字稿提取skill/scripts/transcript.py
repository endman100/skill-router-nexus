#!/usr/bin/env python3
"""Resolve social media, then consume an Agent-produced ASR Router result."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ENV_FILE = SKILL_DIR / ".env"
LOADED_ENV_FILES: list[str] = []


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    real_path = str(path.resolve())
    if real_path in LOADED_ENV_FILES:
        return
    LOADED_ENV_FILES.append(real_path)
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ENV_FILE)
for parent in SKILL_DIR.parents:
    _load_dotenv(parent / ".env")


def default_output_dir() -> str:
    configured = os.getenv("TRANSCRIPT_OUTPUT_DIR")
    if configured:
        return configured
    for parent in SKILL_DIR.parents:
        candidate = parent / "01-内容生产" / "视频工作台" / ".internal" / "洗稿"
        if candidate.exists():
            return str(candidate)
    return str(SKILL_DIR / "outputs")


QUSHUIYIN_API_BASE = os.getenv(
    "QUSHUIYIN_API_BASE", "https://api.guijianpan.com"
).rstrip("/")
QUSHUIYIN_API_KEY = os.getenv("QUSHUIYIN_API_KEY", "")


def is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def detect_platform(url: str) -> str:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if "xiaohongshu" in host or "xhslink" in host:
        return "xiaohongshu"
    if "douyin" in host:
        return "douyin"
    return "unknown"


def safe_filename(name: str, max_len: int = 60) -> str:
    name = re.sub(r"https?://\S+", "", name or "")
    name = re.sub(r"#\S+", "", name)
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:max_len].strip("_") or "transcript"


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method.upper())
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    if data is not None and not request.has_header("Content-Type"):
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:400]}") from exc


def split_title_and_text(value: str) -> tuple[str, str]:
    if "||" not in value:
        return value.strip(), ""
    title, text = value.split("||", 1)
    return title.strip(), text.strip()


def first_string_field(items: list[Any], field_names: tuple[str, ...]) -> str:
    for item in items:
        if isinstance(item, str) and item.startswith("http"):
            return item
        if isinstance(item, dict):
            for name in field_names:
                value = item.get(name)
                if isinstance(value, str) and value.startswith("http"):
                    return value
    return ""


def resolve_qushuiyin(source_url: str, platform: str) -> dict[str, Any]:
    if not QUSHUIYIN_API_KEY:
        raise RuntimeError("QUSHUIYIN_API_KEY not configured")
    endpoint = f"{QUSHUIYIN_API_BASE}/waterRemoveDetail/xxmQsyByAk"
    query = urllib.parse.urlencode({"ak": QUSHUIYIN_API_KEY, "link": source_url})
    data = http_json("GET", f"{endpoint}?{query}", timeout=30)
    content = data.get("content") if isinstance(data, dict) else None
    if not isinstance(data, dict) or data.get("code") != "10000" or not isinstance(content, dict):
        raise RuntimeError((data.get("msg") if isinstance(data, dict) else "") or "Qushuiyin resolve failed")

    title, embedded_text = split_title_and_text(content.get("title", "") or "")
    full_text = content.get("originText", "") or content.get("msg", "") or ""
    if full_text.startswith(("http://", "https://")) and embedded_text:
        full_text = embedded_text
    video_url = content.get("url", "") or first_string_field(
        content.get("videoList") or content.get("video_list") or [],
        ("url", "playUrl", "play_url", "downloadUrl", "download_url"),
    )
    if not video_url:
        raise RuntimeError("Qushuiyin did not return a video URL")
    return {
        "source_url": source_url,
        "platform": platform,
        "title": title,
        "author": content.get("author", "") or "",
        "full_text": full_text,
        "video_url": video_url,
        "cover_url": content.get("cover", "") or content.get("headUrl", "") or "",
        "raw": data,
    }


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def load_router_result(path: Path) -> dict[str, Any]:
    payload = load_json_object(path, "ASR Router result")
    if not payload.get("schema_version"):
        raise ValueError("ASR input is not a normalized Router result")
    if payload.get("provider") != "paraformer":
        raise ValueError("this locked workflow requires preferred_provider=paraformer")
    if not str(payload.get("text", "")).strip():
        raise ValueError("Router result has no transcript text")
    if not isinstance(payload.get("segments"), list):
        raise ValueError("Router result has no segments array")
    return payload


def mmss(seconds: float | int | None) -> str:
    seconds = int(seconds or 0)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def text_chunks(text: str, max_chars: int = 180) -> list[str]:
    pieces = re.split(r"(?<=[。！？!?])", text.strip())
    chunks: list[str] = []
    buffer = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if buffer and len(buffer) + len(piece) > max_chars:
            chunks.append(buffer)
            buffer = piece
        else:
            buffer = (buffer + piece).strip()
    if buffer:
        chunks.append(buffer)
    return chunks or ([text.strip()] if text.strip() else [])


def build_body(text: str, segments: list[Any]) -> str:
    valid = [
        item for item in segments
        if isinstance(item, dict) and str(item.get("text", "")).strip()
    ]
    if not valid:
        return "\n\n".join(
            f"## {index}. 逐字稿\n\n{chunk}"
            for index, chunk in enumerate(text_chunks(text), 1)
        )

    sections: list[tuple[float | None, float | None, list[str]]] = []
    lines: list[str] = []
    section_start: float | None = None
    section_end: float | None = None
    for item in valid:
        start = float(item["start"]) if item.get("start") is not None else None
        end = float(item["end"]) if item.get("end") is not None else None
        if section_start is None:
            section_start = start
        section_end = end if end is not None else section_end
        lines.append(str(item["text"]).strip())
        duration = (
            section_end - section_start
            if section_start is not None and section_end is not None
            else 0
        )
        if len(lines) >= 4 or duration >= 35:
            sections.append((section_start, section_end, lines))
            lines = []
            section_start = None
            section_end = None
    if lines:
        sections.append((section_start, section_end, lines))

    parts = []
    for index, (start, end, section_lines) in enumerate(sections, 1):
        stamp = (
            f"\n\n[{mmss(start)} - {mmss(end)}]"
            if start is not None or end is not None
            else ""
        )
        parts.append(
            f"## {index}. 逐字稿{stamp}\n\n" + "\n\n".join(section_lines)
        )
    return "\n\n".join(parts)


def build_markdown(
    source_url: str,
    resolved: dict[str, Any],
    result: dict[str, Any],
    override_title: str | None = None,
) -> str:
    title = override_title or resolved.get("title") or "视频逐字稿"
    platform_zh = {
        "douyin": "抖音",
        "xiaohongshu": "小红书",
    }.get(str(resolved["platform"]), str(resolved["platform"]))
    header = [
        f"# {title}",
        "",
        f"> 来源: {source_url}",
        f"> 平台: {platform_zh}",
        "> 转写: qushuiyin 解析 + ASR Router（Paraformer profile）",
    ]
    if result.get("task_id"):
        header.append(f"> 任务: {result['task_id']}")
    if resolved.get("author"):
        header.append(f"> 作者: {resolved['author']}")
    return (
        "\n".join(header)
        + "\n\n"
        + build_body(str(result["text"]), result["segments"]).strip()
        + "\n"
    )


def run(
    input_path: str,
    *,
    title: str | None = None,
    output_dir: str | None = None,
    save_md: bool = True,
    resolve_only: bool = False,
    resolve_output: Path | None = None,
    resolved_input: Path | None = None,
    asr_result: Path | None = None,
) -> bool:
    if not is_url(input_path):
        return False
    platform = detect_platform(input_path)
    if platform not in {"douyin", "xiaohongshu"}:
        return False

    if resolved_input is not None:
        resolved = load_json_object(resolved_input, "resolved media")
        if resolved.get("source_url") and resolved["source_url"] != input_path:
            raise ValueError("resolved media source_url does not match input URL")
    else:
        resolved = resolve_qushuiyin(input_path, platform)
    if not str(resolved.get("video_url", "")).startswith(("http://", "https://")):
        raise ValueError("resolved media has no reachable video_url")

    if resolve_output is not None:
        destination = resolve_output.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(resolved, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(destination, file=sys.stderr)
    if resolve_only:
        print(json.dumps(resolved, ensure_ascii=False, indent=2))
        return True
    if asr_result is None:
        raise ValueError(
            "invoke asr-router with preferred_provider=paraformer and "
            "fallback_allowed=false, then pass --asr-result"
        )

    result = load_router_result(asr_result)
    picked_title = title or resolved.get("title") or "视频逐字稿"
    final_md = build_markdown(input_path, resolved, result, title)
    if save_md:
        out_dir = Path(output_dir or default_output_dir())
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{safe_filename(str(picked_title))}_transcript.md"
        out_file.write_text(final_md, encoding="utf-8")
        print(f"[OK] 逐字稿已保存: {out_file}", file=sys.stderr)
    print(final_md)
    return True


def mask(value: str) -> str:
    return value[:6] + "…" + value[-4:] if len(value) > 12 else "***"


def doctor() -> int:
    print("ra-逐字稿提取skill 业务依赖检查")
    if not QUSHUIYIN_API_KEY:
        print("✗ QUSHUIYIN_API_KEY 未配置")
        return 1
    print(f"✓ QUSHUIYIN_API_KEY: {mask(QUSHUIYIN_API_KEY)}")
    print(f"✓ QUSHUIYIN_API_BASE: {QUSHUIYIN_API_BASE}")
    print("i ASR provider 由 Agent 通过 asr-router 检查与执行")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve media and consume an ASR Router transcript"
    )
    parser.add_argument("input", nargs="?", help="抖音/小红书视频 URL")
    parser.add_argument("--title", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--no-save", dest="save_md", action="store_false")
    parser.add_argument("--resolve-only", action="store_true")
    parser.add_argument("--resolve-output", type=Path, default=None)
    parser.add_argument("--resolved-input", type=Path, default=None)
    parser.add_argument("--asr-result", type=Path, default=None)
    parser.add_argument("--doctor", action="store_true")
    parser.set_defaults(save_md=True)
    args = parser.parse_args()

    if args.doctor:
        raise SystemExit(doctor())
    if not args.input:
        parser.error("缺少 input 参数")
    if not run(
        args.input,
        title=args.title,
        output_dir=args.output_dir,
        save_md=args.save_md,
        resolve_only=args.resolve_only,
        resolve_output=args.resolve_output,
        resolved_input=args.resolved_input,
        asr_result=args.asr_result,
    ):
        raise SystemExit("当前 skill 只支持抖音/小红书视频 URL")


if __name__ == "__main__":
    main()
