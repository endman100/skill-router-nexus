#!/usr/bin/env python3
"""Lossless conservative text chunking, with no network or model dependency."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys


def split_chunks(text: str, max_chars: int = 6000) -> list[str]:
    """Keep fenced code/frontmatter intact; refuse oversized atomic blocks."""
    if max_chars < 1:
        raise ValueError('max_chars must be positive')
    if not text:
        return []
    lines = text.splitlines(keepends=True)
    blocks: list[str] = []
    current: list[str] = []
    fence = None
    frontmatter = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if index == 0:
            stripped = stripped.lstrip('\ufeff')  # Detect BOM-prefixed metadata without dropping bytes.
        if index == 0 and stripped == '---':
            frontmatter = True
            current.append(line)
            continue
        if frontmatter:
            current.append(line)
            if stripped in {'---','...'}:
                frontmatter = False
                blocks.append(''.join(current)); current = []
            continue
        if fence:
            current.append(line)
            if re.fullmatch(re.escape(fence[0]) + '{' + str(fence[1]) + ',}', stripped):
                fence = None
            continue
        match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line.rstrip('\r\n'))
        if match:
            fence = (match.group(1)[0],len(match.group(1)))
        current.append(line)
        if not stripped and fence is None:
            blocks.append(''.join(current)); current = []
    if frontmatter or fence:
        raise ValueError('Unclosed frontmatter or fenced code; inspect the source')
    if current:
        blocks.append(''.join(current))
    chunks: list[str] = []
    current_text = ''
    for block in blocks:
        if len(block) > max_chars:
            raise ValueError('Atomic block exceeds max_chars; split semantically or extract fields first')
        if current_text and len(current_text)+len(block) > max_chars:
            chunks.append(current_text); current_text = ''
        current_text += block
    if current_text:
        chunks.append(current_text)
    assert ''.join(chunks) == text
    return chunks


def write_chunks(source: Path, output: Path, max_chars: int = 6000) -> dict:
    raw = source.read_bytes()
    text = raw.decode('utf-8')  # Preserve BOM and original newline bytes on re-encoding.
    chunks = split_chunks(text,max_chars)
    output.mkdir(parents=True,exist_ok=False)  # Never overwrite an existing task directory.
    try:
        records = []
        for index, chunk in enumerate(chunks,1):
            name = f'chunk-{index:04d}.txt'
            data = chunk.encode('utf-8')
            (output/name).write_bytes(data)
            records.append({'file':name,'characters':len(chunk),'sha256':hashlib.sha256(data).hexdigest()})
        manifest = {'source_sha256':hashlib.sha256(raw).hexdigest(),
                    'max_chars':max_chars,'token_budget_verified':False,'chunks':records}
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        return manifest
    except Exception:
        shutil.rmtree(output)  # Only the new directory created by this call.
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--max-chars',type=int,default=6000)
    parser.add_argument('--output-dir',type=Path,required=True)
    args = parser.parse_args()
    try:
        manifest = write_chunks(args.source,args.output_dir,args.max_chars)
        print(json.dumps({'chunks':len(manifest['chunks']),'output_dir':str(args.output_dir),'token_budget_verified':False}))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(str(exc),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
