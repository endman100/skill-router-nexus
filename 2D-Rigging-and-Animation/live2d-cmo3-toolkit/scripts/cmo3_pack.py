#!/usr/bin/env python3
"""Template-based Live2D CMO3/CAFF entry replacement and repacking.

Use an existing CMO3 as the format template. Replace one or more canonical
entry payloads, rebuild every TOC offset/size, validate the temporary archive,
then atomically rename it to the requested output path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import tempfile
from pathlib import Path

import cmo3_dump
import cmo3_eye_subset as cmo3_codec


PROGRAM_VERSION = "1.0.0"


class PackError(Exception):
    """A replacement or archive cannot be packed safely."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_entry_payload(
    archive: Path,
    entry: cmo3_dump.CaffEntry,
    key8: int,
) -> bytes:
    """Return the canonical payload after CAFF XOR and optional DEFLATE."""

    clear_record = cmo3_codec._clear_entry_bytes(archive, entry, key8)
    if entry.compression_option == 0x10:
        return clear_record
    if entry.compression_option in (0x21, 0x25):
        payload, _ = cmo3_codec._zip_record_payload(clear_record)
        return payload
    raise PackError(
        f"entry {entry.index} {entry.file_path!r} uses unsupported "
        f"compression 0x{entry.compression_option:02X}"
    )


def build_stored_replacement(
    archive: Path,
    entry: cmo3_dump.CaffEntry,
    key8: int,
    payload: bytes,
) -> bytes:
    """Wrap a canonical replacement like its template entry and XOR it."""

    if entry.compression_option == 0x10:
        clear_record = payload
    elif entry.compression_option in (0x21, 0x25):
        original = cmo3_codec._clear_entry_bytes(archive, entry, key8)
        _, metadata = cmo3_codec._zip_record_payload(original)
        clear_record = cmo3_codec._build_zip_record(payload, metadata)
    else:
        raise PackError(
            f"entry {entry.index} {entry.file_path!r} uses unsupported "
            f"compression 0x{entry.compression_option:02X}"
        )
    return cmo3_codec._xor(clear_record, key8) if entry.is_obfuscated else clear_record


def repack_entries(
    template: Path,
    output: Path,
    replacements: dict[str, bytes],
) -> dict:
    """Repack a CMO3 while replacing canonical entry payloads by archive path.

    Args:
        template: Existing CMO3 whose header, metadata, and untouched entries
            are preserved.
        output: New output path. It must not exist.
        replacements: Mapping of exact CAFF file_path to canonical bytes. For
            compressed entries, pass uncompressed bytes such as main.xml.

    Returns:
        A JSON-serializable verification report.

    Raises:
        PackError: If a replacement is ambiguous, unsupported, or validation
            fails.
    """

    template = Path(template).resolve()
    output = Path(output).resolve()
    if not template.is_file():
        raise PackError(f"template is not a file: {template}")
    if output == template:
        raise PackError("refusing to overwrite the template CMO3")
    if output.exists():
        raise PackError(f"output already exists: {output}")

    header, entries, source_size = cmo3_dump.parse_caff(template, 1_000_000)
    if header.preview.file_size:
        raise PackError("archives with embedded CAFF previews are not supported")
    by_path: dict[str, list[cmo3_dump.CaffEntry]] = {}
    for entry in entries:
        by_path.setdefault(entry.file_path, []).append(entry)
    for internal_path in replacements:
        matches = by_path.get(internal_path, [])
        if not matches:
            raise PackError(f"archive path does not exist: {internal_path!r}")
        if len(matches) != 1:
            raise PackError(
                f"archive path is ambiguous ({len(matches)} entries): "
                f"{internal_path!r}"
            )

    key8 = header.obfuscation_key_signed & 0xFF
    stored_replacements: dict[int, bytes] = {}
    for internal_path, payload in replacements.items():
        entry = by_path[internal_path][0]
        stored_replacements[entry.index] = build_stored_replacement(
            template, entry, key8, payload
        )

    payload_sizes = [
        len(stored_replacements.get(entry.index, b""))
        if entry.index in stored_replacements
        else entry.file_size
        for entry in entries
    ]
    toc_lengths = [
        len(
            cmo3_codec._encode_toc_entry(
                entry,
                0,
                payload_sizes[index],
                header.obfuscation_key_signed,
            )
        )
        for index, entry in enumerate(entries)
    ]
    index_end = 0x3A + sum(toc_lengths)
    starts: list[int] = []
    cursor = index_end
    for size in payload_sizes:
        starts.append(cursor)
        cursor += size
    toc = b"".join(
        cmo3_codec._encode_toc_entry(
            entry,
            starts[index],
            payload_sizes[index],
            header.obfuscation_key_signed,
        )
        for index, entry in enumerate(entries)
    )

    with template.open("rb") as source:
        source_prefix = source.read(0x36)
        source.seek(source_size - 2)
        guard = source.read(2)
    if len(source_prefix) != 0x36 or guard != b"bc":
        raise PackError("template CAFF header or guard is malformed")
    encoded_count = struct.pack(
        ">I",
        len(entries) ^ (header.obfuscation_key_signed & 0xFFFF_FFFF),
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as target, template.open("rb") as source:
            temporary_path = Path(target.name)
            target.write(source_prefix)
            target.write(encoded_count)
            target.write(toc)
            for entry in entries:
                replacement = stored_replacements.get(entry.index)
                if replacement is not None:
                    target.write(replacement)
                    continue
                source.seek(entry.start_pos)
                remaining = entry.file_size
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise PackError(f"short payload read for entry {entry.index}")
                    target.write(chunk)
                    remaining -= len(chunk)
            target.write(guard)
            target.flush()
            os.fsync(target.fileno())

        verify_header, verify_entries, verify_size = cmo3_dump.parse_caff(
            temporary_path, 1_000_000
        )
        range_errors, intervals = cmo3_dump.validate_entry_ranges(
            verify_header, verify_entries, verify_size
        )
        gaps, overlaps, covered = cmo3_dump.find_gaps_and_overlaps(
            intervals, verify_size
        )
        if range_errors or gaps or overlaps or covered != verify_size:
            raise PackError("temporary archive failed CAFF range/coverage validation")
        verified_by_path = {entry.file_path: entry for entry in verify_entries}
        for internal_path, expected in replacements.items():
            actual = extract_entry_payload(
                temporary_path,
                verified_by_path[internal_path],
                verify_header.obfuscation_key_signed & 0xFF,
            )
            if actual != expected:
                raise PackError(
                    f"replacement verification mismatch: {internal_path!r}"
                )
        if output.exists():
            raise PackError(f"output appeared while packing: {output}")
        temporary_path.rename(output)
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return {
        "tool": {"name": "cmo3_pack.py", "version": PROGRAM_VERSION},
        "template": str(template),
        "output": str(output),
        "entry_count": len(entries),
        "replacement_count": len(replacements),
        "replacements": [
            {
                "archive_path": internal_path,
                "size": len(payload),
                "sha256": sha256_bytes(payload),
            }
            for internal_path, payload in replacements.items()
        ],
        "output_size": output.stat().st_size,
        "output_sha256": cmo3_dump.sha256_file(output),
        "validation": {
            "range_errors": 0,
            "gaps": 0,
            "overlaps": 0,
            "replacement_byte_matches": len(replacements),
        },
    }


def parse_replacement(specification: str) -> tuple[str, Path]:
    if "=" not in specification:
        raise argparse.ArgumentTypeError(
            "replacement must be ARCHIVE_PATH=LOCAL_FILE"
        )
    internal_path, local_text = specification.split("=", 1)
    if not internal_path or not local_text:
        raise argparse.ArgumentTypeError(
            "replacement must have non-empty archive and local paths"
        )
    return internal_path, Path(local_text)


def write_json_new(path: Path, value: dict) -> None:
    path = path.resolve()
    if path.exists():
        raise PackError(f"report already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replace canonical entries in a template CMO3 and rebuild the "
            "CAFF archive without launching Cubism Editor."
        )
    )
    parser.add_argument("template", type=Path, help="existing template .cmo3")
    parser.add_argument("output", type=Path, help="new output .cmo3")
    parser.add_argument(
        "--replace",
        action="append",
        type=parse_replacement,
        default=[],
        metavar="ARCHIVE_PATH=LOCAL_FILE",
        help="replace an exact CAFF path; repeatable",
    )
    parser.add_argument(
        "--main-xml",
        type=Path,
        help="shorthand for --replace main.xml=LOCAL_FILE",
    )
    parser.add_argument("--report", type=Path, help="write a new JSON report")
    parser.add_argument("--version", action="version", version=f"%(prog)s {PROGRAM_VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output.expanduser().resolve()
    report_path = args.report.expanduser().resolve() if args.report else None
    try:
        if output.exists():
            raise PackError(f"output already exists: {output}")
        if report_path is not None and report_path.exists():
            raise PackError(f"report already exists: {report_path}")
        specifications = list(args.replace)
        if args.main_xml:
            specifications.append(("main.xml", args.main_xml))
        replacements: dict[str, bytes] = {}
        for internal_path, local_path in specifications:
            if internal_path in replacements:
                raise PackError(f"duplicate replacement: {internal_path!r}")
            local_path = local_path.expanduser().resolve()
            if not local_path.is_file():
                raise PackError(f"replacement is not a file: {local_path}")
            replacements[internal_path] = local_path.read_bytes()
        report = repack_entries(args.template, output, replacements)
        if report_path is not None:
            write_json_new(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (PackError, cmo3_dump.CaffError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
