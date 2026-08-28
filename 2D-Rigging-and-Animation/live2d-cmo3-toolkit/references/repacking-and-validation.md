# Repacking and validation

## Contents

- Template-based replacement
- Commands
- Automated gates
- Semantic gates
- Failure handling

## Template-based replacement

Use the original CMO3 as a template. `scripts/cmo3_pack.py` preserves the fixed header, unknown/reserved bytes, path/tag bytes, entry flags, untouched stored payloads, and guard. It rebuilds compression records only for replaced compressed entries and recalculates the complete TOC.

The packer replaces existing canonical entry payloads. It does not add/delete paths, change tags, or handle embedded previews. It refuses to overwrite the template or an existing output.

## Commands

```powershell
# Replace modified main.xml.
python "<skill-dir>\scripts\cmo3_pack.py" "source.cmo3" "edited.cmo3" `
  --main-xml "main.edited.xml" --report "edited.pack.json"

# Replace XML and multiple PNG entries in one archive build.
python "<skill-dir>\scripts\cmo3_pack.py" "source.cmo3" "edited.cmo3" `
  --main-xml "main.edited.xml" `
  --replace "image_12.png=eye.png" `
  --replace "imageFileBuf_3.png=eye_source.png"

# Independently unpack the result.
python "<skill-dir>\scripts\cmo3_dump.py" "edited.cmo3" -o "edited_verified"
```

## Automated gates

Require fresh evidence from the produced file:

- CAFF magic and decoded count valid.
- Header/index and every payload range within EOF.
- Zero gaps and overlaps across header/index, payloads, preview if supported, and guard.
- Final guard equals `bc`.
- Every replaced canonical payload byte-matches the supplied file.
- DEFLATE reaches EOF and CRC/sizes match.
- XML parses; PNG structure/CRC/IDAT validate.
- Reconstruction fragments hash to the exact produced CMO3 SHA-256.
- No temporary file remains after success or failure.

Identity testing is valuable: packing without replacements, or replacing an entry with identical canonical bytes, should preserve the archive byte-for-byte when the wrapper is reused unchanged. Rebuilt compressed records may differ in compressed bytes while remaining semantically identical, so compare canonical payloads as well as archive structure.

## Semantic gates

Archive integrity does not prove model correctness. Also validate:

- zero dangling non-`ROOT` `xs.ref`;
- active source-set counts and Part child lists;
- mesh indices, vertex/UV/form counts;
- parameter bindings and key indices;
- parent-deformer ancestry;
- texture file paths and dimensions;
- absence of deleted objects from compatibility/effect/physics/viewer metadata.

When GUI verification is authorized, open only the new output. Check the canvas plus Parts, Parameters, Deformers, Model Images, and Texture Atlas panels. Never save over the source during verification.

## Failure handling

Treat nonzero exit codes, warnings, skipped validations, unknown compression, preview presence, or XML reference errors as incomplete work. Keep the source and diagnostic dump. Do not bypass size/output limits until the target and available storage have been reviewed.

