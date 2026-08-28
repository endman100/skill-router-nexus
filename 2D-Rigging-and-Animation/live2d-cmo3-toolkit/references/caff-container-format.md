# CAFF container format

## Contents

- Scope
- Byte layout
- XOR rules
- File-info entries
- Compression records
- Repacking constraints

## Scope

CMO3 is an editable Cubism project; MOC3 is a runtime model. The observed CMO3 outer container begins with `CAFF`. Live2D does not publish a complete byte-level CMO3/CAFF specification, so preserve unknown data exactly and describe this layout as reverse-engineered.

## Byte layout

All outer multi-byte integers are big-endian. Embedded ZIP-local fields are little-endian.

| Offset | Size | Stored value |
|---:|---:|---|
| `0x00` | 4 | ASCII `CAFF` |
| `0x04` | 3 | archive version bytes |
| `0x07` | 4 | format identifier, commonly `----` |
| `0x0B` | 3 | format version bytes |
| `0x0E` | 4 | signed BE `s32` XOR key |
| `0x12` | 8 | unknown/reserved; preserve |
| `0x1A` | 20 | preview descriptor |
| `0x2E` | 8 | unknown/reserved; preserve |
| `0x36` | 4 | encoded file-info count |
| `0x3A` | variable | file-info table |

Payloads normally follow the table. The final two bytes observed by public decoders are ASCII `bc` (`62 63`), used as a guard rather than a known archive checksum.

Preview descriptor fields are format byte, color byte, two reserved bytes, BE width/height, BE absolute start (`u64`), and BE size (`u32`). The bundled packers reject non-empty previews because cross-version preview relocation/obfuscation is not fully established.

## XOR rules

Read the key as signed BE 32-bit, then derive masks:

```python
key_signed = struct.unpack(">i", raw_key)[0]
k8 = key_signed & 0xFF
k32 = key_signed & 0xFFFF_FFFF
k64 = ((key_signed << 32) | key_signed) & 0xFFFF_FFFF_FFFF_FFFF
```

Decode encoded scalar fields with XOR. The signed extension in `k64` matters for negative keys.

Paths and tags use XOR-obfuscated Big-Endian Base-128 lengths, not little-endian LEB128. Decode each byte with `k8`, shift the accumulated value left seven bits, and stop when bit 7 is clear. XOR each following UTF-8 byte with `k8`.

## File-info entries

Each entry stores:

```text
encoded BE-base-128 path byte length
encoded UTF-8 path bytes
encoded BE-base-128 tag byte length
encoded UTF-8 tag bytes
encoded BE u64 absolute payload start
encoded BE u32 stored payload size
encoded u8 is_obfuscated
encoded u8 compression option
raw 8-byte reserved field
```

If `is_obfuscated != 0`, XOR every stored payload byte with `k8` before interpreting the content.

Known compression values:

| Value | Meaning | Canonical payload |
|---:|---|---|
| `0x10` | RAW | clear bytes after optional XOR |
| `0x21` | FAST | ZIP local record containing raw DEFLATE |
| `0x25` | SMALL | ZIP local record containing raw DEFLATE |

Preserve unknown options as stored/deobfuscated evidence. Do not pretend they were decompressed.

## Compression records

Compressed entries can be a single ZIP local-file record without a central directory or EOCD. Do not require Python `zipfile` to accept it.

Parse the 30-byte little-endian local header, variable filename, variable extra field, raw DEFLATE stream, and optional data descriptor. Flag `0x0008` means CRC and sizes are supplied in the descriptor. Validate DEFLATE EOF, CRC32, compressed size, uncompressed size, and unexpected trailing bytes.

## Repacking constraints

- Recalculate the file-info table, every absolute start, and every stored size.
- Preserve original path/tag bytes, flags, compression option, reserved bytes, ZIP filename/extra, DOS timestamps, and guard unless deliberately changing a supported field.
- XOR rebuilt records exactly like their template entries.
- Write to a temporary file, validate ranges/coverage and replacement bytes, then rename.
- Use `scripts/cmo3_pack.py` for replacing existing entries. Adding/removing entries or relocating preview data requires additional implementation and validation.

