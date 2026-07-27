#!/usr/bin/env python3
"""Audit a Threads Markdown draft against writing and paper-mode policies.

Usage:
    python validate.py <draft.md> [--paper] [--blacklist FILE] [--whitelist FILE]

Whitelist phrases are explicit exceptions. They are removed from the scan copy
before blacklist matching, so an approved longer phrase can contain a normally
blocked shorter phrase without producing a false positive.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from typing import Iterable


SKILL_DIR = Path(__file__).resolve().parent
DEFAULT_BLACKLIST = SKILL_DIR / "blacklist.txt"
DEFAULT_WHITELIST = SKILL_DIR / "whitelist.txt"
POST_SEPARATOR_RE = re.compile(r"(?m)^\s*---\s*$")
IMAGE_LINE_RE = re.compile(
    r'^\s*!\[(?P<alt>[^\]]+)\]\('
    r'(?P<target><[^>]+>|[^)\s]+)'
    r'(?:\s+(?:"[^"]*"|\'[^\']*\'))?'
    r'\)\s*$'
)
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
DOI_RE = re.compile(r"(?i)\b10\.\d{4,9}/[-._;()/:A-Z0-9]+")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]\n]+\]\([^)]+\)")
CITATION_MARKER_RE = re.compile(r"\[\[?\d+(?:\s*[-,]\s*\d+)*\]?\]")
FIGURE_ALT_RE = re.compile(r"^Figure\s+[A-Za-z0-9][A-Za-z0-9._-]*：\s*\S.*$")
FIGURE_FILENAME_RE = re.compile(
    r"^figure-\d{2,3}\.(?:png|jpe?g|webp)$",
    re.IGNORECASE,
)
PAPER_SOURCE_PATTERNS = (
    ("Hugging Face", re.compile(r"hugging\s*face", re.IGNORECASE)),
    ("arXiv", re.compile(r"arxiv", re.IGNORECASE)),
    ("OpenReview", re.compile(r"open\s*review", re.IGNORECASE)),
    ("Semantic Scholar", re.compile(r"semantic\s+scholar", re.IGNORECASE)),
    ("Papers with Code", re.compile(r"papers\s+with\s+code", re.IGNORECASE)),
    ("ResearchGate", re.compile(r"research\s*gate", re.IGNORECASE)),
    ("bioRxiv", re.compile(r"biorxiv", re.IGNORECASE)),
    ("medRxiv", re.compile(r"medrxiv", re.IGNORECASE)),
    ("SSRN", re.compile(r"\bssrn\b", re.IGNORECASE)),
    ("Google Scholar", re.compile(r"google\s+scholar", re.IGNORECASE)),
    ("ACL Anthology", re.compile(r"acl\s+anthology", re.IGNORECASE)),
    ("IEEE Xplore", re.compile(r"ieee\s+xplore", re.IGNORECASE)),
    ("ACM Digital Library", re.compile(r"acm\s+digital\s+library", re.IGNORECASE)),
    ("SpringerLink", re.compile(r"springer\s*link", re.IGNORECASE)),
    ("Zenodo", re.compile(r"\bzenodo\b", re.IGNORECASE)),
    ("PubMed", re.compile(r"\bpubmed\b", re.IGNORECASE)),
    ("Crossref", re.compile(r"\bcrossref\b", re.IGNORECASE)),
)


def load_terms(path: Path) -> list[str]:
    """Load non-empty, non-comment terms while preserving file order."""
    terms: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        term = raw_line.strip()
        if term and not term.startswith("#") and term not in terms:
            terms.append(term)
    return terms


def audit_text(
    text: str,
    *,
    blacklist: Iterable[str],
    whitelist: Iterable[str],
) -> dict[str, object]:
    """Return blacklist failures and whitelist matches for plain text."""
    blacklist_terms = [term for term in blacklist if term]
    whitelist_terms = [term for term in whitelist if term]

    whitelist_hits = [term for term in whitelist_terms if term in text]
    scan_text = text
    for term in sorted(whitelist_hits, key=len, reverse=True):
        scan_text = scan_text.replace(term, "")

    blacklist_hits = [term for term in blacklist_terms if term in scan_text]
    return {
        "ok": not blacklist_hits,
        "blacklist_hits": blacklist_hits,
        "whitelist_hits": whitelist_hits,
    }


def _paper_source_hits(text: str) -> list[str]:
    return [name for name, pattern in PAPER_SOURCE_PATTERNS if pattern.search(text)]


def audit_structure(text: str) -> list[str]:
    posts = POST_SEPARATOR_RE.split(text.strip())
    errors: list[str] = []
    if len(posts) != 4:
        errors.append(f"成品必須有 4 篇 Post，目前解析到 {len(posts)} 篇")
    for post_index, post in enumerate(posts, start=1):
        if not post.strip():
            errors.append(f"第 {post_index} 篇不可為空")
    return errors


def _is_supported_image(path: Path) -> bool:
    with path.open("rb") as image_file:
        header = image_file.read(12)
    suffix = path.suffix.casefold()
    signature_ok = (
        suffix == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n")
    ) or (
        suffix in {".jpg", ".jpeg"} and header.startswith(b"\xff\xd8\xff")
    ) or (
        suffix == ".webp"
        and header.startswith(b"RIFF")
        and header[8:12] == b"WEBP"
    )
    if not signature_ok:
        return False

    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        return True

    try:
        with Image.open(path) as image:
            image.verify()
    except (OSError, SyntaxError, UnidentifiedImageError):
        return False
    return True


def _local_figure_path(
    target: str,
    *,
    source_directory: Path,
    expected_figure_directory: Path,
) -> tuple[Path | None, str | None]:
    clean_target = target[1:-1] if target.startswith("<") and target.endswith(">") else target
    if (
        not clean_target
        or clean_target.startswith(("/", "\\", "~", "//"))
        or URI_SCHEME_RE.match(clean_target)
    ):
        return None, "附圖必須使用成品旁的本機相對路徑"

    resolved = (source_directory / Path(clean_target)).resolve()
    try:
        resolved.relative_to(source_directory.resolve())
    except ValueError:
        return None, "附圖路徑不得離開成品所在目錄"
    if resolved.parent != expected_figure_directory.resolve():
        return None, f"附圖必須直接放在指定附圖目錄：{expected_figure_directory.name}"
    if not FIGURE_FILENAME_RE.fullmatch(resolved.name):
        return None, "附圖檔名必須使用 figure-01.png 形式，並限 PNG、JPEG 或 WebP"
    if not resolved.is_file():
        return None, f"找不到附圖檔案：{clean_target}"
    if not _is_supported_image(resolved):
        return None, f"附圖不是可辨識的 PNG、JPEG 或 WebP：{clean_target}"
    return resolved, None


def audit_paper_layout(text: str, *, source: Path) -> dict[str, object]:
    """Audit source suppression, per-post placement, and image uniqueness."""
    errors: list[str] = []
    image_paths: list[Path] = []
    source_directory = source.resolve().parent
    expected_figure_directory = source_directory / f"{source.stem}-figures"
    posts = POST_SEPARATOR_RE.split(text.strip())

    for post_index, post in enumerate(posts, start=1):
        lines = [line.strip() for line in post.splitlines() if line.strip()]
        image_rows: list[tuple[int, re.Match[str]]] = []
        for line_index, line in enumerate(lines):
            match = IMAGE_LINE_RE.fullmatch(line)
            if match:
                image_rows.append((line_index, match))
                if not FIGURE_ALT_RE.fullmatch(match.group("alt")):
                    errors.append(
                        f"第 {post_index} 篇附圖 alt text 必須包含 Figure 編號與 caption"
                    )
            elif line.startswith("!["):
                errors.append(f"第 {post_index} 篇含有無法解析的 Markdown 圖片語法")

        if not image_rows:
            errors.append(f"第 {post_index} 篇正文下方缺少論文附圖")
            continue

        first_image_row = image_rows[0][0]
        if first_image_row == 0:
            errors.append(f"第 {post_index} 篇必須先有正文，再放附圖")
        for line in lines[first_image_row:]:
            if not IMAGE_LINE_RE.fullmatch(line):
                errors.append(f"第 {post_index} 篇的圖片之後仍有正文")
                break

        for _, match in image_rows:
            resolved, path_error = _local_figure_path(
                match.group("target"),
                source_directory=source_directory,
                expected_figure_directory=expected_figure_directory,
            )
            if path_error:
                errors.append(f"第 {post_index} 篇：{path_error}")
            elif resolved is not None:
                image_paths.append(resolved)

    path_counts: dict[str, int] = {}
    hash_counts: dict[str, int] = {}
    for path in image_paths:
        normalized = str(path).casefold()
        path_counts[normalized] = path_counts.get(normalized, 0) + 1
        with path.open("rb") as image_file:
            digest = hashlib.file_digest(image_file, "sha256").hexdigest()
        hash_counts[digest] = hash_counts.get(digest, 0) + 1

    duplicate_paths = [path for path, count in path_counts.items() if count > 1]
    duplicate_hashes = [digest for digest, count in hash_counts.items() if count > 1]
    if duplicate_paths:
        errors.append("同一個附圖路徑被使用超過一次")
    if duplicate_hashes:
        errors.append("偵測到內容相同但檔名可能不同的重複附圖")

    referenced_paths = {path.resolve() for path in image_paths}
    unreferenced_paths: list[str] = []
    if expected_figure_directory.is_dir():
        for entry in expected_figure_directory.iterdir():
            if not entry.is_file() or entry.resolve() not in referenced_paths:
                unreferenced_paths.append(entry.name)
    if unreferenced_paths:
        errors.append(
            "指定附圖目錄含有未在文章中使用的檔案或目錄："
            + "、".join(sorted(unreferenced_paths))
        )

    source_hits = _paper_source_hits(text)
    return {
        "paper_source_hits": source_hits,
        "paper_errors": errors,
        "paper_image_count": len(image_paths),
        "duplicate_image_paths": duplicate_paths,
        "duplicate_image_hashes": duplicate_hashes,
        "unreferenced_figure_entries": unreferenced_paths,
    }


def audit_file(
    source: Path,
    *,
    blacklist_path: Path = DEFAULT_BLACKLIST,
    whitelist_path: Path = DEFAULT_WHITELIST,
    paper_mode: bool = False,
) -> dict[str, object]:
    text = source.read_text(encoding="utf-8")
    result = audit_text(
        text,
        blacklist=load_terms(blacklist_path),
        whitelist=load_terms(whitelist_path),
    )
    result.update(
        {
            "format_errors": [],
            "structure_errors": audit_structure(text),
            "url_hits": URL_RE.findall(text),
            "citation_hits": [
                *DOI_RE.findall(text),
                *MARKDOWN_LINK_RE.findall(text),
                *CITATION_MARKER_RE.findall(text),
            ],
            "paper_source_hits": [],
            "paper_errors": [],
            "paper_image_count": 0,
            "duplicate_image_paths": [],
            "duplicate_image_hashes": [],
            "unreferenced_figure_entries": [],
        }
    )
    if source.suffix.casefold() == ".json":
        result["format_errors"] = [
            "輸入必須是最終 Markdown；JSON 不再是有效的成品格式"
        ]
    if paper_mode:
        result.update(audit_paper_layout(text, source=source))
    result["ok"] = not any(
        (
            result["blacklist_hits"],
            result["format_errors"],
            result["structure_errors"],
            result["url_hits"],
            result["citation_hits"],
            result["paper_source_hits"],
            result["paper_errors"],
        )
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit a Markdown draft against text blacklist and whitelist files."
    )
    parser.add_argument("source", type=Path, help="UTF-8 Markdown or text draft")
    parser.add_argument(
        "--paper",
        action="store_true",
        help="啟用論文來源隱藏、每篇附圖、相對路徑與去重審核",
    )
    parser.add_argument(
        "--blacklist", type=Path, default=DEFAULT_BLACKLIST, help="blacklist term file"
    )
    parser.add_argument(
        "--whitelist", type=Path, default=DEFAULT_WHITELIST, help="whitelist term file"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = audit_file(
            args.source,
            blacklist_path=args.blacklist,
            whitelist_path=args.whitelist,
            paper_mode=args.paper,
        )
    except FileNotFoundError as error:
        print(f"[錯誤] 找不到檔案：{error.filename}")
        return 2
    except UnicodeDecodeError as error:
        print(f"[錯誤] 檔案不是有效的 UTF-8 文字：{error}")
        return 2

    whitelist_hits = result["whitelist_hits"]
    blacklist_hits = result["blacklist_hits"]
    format_errors = result["format_errors"]
    structure_errors = result["structure_errors"]
    url_hits = result["url_hits"]
    citation_hits = result["citation_hits"]
    paper_source_hits = result["paper_source_hits"]
    paper_errors = result["paper_errors"]

    if whitelist_hits:
        print("[白名單] " + "、".join(whitelist_hits))
    else:
        print("[白名單] 無命中")

    if blacklist_hits:
        print("[黑名單] " + "、".join(blacklist_hits))
    else:
        print("[黑名單] 無命中")

    for error in format_errors:
        print(f"[格式錯誤] {error}")
    for error in structure_errors:
        print(f"[結構錯誤] {error}")
    if url_hits:
        print("[網址] " + "、".join(url_hits))
    else:
        print("[網址] 無命中")
    if citation_hits:
        print("[引用] " + "、".join(citation_hits))
    else:
        print("[引用] 無命中")

    if args.paper:
        if paper_source_hits:
            print("[論文來源名稱] " + "、".join(paper_source_hits))
        else:
            print("[論文來源名稱] 無命中")
        for error in paper_errors:
            print(f"[附圖錯誤] {error}")
        print(f"[論文附圖] {result['paper_image_count']} 張")

    if not result["ok"]:
        print("審核失敗")
        return 1

    print("審核通過")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
