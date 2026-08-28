#!/usr/bin/env python3
"""Losslessly inventory and extract Live2D Cubism CMO3/CAFF archives.

This is a standalone Python 3.10+ command-line program.  It uses only the
standard library and never invokes Cubism Editor or another extractor.

The CAFF layout implemented here was independently checked against public
open-source decoders (not an official Live2D specification), chiefly:
https://github.com/wader/fq/tree/master/format/caff
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import shutil
import struct
import sys
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import BinaryIO, Iterable
from xml.etree import ElementTree


PROGRAM_VERSION = "1.1.0"
CHUNK_SIZE = 1024 * 1024
MAX_STRING_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_ENTRIES = 1_000_000
DEFAULT_MAX_INFLATED_BYTES = 8 * 1024 * 1024 * 1024
DEFAULT_MAX_VALIDATION_BYTES = 64 * 1024 * 1024
AUTO_OUTPUT_LIMIT_MULTIPLIER = 8
AUTO_OUTPUT_LIMIT_MINIMUM = 64 * 1024 * 1024

CAFF_MAGIC = b"CAFF"
GUARD_BYTES = b"bc"
ZIP_LOCAL_MAGIC = b"PK\x03\x04"
ZIP_DESCRIPTOR_MAGIC = b"PK\x07\x08"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

COMPRESSION_NAMES = {
    0x10: "raw",
    0x21: "fast",
    0x25: "small",
}
IMAGE_FORMAT_NAMES = {
    0x00: "unknown",
    0x01: "png",
    0x7F: "no_preview",
}
COLOR_TYPE_NAMES = {
    0x00: "unknown",
    0x01: "argb",
    0x02: "rgb",
    0x7F: "no_preview",
}
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class CaffError(Exception):
    """A malformed or unsupported CAFF archive condition."""


@dataclass
class PreviewInfo:
    image_format: int
    image_format_name: str
    color_type: int
    color_type_name: str
    unused0_hex: str
    width: int
    height: int
    start_pos: int
    file_size: int


@dataclass
class CaffHeader:
    archive_id: str
    archive_version: list[int]
    format_id: str
    format_id_hex: str
    format_version: list[int]
    obfuscation_key_signed: int
    obfuscation_key_hex: str
    unused0_hex: str
    preview: PreviewInfo
    unused1_hex: str
    file_info_count: int
    index_end: int


@dataclass
class CaffEntry:
    index: int
    file_path: str
    file_path_utf8_valid: bool
    file_path_bytes_hex: str
    tag: str
    tag_utf8_valid: bool
    tag_bytes_hex: str
    start_pos: int
    file_size: int
    is_obfuscated_value: int
    is_obfuscated: bool
    compression_option: int
    compression_name: str
    unused0_hex: str
    toc_start: int
    toc_end: int


@dataclass
class OutputComponent:
    source_start: int
    source_end: int
    relative_path: str
    label: str


@dataclass
class EntryResult:
    index: int
    internal_path: str
    tag: str
    source_offset: int
    stored_size: int
    is_obfuscated: bool
    compression_option: int
    compression_name: str
    stored_path: str | None = None
    stored_sha256: str | None = None
    deobfuscated_path: str | None = None
    deobfuscated_sha256: str | None = None
    extracted_path: str | None = None
    extracted_size: int | None = None
    extracted_sha256: str | None = None
    detected_type: str = "unknown"
    zip_record: dict | None = None
    content_validation: dict | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class OutputBudget:
    """Aggregate safety budget for payload-layer files written by the tool."""

    limit: int
    used: int = 0

    @property
    def remaining(self) -> int:
        if self.limit == 0:
            return 0
        return max(0, self.limit - self.used)

    def reserve(self, size: int, label: str) -> None:
        if size < 0:
            raise CaffError(f"{label}: negative output size {size}")
        if self.limit and self.used + size > self.limit:
            raise CaffError(
                f"aggregate payload output would exceed safety limit "
                f"{self.limit:,} bytes while writing {label}; "
                f"already accounted {self.used:,}, requested {size:,}. "
                "Use --max-output-bytes with a larger value, or 0 to disable."
            )
        self.used += size


class BigEndianReader:
    """Strict, bounds-aware reader for CAFF metadata."""

    def __init__(self, stream: BinaryIO, size: int) -> None:
        self.stream = stream
        self.size = size

    @property
    def offset(self) -> int:
        return self.stream.tell()

    def read_exact(self, size: int, label: str) -> bytes:
        if size < 0 or self.offset + size > self.size:
            raise CaffError(
                f"{label}: range 0x{self.offset:X}+0x{size:X} exceeds "
                f"archive size 0x{self.size:X}"
            )
        data = self.stream.read(size)
        if len(data) != size:
            raise CaffError(
                f"{label}: expected {size} bytes at 0x{self.offset - len(data):X}, "
                f"got {len(data)}"
            )
        return data

    def unpack(self, fmt: str, label: str) -> int:
        size = struct.calcsize(fmt)
        return int(struct.unpack(fmt, self.read_exact(size, label))[0])

    def u8(self, label: str) -> int:
        return self.unpack(">B", label)

    def u16(self, label: str) -> int:
        return self.unpack(">H", label)

    def u32(self, label: str) -> int:
        return self.unpack(">I", label)

    def s32(self, label: str) -> int:
        return self.unpack(">i", label)

    def u64(self, label: str) -> int:
        return self.unpack(">Q", label)


def hex_range(start: int, end: int) -> str:
    return f"0x{start:X}-0x{end:X}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_region(stream: BinaryIO, start: int, size: int) -> str:
    digest = hashlib.sha256()
    stream.seek(start)
    remaining = size
    while remaining:
        chunk = stream.read(min(CHUNK_SIZE, remaining))
        if not chunk:
            raise CaffError(f"unexpected EOF while hashing {hex_range(start, start + size)}")
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


def copy_region(stream: BinaryIO, start: int, size: int, output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    stream.seek(start)
    remaining = size
    with output.open("wb") as target:
        while remaining:
            chunk = stream.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                raise CaffError(
                    f"unexpected EOF while copying {hex_range(start, start + size)}"
                )
            target.write(chunk)
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def decode_utf8(raw: bytes) -> tuple[str, bool]:
    try:
        return raw.decode("utf-8"), True
    except UnicodeDecodeError:
        return raw.decode("utf-8", "replace"), False


def xor_u64_mask(key_signed: int) -> int:
    """Match CAFF's signed-key expression `(key << 32) | key` in 64 bits."""

    return ((key_signed << 32) | key_signed) & 0xFFFF_FFFF_FFFF_FFFF


def parse_caff(path: Path, max_entries: int) -> tuple[CaffHeader, list[CaffEntry], int]:
    file_size = path.stat().st_size
    if file_size < 0x3C:
        raise CaffError(f"file is too short for a CAFF archive: {file_size} bytes")

    with path.open("rb") as stream:
        reader = BigEndianReader(stream, file_size)
        magic = reader.read_exact(4, "archive_id")
        if magic != CAFF_MAGIC:
            raise CaffError(
                f"not a Live2D CAFF archive: expected {CAFF_MAGIC!r}, got {magic!r}"
            )

        archive_version = list(reader.read_exact(3, "archive_version"))
        format_id_raw = reader.read_exact(4, "format_id")
        format_id, _ = decode_utf8(format_id_raw)
        format_version = list(reader.read_exact(3, "format_version"))
        key_signed = reader.s32("obfuscation_key")
        key32 = key_signed & 0xFFFF_FFFF
        key8 = key_signed & 0xFF
        key64 = xor_u64_mask(key_signed)
        unused0 = reader.read_exact(8, "unused0")

        image_format = reader.u8("preview.image_format")
        color_type = reader.u8("preview.color_type")
        preview_unused = reader.read_exact(2, "preview.unused0")
        preview_width = reader.u16("preview.width")
        preview_height = reader.u16("preview.height")
        preview_start = reader.u64("preview.start_pos")
        preview_size = reader.u32("preview.file_size")
        unused1 = reader.read_exact(8, "unused1")
        encoded_count = reader.u32("file_info_count")
        count = encoded_count ^ key32

        if count > max_entries:
            raise CaffError(
                f"decoded entry count {count:,} exceeds --max-entries {max_entries:,}"
            )

        def obfuscated_u8(label: str) -> int:
            return reader.u8(label) ^ key8

        def obfuscated_u32(label: str) -> int:
            return reader.u32(label) ^ key32

        def obfuscated_u64(label: str) -> int:
            return reader.u64(label) ^ key64

        def obfuscated_beb128(label: str) -> int:
            value = 0
            for index in range(10):
                byte = obfuscated_u8(f"{label}[{index}]")
                if value > (0xFFFF_FFFF_FFFF_FFFF >> 7):
                    raise CaffError(f"{label}: big-endian base-128 integer overflow")
                value = (value << 7) | (byte & 0x7F)
                if byte & 0x80 == 0:
                    return value
            raise CaffError(f"{label}: unterminated big-endian base-128 integer")

        def obfuscated_string(label: str) -> tuple[str, bool, bytes]:
            length = obfuscated_beb128(f"{label}.length")
            if length > MAX_STRING_BYTES:
                raise CaffError(
                    f"{label}: decoded length {length:,} exceeds safety limit "
                    f"{MAX_STRING_BYTES:,}"
                )
            encoded = reader.read_exact(length, f"{label}.bytes")
            raw = bytes(byte ^ key8 for byte in encoded)
            text, valid = decode_utf8(raw)
            return text, valid, raw

        entries: list[CaffEntry] = []
        for index in range(count):
            toc_start = reader.offset
            file_path, path_valid, path_raw = obfuscated_string(
                f"file_info[{index}].file_path"
            )
            tag, tag_valid, tag_raw = obfuscated_string(f"file_info[{index}].tag")
            start_pos = obfuscated_u64(f"file_info[{index}].start_pos")
            member_size = obfuscated_u32(f"file_info[{index}].file_size")
            is_obfuscated_value = obfuscated_u8(
                f"file_info[{index}].is_obfuscated"
            )
            compression_option = obfuscated_u8(
                f"file_info[{index}].compression_option"
            )
            entry_unused = reader.read_exact(8, f"file_info[{index}].unused0")
            toc_end = reader.offset
            entries.append(
                CaffEntry(
                    index=index,
                    file_path=file_path,
                    file_path_utf8_valid=path_valid,
                    file_path_bytes_hex=path_raw.hex(),
                    tag=tag,
                    tag_utf8_valid=tag_valid,
                    tag_bytes_hex=tag_raw.hex(),
                    start_pos=start_pos,
                    file_size=member_size,
                    is_obfuscated_value=is_obfuscated_value,
                    is_obfuscated=is_obfuscated_value != 0,
                    compression_option=compression_option,
                    compression_name=COMPRESSION_NAMES.get(
                        compression_option, f"unknown_0x{compression_option:02x}"
                    ),
                    unused0_hex=entry_unused.hex(),
                    toc_start=toc_start,
                    toc_end=toc_end,
                )
            )

        header = CaffHeader(
            archive_id="CAFF",
            archive_version=archive_version,
            format_id=format_id,
            format_id_hex=format_id_raw.hex(),
            format_version=format_version,
            obfuscation_key_signed=key_signed,
            obfuscation_key_hex=f"0x{key32:08X}",
            unused0_hex=unused0.hex(),
            preview=PreviewInfo(
                image_format=image_format,
                image_format_name=IMAGE_FORMAT_NAMES.get(
                    image_format, f"unknown_0x{image_format:02x}"
                ),
                color_type=color_type,
                color_type_name=COLOR_TYPE_NAMES.get(
                    color_type, f"unknown_0x{color_type:02x}"
                ),
                unused0_hex=preview_unused.hex(),
                width=preview_width,
                height=preview_height,
                start_pos=preview_start,
                file_size=preview_size,
            ),
            unused1_hex=unused1.hex(),
            file_info_count=count,
            index_end=reader.offset,
        )

    return header, entries, file_size


def validate_entry_ranges(
    header: CaffHeader, entries: list[CaffEntry], file_size: int
) -> tuple[list[str], list[tuple[int, int, str]]]:
    errors: list[str] = []
    intervals: list[tuple[int, int, str]] = [(0, header.index_end, "header_and_index")]

    if header.index_end > file_size:
        errors.append(
            f"header/index ends at 0x{header.index_end:X}, beyond EOF 0x{file_size:X}"
        )

    if header.preview.file_size:
        preview_end = header.preview.start_pos + header.preview.file_size
        if preview_end > file_size:
            errors.append(
                f"preview range {hex_range(header.preview.start_pos, preview_end)} "
                f"exceeds EOF 0x{file_size:X}"
            )
        else:
            intervals.append(
                (header.preview.start_pos, preview_end, "preview_image")
            )

    for entry in entries:
        end = entry.start_pos + entry.file_size
        if end < entry.start_pos or end > file_size:
            errors.append(
                f"entry {entry.index} range {hex_range(entry.start_pos, end)} "
                f"exceeds EOF 0x{file_size:X}"
            )
            continue
        intervals.append((entry.start_pos, end, f"entry_{entry.index:06d}"))

    if file_size >= 2:
        intervals.append((file_size - 2, file_size, "guard_bytes"))
    return errors, intervals


def find_gaps_and_overlaps(
    intervals: Iterable[tuple[int, int, str]], file_size: int
) -> tuple[list[tuple[int, int]], list[dict], int]:
    ordered = sorted(intervals, key=lambda item: (item[0], item[1], item[2]))
    gaps: list[tuple[int, int]] = []
    overlaps: list[dict] = []
    cursor = 0
    owner = "start_of_file"
    for start, end, label in ordered:
        start = max(0, min(start, file_size))
        end = max(start, min(end, file_size))
        if start > cursor:
            gaps.append((cursor, start))
        elif start < cursor and end > start:
            overlaps.append(
                {
                    "range_start": start,
                    "range_end": min(cursor, end),
                    "range_hex": hex_range(start, min(cursor, end)),
                    "previous_owner": owner,
                    "overlapping_owner": label,
                }
            )
        if end > cursor:
            cursor = end
            owner = label
    if cursor < file_size:
        gaps.append((cursor, file_size))
    covered = file_size - sum(end - start for start, end in gaps)
    return gaps, overlaps, covered


def escape_component(component: str) -> str:
    if component in ("", "."):
        return "_empty_"
    if component == "..":
        return "_parent_"

    out: list[str] = []
    for char in component:
        code = ord(char)
        if code < 32 or char in '<>:"/\\|?*' or code == 0x7F:
            out.append(f"_u{code:04X}_")
        else:
            out.append(char)
    safe = "".join(out)
    while safe.endswith((" ", ".")):
        char = safe[-1]
        safe = safe[:-1] + f"_u{ord(char):04X}_"
    if not safe:
        safe = "_empty_"
    if safe.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        safe = "_" + safe
    if len(safe) > 120:
        digest = hashlib.sha256(safe.encode("utf-8", "surrogatepass")).hexdigest()[:12]
        safe = safe[:96] + "_sha256_" + digest
    return safe


def safe_internal_path(internal: str) -> Path:
    normalized = internal.replace("\\", "/")
    components = [escape_component(part) for part in normalized.split("/") if part]
    if not components:
        components = ["_unnamed.bin"]
    if len(components) <= 32:
        candidate = Path(*components)
        if len(candidate.as_posix()) <= 160:
            return candidate

    # Deep or very long archive paths can exceed platform path limits even
    # after each component is escaped.  Preserve the original in manifest.json
    # and map the filesystem name deterministically to a short, unique path.
    digest = hashlib.sha256(
        internal.encode("utf-8", "surrogatepass")
    ).hexdigest()[:20]
    basename = escape_component(components[-1])
    if len(basename) > 72:
        basename = basename[:72]
    return Path("_long_path") / f"{basename}_sha256_{digest}"


def short_entry_label(entry: CaffEntry) -> str:
    basename = entry.file_path.replace("\\", "/").rsplit("/", 1)[-1]
    basename = escape_component(basename or "unnamed")
    if len(basename) > 80:
        basename = basename[:80]
    return f"{entry.index:06d}_{basename}"


def xor_entry_layers(
    source: BinaryIO,
    entry: CaffEntry,
    key8: int,
    stored_path: Path,
    deobfuscated_path: Path,
) -> tuple[str, str]:
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    deobfuscated_path.parent.mkdir(parents=True, exist_ok=True)
    stored_hash = hashlib.sha256()
    decoded_hash = hashlib.sha256()
    translation = bytes(byte ^ key8 for byte in range(256))
    source.seek(entry.start_pos)
    remaining = entry.file_size
    with stored_path.open("wb") as stored, deobfuscated_path.open("wb") as decoded:
        while remaining:
            chunk = source.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                raise CaffError(
                    f"entry {entry.index}: unexpected EOF in "
                    f"{hex_range(entry.start_pos, entry.start_pos + entry.file_size)}"
                )
            stored.write(chunk)
            stored_hash.update(chunk)
            clear = chunk.translate(translation) if entry.is_obfuscated else chunk
            decoded.write(clear)
            decoded_hash.update(clear)
            remaining -= len(chunk)
    return stored_hash.hexdigest(), decoded_hash.hexdigest()


def detect_type(path: Path) -> str:
    with path.open("rb") as stream:
        head = stream.read(64)
    stripped = head.lstrip()
    if head.startswith(PNG_MAGIC):
        return "png"
    if head.startswith(ZIP_LOCAL_MAGIC):
        return "zip_local_record"
    if head.startswith(b"MOC3"):
        return "moc3"
    if head.startswith(b"\xFF\xD8\xFF"):
        return "jpeg"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "gif"
    if stripped.startswith(b"<?xml") or stripped.startswith(b"<"):
        return "xml"
    if stripped.startswith((b"{", b"[")):
        return "json_or_text"
    return "binary"


def parse_zip_descriptor(
    trailing: bytes, zip64: bool
) -> tuple[dict | None, bytes]:
    offset = 0
    has_signature = trailing.startswith(ZIP_DESCRIPTOR_MAGIC)
    if has_signature:
        offset = 4
    size = 20 if zip64 else 12
    if len(trailing) < offset + size:
        return None, trailing
    if zip64:
        crc32, compressed_size, uncompressed_size = struct.unpack_from(
            "<IQQ", trailing, offset
        )
    else:
        crc32, compressed_size, uncompressed_size = struct.unpack_from(
            "<III", trailing, offset
        )
    consumed = offset + size
    return (
        {
            "has_signature": has_signature,
            "crc32_hex": f"0x{crc32:08x}",
            "crc32": crc32,
            "compressed_size": compressed_size,
            "uncompressed_size": uncompressed_size,
            "descriptor_size": consumed,
        },
        trailing[consumed:],
    )


def decompress_zip_local_record(
    source_path: Path,
    output_path: Path,
    max_inflated_bytes: int,
) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_name(output_path.name + ".partial")
    try:
        with source_path.open("rb") as source:
            fixed = source.read(30)
            if len(fixed) != 30:
                raise CaffError("compressed member is shorter than a ZIP local header")
            (
                signature,
                version_needed,
                flags,
                method,
                dos_time,
                dos_date,
                local_crc32,
                local_compressed_size,
                local_uncompressed_size,
                name_length,
                extra_length,
            ) = struct.unpack("<4s5H3I2H", fixed)
            if signature != ZIP_LOCAL_MAGIC:
                raise CaffError(
                    f"compressed member lacks ZIP local magic: got {signature!r}"
                )
            if flags & (0x0001 | 0x0040 | 0x2000):
                raise CaffError("encrypted ZIP local records are not supported")
            if method != 8:
                raise CaffError(
                    f"unsupported ZIP compression method {method}; "
                    "expected raw DEFLATE (8)"
                )
            name_raw = source.read(name_length)
            extra = source.read(extra_length)
            if len(name_raw) != name_length or len(extra) != extra_length:
                raise CaffError("truncated ZIP local filename or extra field")
            name_encoding = "utf-8" if flags & 0x0800 else "cp437"
            try:
                zip_name = name_raw.decode(name_encoding)
                zip_name_valid = True
            except UnicodeDecodeError:
                zip_name = name_raw.decode(name_encoding, "replace")
                zip_name_valid = False
            data_start = source.tell()

            inflater = zlib.decompressobj(-zlib.MAX_WBITS)
            crc32 = 0
            uncompressed_size = 0
            bytes_fed = 0
            trailing_prefix = b""
            with partial_path.open("xb") as output:
                while not inflater.eof:
                    chunk = source.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    bytes_fed += len(chunk)
                    pending = chunk
                    while pending and not inflater.eof:
                        before = len(pending)
                        if max_inflated_bytes:
                            room = max_inflated_bytes - uncompressed_size
                            max_output = min(CHUNK_SIZE, max(1, room + 1))
                        else:
                            max_output = CHUNK_SIZE
                        try:
                            clear = inflater.decompress(pending, max_output)
                        except zlib.error as exc:
                            raise CaffError(
                                f"raw DEFLATE stream failed: {exc}"
                            ) from exc
                        pending = inflater.unconsumed_tail
                        if clear:
                            uncompressed_size += len(clear)
                            if (
                                max_inflated_bytes
                                and uncompressed_size > max_inflated_bytes
                            ):
                                raise CaffError(
                                    f"inflated member exceeds safety limit "
                                    f"{max_inflated_bytes:,} bytes; use "
                                    "--max-inflated-bytes/--max-output-bytes to "
                                    "raise it, or 0 to disable"
                                )
                            output.write(clear)
                            crc32 = zlib.crc32(clear, crc32)
                        if (
                            not inflater.eof
                            and pending
                            and len(pending) == before
                            and not clear
                        ):
                            raise CaffError("raw DEFLATE decoder made no progress")
                if not inflater.eof:
                    raise CaffError("raw DEFLATE stream did not reach an end marker")
                trailing_prefix = inflater.unused_data

            compressed_stream_size = bytes_fed - len(inflater.unused_data)
            zip64 = (
                local_compressed_size == 0xFFFF_FFFF
                or local_uncompressed_size == 0xFFFF_FFFF
            )

            def fill_trailing_prefix(required: int) -> None:
                nonlocal trailing_prefix
                while len(trailing_prefix) < required:
                    part = source.read(required - len(trailing_prefix))
                    if not part:
                        break
                    trailing_prefix += part

            descriptor = None
            descriptor_remainder = trailing_prefix
            if flags & 0x0008:
                fill_trailing_prefix(4)
                signature_size = 4 if trailing_prefix.startswith(ZIP_DESCRIPTOR_MAGIC) else 0
                descriptor_size = signature_size + (20 if zip64 else 12)
                fill_trailing_prefix(descriptor_size)
                descriptor, descriptor_remainder = parse_zip_descriptor(
                    trailing_prefix, zip64
                )
                if descriptor is None:
                    raise CaffError(
                        "ZIP data-descriptor flag is set but the required "
                        "descriptor is missing or truncated"
                    )

            trailing_hash = hashlib.sha256()
            trailing_size = 0
            trailing_sample = bytearray()

            def account_trailing(chunk: bytes) -> None:
                nonlocal trailing_size
                if not chunk:
                    return
                trailing_hash.update(chunk)
                trailing_size += len(chunk)
                if len(trailing_sample) <= 256:
                    take = min(257 - len(trailing_sample), len(chunk))
                    trailing_sample.extend(chunk[:take])

            account_trailing(descriptor_remainder)
            while trailing_chunk := source.read(CHUNK_SIZE):
                account_trailing(trailing_chunk)

            computed_crc32 = crc32 & 0xFFFF_FFFF
            checks: dict[str, bool | None] = {
                "deflate_eof": inflater.eof,
                "local_crc32_matches": None,
                "local_compressed_size_matches": None,
                "local_uncompressed_size_matches": None,
                "descriptor_crc32_matches": None,
                "descriptor_compressed_size_matches": None,
                "descriptor_uncompressed_size_matches": None,
                "no_unparsed_trailing_bytes": trailing_size == 0,
            }
            if flags & 0x0008:
                # With bit 3 set, the descriptor is authoritative.  Non-zero
                # local fields are still checked for contradictions.
                if local_crc32:
                    checks["local_crc32_matches"] = local_crc32 == computed_crc32
                if local_compressed_size not in (0, 0xFFFF_FFFF):
                    checks["local_compressed_size_matches"] = (
                        local_compressed_size == compressed_stream_size
                    )
                if local_uncompressed_size not in (0, 0xFFFF_FFFF):
                    checks["local_uncompressed_size_matches"] = (
                        local_uncompressed_size == uncompressed_size
                    )
                checks["descriptor_crc32_matches"] = (
                    descriptor["crc32"] == computed_crc32
                )
                checks["descriptor_compressed_size_matches"] = (
                    descriptor["compressed_size"] == compressed_stream_size
                )
                checks["descriptor_uncompressed_size_matches"] = (
                    descriptor["uncompressed_size"] == uncompressed_size
                )
            else:
                # Without bit 3, all three local fields are authoritative,
                # including legitimate zero values.
                checks["local_crc32_matches"] = local_crc32 == computed_crc32
                checks["local_compressed_size_matches"] = (
                    local_compressed_size == compressed_stream_size
                )
                checks["local_uncompressed_size_matches"] = (
                    local_uncompressed_size == uncompressed_size
                )

            integrity_names = [
                name
                for name in checks
                if name != "no_unparsed_trailing_bytes"
            ]
            failed_integrity = [
                name for name in integrity_names if checks[name] is False
            ]
            if failed_integrity:
                raise CaffError(
                    "failed ZIP integrity checks: " + ", ".join(failed_integrity)
                )
            if trailing_size:
                warnings.append(
                    f"ZIP record has {trailing_size} unparsed trailing bytes"
                )

            metadata = {
                "version_needed": version_needed,
                "flags_hex": f"0x{flags:04x}",
                "flags": flags,
                "uses_data_descriptor": bool(flags & 0x0008),
                "utf8_filename": bool(flags & 0x0800),
                "compression_method": method,
                "dos_time_hex": f"0x{dos_time:04x}",
                "dos_date_hex": f"0x{dos_date:04x}",
                "local_crc32_hex": f"0x{local_crc32:08x}",
                "local_compressed_size": local_compressed_size,
                "local_uncompressed_size": local_uncompressed_size,
                "filename": zip_name,
                "filename_utf8_or_cp437_valid": zip_name_valid,
                "filename_bytes_hex": name_raw.hex(),
                "extra_field_hex": extra.hex(),
                "header_size": data_start,
                "compressed_stream_size": compressed_stream_size,
                "computed_uncompressed_size": uncompressed_size,
                "computed_crc32_hex": f"0x{computed_crc32:08x}",
                "data_descriptor": descriptor,
                "unparsed_trailing_size": trailing_size,
                "unparsed_trailing_hex": (
                    bytes(trailing_sample).hex() if trailing_size <= 256 else None
                ),
                "unparsed_trailing_sha256": trailing_hash.hexdigest(),
                "checks": checks,
                "all_applicable_checks_pass": not any(
                    value is False for value in checks.values()
                ),
            }

        if output_path.exists():
            raise CaffError(f"refusing to replace existing extracted file: {output_path}")
        partial_path.rename(output_path)
        return metadata, warnings
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise


def validate_png(path: Path, max_validation_bytes: int) -> dict:
    result: dict = {
        "valid_signature": False,
        "chunk_count": 0,
        "chunk_type_counts": {},
        "chunk_crc_failures": [],
        "idat_zlib_eof": None,
        "idat_chunk_count": 0,
        "idat_inflated_bytes": 0,
        "idat_extra_compressed_bytes": False,
        "validation_limit_exceeded": False,
        "has_ihdr": False,
        "ihdr_valid": False,
        "has_iend": False,
        "iend_valid": False,
        "first_chunk_is_ihdr": False,
        "idat_chunks_consecutive": True,
        "trailing_bytes": 0,
        "valid": False,
    }
    counts: collections.Counter[str] = collections.Counter()
    inflater: zlib.Decompress | None = None
    saw_non_idat_after_idat = False
    file_size = path.stat().st_size

    def feed_idat(data: bytes) -> None:
        nonlocal inflater
        if inflater is None or result.get("idat_zlib_error"):
            return
        if inflater.eof:
            if data:
                result["idat_extra_compressed_bytes"] = True
            return
        pending = data
        while pending and not inflater.eof:
            before = len(pending)
            if max_validation_bytes:
                room = max_validation_bytes - result["idat_inflated_bytes"]
                max_output = min(CHUNK_SIZE, max(1, room + 1))
            else:
                max_output = CHUNK_SIZE
            try:
                clear = inflater.decompress(pending, max_output)
            except zlib.error as exc:
                result["idat_zlib_error"] = str(exc)
                return
            pending = inflater.unconsumed_tail
            result["idat_inflated_bytes"] += len(clear)
            if (
                max_validation_bytes
                and result["idat_inflated_bytes"] > max_validation_bytes
            ):
                result["validation_limit_exceeded"] = True
                result["idat_zlib_error"] = (
                    "inflated IDAT data exceeds content-validation limit "
                    f"{max_validation_bytes:,} bytes"
                )
                return
            if inflater.eof and inflater.unused_data:
                result["idat_extra_compressed_bytes"] = True
            if (
                not inflater.eof
                and pending
                and len(pending) == before
                and not clear
            ):
                result["idat_zlib_error"] = "zlib decoder made no progress"
                return

    with path.open("rb") as stream:
        if stream.read(8) != PNG_MAGIC:
            return result
        result["valid_signature"] = True
        while True:
            header = stream.read(8)
            if not header:
                break
            if len(header) != 8:
                result["trailing_bytes"] = file_size - (stream.tell() - len(header))
                break
            length, chunk_type = struct.unpack(">I4s", header)
            if length > file_size - stream.tell() - 4:
                result["chunk_crc_failures"].append("impossible_chunk_length")
                break
            type_text = chunk_type.decode("ascii", "replace")
            counts[type_text] += 1
            chunk_index = result["chunk_count"]
            result["chunk_count"] += 1
            if chunk_index == 0:
                result["first_chunk_is_ihdr"] = chunk_type == b"IHDR"
            if chunk_type == b"IDAT":
                if inflater is None:
                    inflater = zlib.decompressobj()
                result["idat_chunk_count"] += 1
                if saw_non_idat_after_idat:
                    result["idat_chunks_consecutive"] = False
            elif result["idat_chunk_count"]:
                saw_non_idat_after_idat = True

            computed_crc = zlib.crc32(chunk_type)
            ihdr_data = bytearray()
            remaining = length
            truncated = False
            while remaining:
                data = stream.read(min(CHUNK_SIZE, remaining))
                if not data:
                    truncated = True
                    break
                remaining -= len(data)
                computed_crc = zlib.crc32(data, computed_crc)
                if chunk_type == b"IHDR" and len(ihdr_data) < 13:
                    ihdr_data.extend(data[: 13 - len(ihdr_data)])
                if chunk_type == b"IDAT":
                    feed_idat(data)
            if truncated:
                result["chunk_crc_failures"].append("truncated_chunk")
                break
            crc_raw = stream.read(4)
            if len(crc_raw) != 4:
                result["chunk_crc_failures"].append("truncated_chunk")
                break
            expected_crc = struct.unpack(">I", crc_raw)[0]
            computed_crc &= 0xFFFF_FFFF
            if expected_crc != computed_crc:
                result["chunk_crc_failures"].append(
                    {
                        "chunk_index": chunk_index,
                        "type": type_text,
                        "expected": f"0x{expected_crc:08x}",
                        "computed": f"0x{computed_crc:08x}",
                    }
                )
            if chunk_type == b"IHDR":
                result["has_ihdr"] = True
                if length == 13 and counts[type_text] == 1:
                    width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                        ">IIBBBBB", ihdr_data
                    )
                    result["ihdr"] = {
                        "width": width,
                        "height": height,
                        "bit_depth": bit_depth,
                        "color_type": color_type,
                        "compression_method": compression,
                        "filter_method": filtering,
                        "interlace_method": interlace,
                    }
                    allowed_depths = {
                        0: {1, 2, 4, 8, 16},
                        2: {8, 16},
                        3: {1, 2, 4, 8},
                        4: {8, 16},
                        6: {8, 16},
                    }
                    result["ihdr_valid"] = bool(
                        0 < width <= 0x7FFF_FFFF
                        and 0 < height <= 0x7FFF_FFFF
                        and bit_depth in allowed_depths.get(color_type, set())
                        and compression == 0
                        and filtering == 0
                        and interlace in (0, 1)
                    )
            elif chunk_type == b"IEND":
                result["has_iend"] = True
                result["iend_valid"] = length == 0 and counts[type_text] == 1
                result["trailing_bytes"] = file_size - stream.tell()
                break
    if inflater is not None:
        result["idat_zlib_eof"] = inflater.eof
    result["chunk_type_counts"] = dict(sorted(counts.items()))
    result["valid"] = bool(
        result["valid_signature"]
        and result["has_ihdr"]
        and result["ihdr_valid"]
        and result["has_iend"]
        and result["iend_valid"]
        and result["first_chunk_is_ihdr"]
        and result["idat_chunk_count"] > 0
        and result["idat_chunks_consecutive"]
        and not result["chunk_crc_failures"]
        and result["trailing_bytes"] == 0
        and result["idat_zlib_eof"] is True
        and not result.get("idat_zlib_error")
        and not result["idat_extra_compressed_bytes"]
        and not result["validation_limit_exceeded"]
    )
    return result


def inspect_xml(path: Path, max_validation_bytes: int) -> dict:
    file_size = path.stat().st_size
    if max_validation_bytes and file_size > max_validation_bytes:
        return {
            "parsed": None,
            "skipped": True,
            "reason": (
                f"file size {file_size:,} exceeds content-validation limit "
                f"{max_validation_bytes:,} bytes"
            ),
        }
    tags: collections.Counter[str] = collections.Counter()
    attributes: collections.Counter[str] = collections.Counter()
    root_tag: str | None = None
    root_attributes: dict[str, str] = {}
    element_count = 0
    parse_error: str | None = None
    try:
        for event, element in ElementTree.iterparse(path, events=("start", "end")):
            if event == "start":
                element_count += 1
                tag = str(element.tag)
                tags[tag] += 1
                attributes.update(str(name) for name in element.attrib)
                if root_tag is None:
                    root_tag = tag
                    root_attributes = dict(element.attrib)
            else:
                element.clear()
    except ElementTree.ParseError as exc:
        parse_error = str(exc)

    pi_targets: collections.Counter[str] = collections.Counter()
    absolute_path_matches = 0
    pi_pattern = re.compile(rb"<\?([A-Za-z_][A-Za-z0-9_.:-]*)\b")
    windows_path_pattern = re.compile(rb"[A-Za-z]:[\\/][^\x00\r\n<>\"]+")
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            for match in pi_pattern.finditer(chunk):
                pi_targets[match.group(1).decode("ascii", "replace")] += 1
            absolute_path_matches += len(windows_path_pattern.findall(chunk))

    return {
        "parsed": parse_error is None,
        "skipped": False,
        "parse_error": parse_error,
        "root_tag": root_tag,
        "root_attributes": root_attributes,
        "element_count": element_count,
        "unique_element_tags": len(tags),
        "element_tag_counts": dict(tags.most_common()),
        "attribute_count": sum(attributes.values()),
        "unique_attribute_names": len(attributes),
        "attribute_name_counts": dict(attributes.most_common()),
        "processing_instruction_target_counts": dict(pi_targets.most_common()),
        "possible_windows_absolute_path_occurrences": absolute_path_matches,
        "privacy_warning": (
            "XML may contain original local filesystem paths and project metadata"
            if absolute_path_matches
            else None
        ),
    }


def validate_json(path: Path, max_validation_bytes: int) -> dict:
    file_size = path.stat().st_size
    if max_validation_bytes and file_size > max_validation_bytes:
        return {
            "valid": None,
            "skipped": True,
            "reason": (
                f"file size {file_size:,} exceeds content-validation limit "
                f"{max_validation_bytes:,} bytes"
            ),
        }
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
        return {
            "valid": True,
            "skipped": False,
            "root_type": type(value).__name__,
        }
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"valid": False, "skipped": False, "error": str(exc)}


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=False)
        stream.write("\n")


def write_inventory_csv(
    path: Path, entries: list[CaffEntry], results: list[EntryResult]
) -> None:
    by_index = {result.index: result for result in results}
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "index",
                "internal_path",
                "tag",
                "start_pos",
                "start_pos_hex",
                "stored_size",
                "obfuscated",
                "compression_option",
                "compression_name",
                "detected_type",
                "extracted_size",
                "stored_sha256",
                "deobfuscated_sha256",
                "extracted_sha256",
                "extracted_path",
                "warnings",
                "errors",
            ]
        )
        for entry in entries:
            result = by_index.get(entry.index)
            writer.writerow(
                [
                    entry.index,
                    entry.file_path,
                    entry.tag,
                    entry.start_pos,
                    f"0x{entry.start_pos:X}",
                    entry.file_size,
                    entry.is_obfuscated,
                    f"0x{entry.compression_option:02X}",
                    entry.compression_name,
                    result.detected_type if result else "",
                    result.extracted_size if result else "",
                    result.stored_sha256 if result else "",
                    result.deobfuscated_sha256 if result else "",
                    result.extracted_sha256 if result else "",
                    result.extracted_path if result else "",
                    " | ".join(result.warnings) if result else "",
                    " | ".join(result.errors) if result else "",
                ]
            )


def build_reconstruction_fragments(
    components: Iterable[OutputComponent], file_size: int
) -> list[dict]:
    ordered = sorted(
        components,
        key=lambda item: (item.source_start, item.source_end, item.label),
    )
    fragments: list[dict] = []
    cursor = 0
    for component in ordered:
        if component.source_end <= cursor:
            continue
        use_start = max(cursor, component.source_start)
        if use_start > cursor:
            raise CaffError(
                f"reconstruction map has a hole {hex_range(cursor, use_start)}"
            )
        length = component.source_end - use_start
        if length <= 0:
            continue
        fragments.append(
            {
                "source_start": use_start,
                "source_end": component.source_end,
                "length": length,
                "fragment_path": component.relative_path,
                "fragment_offset": use_start - component.source_start,
                "label": component.label,
            }
        )
        cursor = component.source_end
    if cursor != file_size:
        raise CaffError(
            f"reconstruction map covers 0x{cursor:X} bytes, expected 0x{file_size:X}"
        )
    return fragments


def hash_reconstruction(root: Path, fragments: list[dict]) -> str:
    digest = hashlib.sha256()
    for fragment in fragments:
        path = root / fragment["fragment_path"]
        with path.open("rb") as stream:
            stream.seek(fragment["fragment_offset"])
            remaining = fragment["length"]
            while remaining:
                chunk = stream.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise CaffError(
                        f"reconstruction fragment {path} ended {remaining} bytes early"
                    )
                digest.update(chunk)
                remaining -= len(chunk)
    return digest.hexdigest()


def copy_deobfuscated_to_extracted(decoded: Path, extracted: Path) -> None:
    extracted.parent.mkdir(parents=True, exist_ok=True)
    partial = extracted.with_name(extracted.name + ".partial")
    try:
        with decoded.open("rb") as source, partial.open("xb") as target:
            shutil.copyfileobj(source, target, CHUNK_SIZE)
        if extracted.exists():
            raise CaffError(f"refusing to replace existing extracted file: {extracted}")
        partial.rename(extracted)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def copy_or_xor_file(source: Path, target: Path, xor_key: int | None = None) -> None:
    """Copy a file atomically, optionally XOR-translating every byte."""

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    translation = (
        bytes(byte ^ xor_key for byte in range(256))
        if xor_key is not None
        else None
    )
    try:
        with source.open("rb") as input_stream, partial.open("xb") as output_stream:
            while chunk := input_stream.read(CHUNK_SIZE):
                output_stream.write(
                    chunk.translate(translation) if translation is not None else chunk
                )
        if target.exists():
            raise CaffError(f"refusing to replace existing file: {target}")
        partial.rename(target)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def dump_archive(
    input_path: Path,
    output_root: Path,
    max_entries: int,
    max_inflated_bytes: int,
    validate_content: bool,
    max_output_bytes: int | None = None,
    max_validation_bytes: int = DEFAULT_MAX_VALIDATION_BYTES,
) -> tuple[dict, int]:
    header, entries, file_size = parse_caff(input_path, max_entries)
    range_errors, intervals = validate_entry_ranges(header, entries, file_size)
    if range_errors:
        raise CaffError("invalid archive ranges:\n- " + "\n- ".join(range_errors))

    gaps, overlaps, covered_bytes = find_gaps_and_overlaps(intervals, file_size)
    effective_output_limit = (
        max(AUTO_OUTPUT_LIMIT_MINIMUM, file_size * AUTO_OUTPUT_LIMIT_MULTIPLIER)
        if max_output_bytes is None
        else max_output_bytes
    )
    budget = OutputBudget(effective_output_limit)

    # Fail before creating the output directory when the size of all known
    # layers already exceeds the budget. Compressed final sizes are bounded
    # incrementally below because they are not known until DEFLATE finishes.
    entry_bytes = sum(entry.file_size for entry in entries)
    gap_bytes = sum(end - start for start, end in gaps)
    known_extracted_bytes = sum(
        entry.file_size
        for entry in entries
        if entry.compression_option not in (0x21, 0x25)
    )
    known_mandatory_output = (
        header.index_end
        + header.preview.file_size
        + 2
        + entry_bytes * 2
        + gap_bytes
        + known_extracted_bytes
    )
    known_payload_output = (
        known_mandatory_output
        + header.preview.file_size  # worst case: a decoded preview copy
    )
    if effective_output_limit and known_payload_output > effective_output_limit:
        raise CaffError(
            f"known payload layers require at least {known_payload_output:,} bytes, "
            f"exceeding aggregate output safety limit {effective_output_limit:,}. "
            "Use --max-output-bytes with a larger value, or 0 to disable."
        )
    budget.reserve(known_mandatory_output, "known mandatory payload layers")

    output_root.mkdir(parents=False, exist_ok=False)
    incomplete_marker = output_root / "INCOMPLETE.txt"
    incomplete_marker.write_text(
        "Extraction is still running or stopped with errors. See manifest.json.\n",
        encoding="utf-8",
    )

    archive_dir = output_root / "archive"
    stored_dir = output_root / "stored_entries"
    decoded_dir = output_root / "deobfuscated_entries"
    files_dir = output_root / "files"
    analysis_dir = output_root / "analysis"
    for directory in (archive_dir, stored_dir, decoded_dir, files_dir, analysis_dir):
        directory.mkdir(parents=True, exist_ok=True)

    source_sha256 = sha256_file(input_path)
    global_warnings: list[str] = []
    global_errors: list[str] = []
    components: list[OutputComponent] = []
    if overlaps:
        global_warnings.append(
            f"declared archive ranges contain {len(overlaps)} overlap(s); "
            "all source bytes are preserved, but the member map is ambiguous"
        )

    header_path = archive_dir / "header_and_index.bin"
    with input_path.open("rb") as source:
        header_hash = copy_region(source, 0, header.index_end, header_path)
    components.append(
        OutputComponent(
            0,
            header.index_end,
            relative_posix(header_path, output_root),
            "header_and_index",
        )
    )

    preview_manifest: dict | None = None
    if header.preview.file_size:
        preview_path = archive_dir / "preview_image.stored.bin"
        with input_path.open("rb") as source:
            preview_hash = copy_region(
                source,
                header.preview.start_pos,
                header.preview.file_size,
                preview_path,
            )
        components.append(
            OutputComponent(
                header.preview.start_pos,
                header.preview.start_pos + header.preview.file_size,
                relative_posix(preview_path, output_root),
                "preview_image",
            )
        )
        preview_manifest = {
            "stored_path": relative_posix(preview_path, output_root),
            "stored_sha256": preview_hash,
            "decoded_path": None,
            "decode_method": "preserved_exactly; preview obfuscation is undocumented",
        }
        with preview_path.open("rb") as preview_stream:
            stored_preview_head = preview_stream.read(len(PNG_MAGIC))
        if stored_preview_head.startswith(PNG_MAGIC):
            decoded_preview = archive_dir / "preview_image.png"
            budget.reserve(header.preview.file_size, "decoded preview")
            copy_or_xor_file(preview_path, decoded_preview)
            preview_manifest["decoded_path"] = relative_posix(
                decoded_preview, output_root
            )
            preview_manifest["decode_method"] = "stored bytes already form PNG"
        else:
            key8 = header.obfuscation_key_signed & 0xFF
            candidate_head = bytes(byte ^ key8 for byte in stored_preview_head)
            if candidate_head.startswith(PNG_MAGIC):
                decoded_preview = archive_dir / "preview_image.xor.png"
                budget.reserve(header.preview.file_size, "XOR-decoded preview")
                copy_or_xor_file(preview_path, decoded_preview, key8)
                preview_manifest["decoded_path"] = relative_posix(
                    decoded_preview, output_root
                )
                preview_manifest["decode_method"] = "XOR with CAFF key low byte"

    guard_path = archive_dir / "guard_bytes.bin"
    with input_path.open("rb") as source:
        guard_hash = copy_region(source, file_size - 2, 2, guard_path)
    guard_value = guard_path.read_bytes()
    components.append(
        OutputComponent(
            file_size - 2,
            file_size,
            relative_posix(guard_path, output_root),
            "guard_bytes",
        )
    )
    guard_valid = guard_value == GUARD_BYTES
    if not guard_valid:
        global_warnings.append(
            f"final guard bytes are {guard_value.hex()}, expected {GUARD_BYTES.hex()}"
        )

    key8 = header.obfuscation_key_signed & 0xFF
    results: list[EntryResult] = []
    with input_path.open("rb") as source:
        for entry in entries:
            result = EntryResult(
                index=entry.index,
                internal_path=entry.file_path,
                tag=entry.tag,
                source_offset=entry.start_pos,
                stored_size=entry.file_size,
                is_obfuscated=entry.is_obfuscated,
                compression_option=entry.compression_option,
                compression_name=entry.compression_name,
            )
            results.append(result)
            label = short_entry_label(entry)
            stored_path = stored_dir / f"{label}.stored.bin"
            decoded_path = decoded_dir / f"{label}.decoded.bin"
            result.stored_path = relative_posix(stored_path, output_root)
            result.deobfuscated_path = relative_posix(decoded_path, output_root)
            try:
                stored_hash, decoded_hash = xor_entry_layers(
                    source,
                    entry,
                    key8,
                    stored_path,
                    decoded_path,
                )
                result.stored_sha256 = stored_hash
                result.deobfuscated_sha256 = decoded_hash
                components.append(
                    OutputComponent(
                        entry.start_pos,
                        entry.start_pos + entry.file_size,
                        relative_posix(stored_path, output_root),
                        f"entry_{entry.index:06d}",
                    )
                )

                entry_root = files_dir / f"{entry.index:06d}"
                extracted_path = entry_root / safe_internal_path(entry.file_path)
                if entry.compression_option == 0x10:
                    copy_deobfuscated_to_extracted(decoded_path, extracted_path)
                elif entry.compression_option in (0x21, 0x25):
                    member_limits = [
                        limit
                        for limit in (max_inflated_bytes, budget.remaining)
                        if limit
                    ]
                    if budget.limit and budget.remaining == 0:
                        raise CaffError(
                            "aggregate payload output safety limit has no space "
                            f"remaining for compressed entry {entry.index}"
                        )
                    effective_member_limit = min(member_limits) if member_limits else 0
                    zip_metadata, zip_warnings = decompress_zip_local_record(
                        decoded_path,
                        extracted_path,
                        effective_member_limit,
                    )
                    result.zip_record = zip_metadata
                    result.warnings.extend(zip_warnings)
                    budget.reserve(
                        extracted_path.stat().st_size,
                        f"inflated entry {entry.index}",
                    )
                else:
                    result.warnings.append(
                        f"unknown compression option 0x{entry.compression_option:02X}; "
                        "the deobfuscated record is preserved but not decompressed"
                    )
                    fallback = extracted_path.with_name(extracted_path.name + ".unparsed")
                    copy_deobfuscated_to_extracted(decoded_path, fallback)
                    extracted_path = fallback

                result.extracted_path = relative_posix(extracted_path, output_root)
                result.extracted_size = extracted_path.stat().st_size
                result.extracted_sha256 = sha256_file(extracted_path)
                result.detected_type = detect_type(extracted_path)
                if validate_content:
                    if result.detected_type == "png":
                        result.content_validation = validate_png(
                            extracted_path, max_validation_bytes
                        )
                        if not result.content_validation.get("valid"):
                            result.warnings.append("PNG structural validation failed")
                    elif result.detected_type == "xml":
                        result.content_validation = inspect_xml(
                            extracted_path, max_validation_bytes
                        )
                        if result.content_validation.get("skipped"):
                            result.warnings.append(
                                "XML validation skipped: "
                                + str(result.content_validation.get("reason"))
                            )
                        elif not result.content_validation.get("parsed"):
                            result.warnings.append("XML parsing failed")
                        xml_inventory_path = (
                            analysis_dir / "xml" / f"{entry.index:06d}.json"
                        )
                        write_json(xml_inventory_path, result.content_validation)
                    elif result.detected_type == "json_or_text":
                        result.content_validation = validate_json(
                            extracted_path, max_validation_bytes
                        )
                        if result.content_validation.get("skipped"):
                            result.warnings.append(
                                "JSON validation skipped: "
                                + str(result.content_validation.get("reason"))
                            )
                        elif not result.content_validation.get("valid"):
                            result.warnings.append("JSON parsing failed")
            except (CaffError, OSError, ValueError) as exc:
                result.errors.append(str(exc))
                global_errors.append(f"entry {entry.index}: {exc}")

    gap_dir = archive_dir / "unclaimed_ranges"
    gap_records: list[dict] = []
    if gaps:
        gap_dir.mkdir(parents=True, exist_ok=True)
    with input_path.open("rb") as source:
        for index, (start, end) in enumerate(gaps):
            gap_path = gap_dir / f"{index:04d}_0x{start:X}-0x{end:X}.bin"
            gap_hash = copy_region(source, start, end - start, gap_path)
            gap_records.append(
                {
                    "start": start,
                    "end": end,
                    "length": end - start,
                    "range_hex": hex_range(start, end),
                    "path": relative_posix(gap_path, output_root),
                    "sha256": gap_hash,
                }
            )
            components.append(
                OutputComponent(
                    start,
                    end,
                    relative_posix(gap_path, output_root),
                    f"unclaimed_gap_{index:04d}",
                )
            )

    fragments = build_reconstruction_fragments(components, file_size)
    reconstructed_sha256 = hash_reconstruction(output_root, fragments)
    reconstruction_matches = reconstructed_sha256 == source_sha256
    if not reconstruction_matches:
        global_errors.append(
            "reconstruction fragment hash does not match the input SHA-256"
        )

    compression_counts = collections.Counter(
        entry.compression_name for entry in entries
    )
    detected_counts = collections.Counter(result.detected_type for result in results)
    extracted_total = sum(result.extracted_size or 0 for result in results)
    stored_total = sum(entry.file_size for entry in entries)

    def validation_failed(result: EntryResult) -> bool:
        validation = result.content_validation
        if not validation or validation.get("skipped"):
            return False
        return bool(
            validation.get("valid") is False
            or validation.get("parsed") is False
        )

    content_validation_failures = sum(
        validation_failed(result) for result in results
    )
    content_validation_skips = sum(
        bool(result.content_validation and result.content_validation.get("skipped"))
        for result in results
    )
    entry_error_count = sum(bool(result.errors) for result in results)
    entry_warning_count = sum(bool(result.warnings) for result in results)
    if global_errors:
        status = "complete_with_errors"
    elif global_warnings or entry_warning_count:
        status = "complete_with_warnings"
    else:
        status = "complete"

    manifest = {
        "tool": {
            "name": "cmo3_dump.py",
            "version": PROGRAM_VERSION,
            "python": sys.version.split()[0],
            "standard_library_only": True,
            "limits": {
                "max_entries": max_entries,
                "max_inflated_bytes_per_entry": max_inflated_bytes,
                "max_content_validation_bytes": max_validation_bytes,
                "max_payload_output_bytes": effective_output_limit,
                "max_payload_output_mode": (
                    "automatic_8x_input_minimum_64MiB"
                    if max_output_bytes is None
                    else ("disabled" if max_output_bytes == 0 else "explicit")
                ),
                "payload_output_bytes_accounted": budget.used,
                "note": (
                    "The aggregate budget covers binary payload layers; "
                    "JSON/CSV/text metadata adds a comparatively small amount."
                ),
            },
        },
        "source": {
            "path": str(input_path.resolve()),
            "file_name": input_path.name,
            "size": file_size,
            "size_hex": f"0x{file_size:X}",
            "sha256": source_sha256,
        },
        "header": asdict(header),
        "header_and_index": {
            "path": relative_posix(header_path, output_root),
            "size": header.index_end,
            "sha256": header_hash,
        },
        "preview_output": preview_manifest,
        "guard": {
            "path": relative_posix(guard_path, output_root),
            "value_hex": guard_value.hex(),
            "expected_hex": GUARD_BYTES.hex(),
            "valid": guard_valid,
            "sha256": guard_hash,
        },
        "entries": [
            {
                "toc": asdict(entry),
                "output": asdict(result),
            }
            for entry, result in zip(entries, results)
        ],
        "coverage": {
            "archive_size": file_size,
            "covered_bytes_by_declared_intervals": covered_bytes,
            "coverage_percent": round(covered_bytes / file_size * 100, 9),
            "gaps": gap_records,
            "overlaps": overlaps,
            "all_bytes_preserved_in_fragments": reconstruction_matches,
        },
        "reconstruction": {
            "method": (
                "Concatenate each fragment_path slice in listed order. Read "
                "length bytes starting at fragment_offset."
            ),
            "fragments": fragments,
            "computed_sha256": reconstructed_sha256,
            "matches_source_sha256": reconstruction_matches,
        },
        "summary": {
            "entry_count": len(entries),
            "obfuscated_entry_count": sum(entry.is_obfuscated for entry in entries),
            "compression_counts": dict(sorted(compression_counts.items())),
            "detected_type_counts": dict(sorted(detected_counts.items())),
            "stored_payload_bytes": stored_total,
            "extracted_payload_bytes": extracted_total,
            "entry_error_count": entry_error_count,
            "entry_warning_count": entry_warning_count,
            "global_warning_count": len(global_warnings),
            "content_validation_failure_count": content_validation_failures,
            "content_validation_skip_count": content_validation_skips,
        },
        "warnings": global_warnings,
        "errors": global_errors,
        "status": status,
        "format_notice": (
            "CAFF is proprietary and has no located official byte-level specification. "
            "Header/TOC meanings are based on public reverse-engineered decoders and "
            "direct validation. Extracted inner XML is preserved exactly; its class-level "
            "semantics are version-dependent and not flattened."
        ),
    }

    write_json(output_root / "manifest.json", manifest)
    write_json(output_root / "reconstruction_map.json", manifest["reconstruction"])
    write_inventory_csv(output_root / "inventory.csv", entries, results)

    summary_text = "\n".join(
        [
            "CMO3 / CAFF dump summary",
            "========================",
            f"Source: {input_path.resolve()}",
            f"Size: {file_size:,} bytes (0x{file_size:X})",
            f"SHA-256: {source_sha256}",
            f"Status: {status}",
            f"CAFF archive version: {'.'.join(map(str, header.archive_version))}",
            f"Format ID/version: {header.format_id!r} / {'.'.join(map(str, header.format_version))}",
            f"Obfuscation key: {header.obfuscation_key_signed} ({header.obfuscation_key_hex})",
            f"Entries: {len(entries):,}",
            f"Compression: {dict(sorted(compression_counts.items()))}",
            f"Detected extracted types: {dict(sorted(detected_counts.items()))}",
            f"Stored member bytes: {stored_total:,}",
            f"Extracted member bytes: {extracted_total:,}",
            f"Guard bytes: {guard_value!r} ({'valid' if guard_valid else 'unexpected'})",
            f"Declared byte coverage: {covered_bytes:,}/{file_size:,}",
            f"Reconstruction SHA-256 matches input: {reconstruction_matches}",
            f"Entry warnings/errors: {sum(bool(r.warnings) for r in results)}/{sum(bool(r.errors) for r in results)}",
            f"Global warnings: {len(global_warnings)}",
            f"Payload output budget accounted: {budget.used:,}/{effective_output_limit or 'unlimited'}",
            "",
            "Open manifest.json for every field, offset, hash, validation result,",
            "and the exact byte-preserving reconstruction map.",
            "Extracted content is under files/<entry-index>/... .",
            "Exact stored and XOR-decoded records are under stored_entries/ and",
            "deobfuscated_entries/.",
            "",
        ]
    )
    (output_root / "SUMMARY.txt").write_text(
        summary_text, encoding="utf-8", newline="\n"
    )

    if status == "complete":
        incomplete_marker.unlink()
    elif status == "complete_with_warnings":
        incomplete_marker.unlink()
        (output_root / "ATTENTION_REQUIRED.txt").write_text(
            "Extraction completed with warnings. Review manifest.json before use.\n",
            encoding="utf-8",
        )
    return manifest, {"complete": 0, "complete_with_errors": 3}.get(status, 4)


def print_listing(
    input_path: Path, header: CaffHeader, entries: list[CaffEntry], file_size: int
) -> None:
    print(f"File: {input_path.resolve()}")
    print(f"Size: {file_size:,} bytes (0x{file_size:X})")
    print(
        "CAFF: archive "
        + ".".join(map(str, header.archive_version))
        + f", format {header.format_id!r} "
        + ".".join(map(str, header.format_version))
    )
    print(
        f"Key: {header.obfuscation_key_signed} ({header.obfuscation_key_hex}); "
        f"entries: {len(entries):,}; index end: 0x{header.index_end:X}"
    )
    print("index  offset       size       obfs comp  tag/path")
    for entry in entries:
        print(
            f"{entry.index:6d}  0x{entry.start_pos:08X} {entry.file_size:10d} "
            f"{int(entry.is_obfuscated):4d} 0x{entry.compression_option:02X}  "
            f"{entry.tag!r} / {entry.file_path!r}"
        )


def parse_size(text: str) -> int:
    value = text.strip().lower().replace("_", "")
    multipliers = {
        "k": 1024,
        "kb": 1024,
        "m": 1024**2,
        "mb": 1024**2,
        "g": 1024**3,
        "gb": 1024**3,
    }
    for suffix in sorted(multipliers, key=len, reverse=True):
        if value.endswith(suffix):
            number = value[: -len(suffix)]
            return int(float(number) * multipliers[suffix])
    return int(value, 0)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory and losslessly extract Live2D CMO3/CAFF archives using "
            "only the Python standard library."
        )
    )
    parser.add_argument("input", type=Path, help="input .cmo3/.can3 CAFF file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="new output directory (default: <input-stem>_dump beside input)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print CAFF header and member table without writing files",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=DEFAULT_MAX_ENTRIES,
        help=f"metadata safety limit (default: {DEFAULT_MAX_ENTRIES})",
    )
    parser.add_argument(
        "--max-inflated-bytes",
        type=parse_size,
        default=DEFAULT_MAX_INFLATED_BYTES,
        metavar="N",
        help="per-member DEFLATE safety limit; accepts 512M/8G; 0 disables",
    )
    parser.add_argument(
        "--max-output-bytes",
        type=parse_size,
        default=None,
        metavar="N",
        help=(
            "aggregate binary payload-layer budget; default is automatic "
            "max(64M, 8x input); 0 disables"
        ),
    )
    parser.add_argument(
        "--max-validation-bytes",
        type=parse_size,
        default=DEFAULT_MAX_VALIDATION_BYTES,
        metavar="N",
        help=(
            "per-file XML/JSON size and PNG inflated-data validation limit; "
            "default 64M; 0 disables"
        ),
    )
    parser.add_argument(
        "--no-content-validation",
        action="store_true",
        help="skip PNG CRC/IDAT, XML, and JSON validation",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {PROGRAM_VERSION}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    input_path = args.input.expanduser().resolve()
    if not input_path.is_file():
        parser.error(f"input is not a regular file: {input_path}")
    if args.max_entries < 0:
        parser.error("--max-entries must be non-negative")
    if args.max_inflated_bytes < 0:
        parser.error("--max-inflated-bytes must be non-negative")
    if args.max_output_bytes is not None and args.max_output_bytes < 0:
        parser.error("--max-output-bytes must be non-negative")
    if args.max_validation_bytes < 0:
        parser.error("--max-validation-bytes must be non-negative")

    try:
        header, entries, file_size = parse_caff(input_path, args.max_entries)
        if args.list:
            print_listing(input_path, header, entries, file_size)
            return 0

        output = args.output
        if output is None:
            output = input_path.with_name(input_path.stem + "_dump")
        output = output.expanduser().resolve()
        if output.exists():
            raise CaffError(
                f"output path already exists; refusing to overwrite: {output}"
            )
        if output == input_path:
            raise CaffError("output directory cannot be the input file")

        manifest, code = dump_archive(
            input_path=input_path,
            output_root=output,
            max_entries=args.max_entries,
            max_inflated_bytes=args.max_inflated_bytes,
            validate_content=not args.no_content_validation,
            max_output_bytes=args.max_output_bytes,
            max_validation_bytes=args.max_validation_bytes,
        )
        summary = manifest["summary"]
        print(f"Output: {output}")
        print(
            f"Entries: {summary['entry_count']:,}; "
            f"errors: {summary['entry_error_count']}; "
            f"warnings: {summary['entry_warning_count']}"
        )
        print(f"Status: {manifest['status']}; exit code: {code}")
        print(
            "Exact reconstruction SHA-256 matches input: "
            f"{manifest['reconstruction']['matches_source_sha256']}"
        )
        return code
    except (CaffError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
