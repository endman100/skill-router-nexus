---
name: live2d-cmo3-toolkit
description: Directly compile flat layered PSDs into static Live2D Cubism .cmo3 projects, and inspect, fully unpack, edit, template-repack, or verify .cmo3/CAFF files with bundled Python tools. Use for CMO3 or mistyped DMO3/CLN3 requests involving PSD-to-CMO3 conversion without Editor control, archive extraction, CAFF analysis, main.xml object graphs, ArtMesh vertices/indices/UVs, parameters/keyforms/deformers, PNG/texture replacement, eye-only reduction, or safe reconstruction.
---

# Live2D CMO3 Toolkit

Treat “DMO3” or “CLN3” as a likely typo for `.cmo3`; verify the file magic is `CAFF` before modifying it. Distinguish editable `.cmo3` projects from runtime `.moc3` files.

## Operating rules

1. Preserve the source file. Always write to a new path and refuse overwrite.
2. Inspect and fully dump before editing. Record SHA-256, entry count, offsets, compression, and validation state.
3. Use an existing CMO3 or the bundled scrubbed static-ArtMesh asset as the repacking template. Do not invent unknown header or entry metadata.
4. Preserve the XML processing-instruction prefix, element order, `xs.id`/`xs.ref` identities, container `count` values, and all unknown fields.
5. Modify the smallest closed dependency set. Validate references, mesh topology, keyform shapes, and texture paths before repacking.
6. Re-unpack every produced CMO3 and require zero structural errors before claiming success. Open Cubism Editor only when the user requests GUI verification.

## Mandatory direct-compilation branch

If the request asks to convert, export, package, or compile a layered PSD directly
to an editable `.cmo3` without launching or controlling Cubism Editor, **read
[Direct PSD compilation](references/direct-psd-compilation.md) completely before
running any command or modifying the PSD**. Follow that child document as the
authoritative procedure, then use `scripts/cmo3_compile_psd.py` with
`assets/static-artmesh-83.cmo3`. Do not substitute Editor automation unless the
user explicitly requests it.

## Route to the required reference

Read only the documents needed for the request. All links are relative to this Skill.

| Task | Read | Use |
|---|---|---|
| Compile a flat layered PSD directly to static CMO3 without Editor control | **Read first:** [Direct PSD compilation](references/direct-psd-compilation.md) | `scripts/cmo3_compile_psd.py` + `assets/static-artmesh-83.cmo3` |
| Understand or decode CAFF | [CAFF container format](references/caff-container-format.md) | `scripts/cmo3_dump.py` |
| Understand or edit `main.xml` | [Cubism XML object graph](references/cubism-xml-object-model.md) | dump, edit a copy, then pack |
| Move vertices or change topology/UVs | [Mesh editing](references/mesh-editing.md) | XML editor code + `scripts/cmo3_pack.py` |
| Change parameters, keyforms, or deformers | [Animation editing](references/animation-editing.md) | XML editor code + `scripts/cmo3_pack.py` |
| Replace PNGs or texture inputs | [Image editing](references/image-editing.md) | `scripts/cmo3_pack.py --replace` |
| Rebuild and prove integrity | [Repacking and verification](references/repacking-and-validation.md) | pack, then full dump |
| Reduce a compatible model to its eye unit | [Eye-only reduction](references/eye-only-reduction.md) | `scripts/cmo3_eye_subset.py` |

## Bundled commands

Resolve `<skill-dir>` as the directory containing this `SKILL.md`.

```powershell
# List archive metadata without writing files.
python "<skill-dir>\scripts\cmo3_dump.py" "model.cmo3" --list

# Full lossless dump and validation.
python "<skill-dir>\scripts\cmo3_dump.py" "model.cmo3" -o "model_dump"

# Repack a modified main.xml while preserving all other entries.
python "<skill-dir>\scripts\cmo3_pack.py" "model.cmo3" "model_edited.cmo3" `
  --main-xml "edited_main.xml" --report "model_edited_report.json"

# Replace one or more canonical archive entries such as PNG files.
python "<skill-dir>\scripts\cmo3_pack.py" "model.cmo3" "model_images.cmo3" `
  --replace "image_321.png=edited_eye.png" `
  --replace "imageFileBuf_12.png=edited_source.png"

# Apply the reusable eye-only model-graph reduction workflow.
python "<skill-dir>\scripts\cmo3_eye_subset.py" "model.cmo3" "model_eyes.cmo3" `
  --report "model_eyes_report.json"

# Directly compile up to 83 flat visible PSD layers as static ArtMeshes.
python "<skill-dir>\scripts\cmo3_compile_psd.py" `
  "<skill-dir>\assets\static-artmesh-83.cmo3" `
  "parts.psd" "parts.cmo3" --report "parts.cmo3.report.json"
```

`cmo3_pack.py` replaces existing entries only. It preserves entry count, paths, tags, unknown bytes, and untouched stored payloads. It does not add/delete archive entries or support CAFF archives with an embedded preview.

`cmo3_compile_psd.py` produces registered static quad ArtMeshes; it does not infer rigging, physics, clipping, or parameter keyforms. It requires Pillow and `psd-tools`, accepts top-level pixel layers only, and uses the bundled Cubism 5.3 template.

Do not treat the bundled scripts as a universal typed `main.xml` editor. Cubism class layouts and dependency graphs vary by version and model. Implement each requested mesh/animation transformation as a small, reviewable XML edit using the relevant reference document, then pass the resulting XML to the generic packer.

## Required end-to-end workflow

For direct PSD compilation, first read the required child document above in full,
run `cmo3_compile_psd.py` with the bundled template, then continue at step 6.

1. Run `cmo3_dump.py --list`; reject non-CAFF files.
2. Run a full dump to a new directory and read `manifest.json` plus the canonical `main.xml` under `files/<index>/`.
3. Read the relevant modification document above.
4. Edit copied XML or image files; never edit the only source copy.
5. Run `cmo3_pack.py` with the original CMO3 as template.
6. Run `cmo3_dump.py` on the new CMO3 to a fresh directory.
7. Require: exit code 0, zero entry errors/warnings, zero gap/overlap, valid guard, valid XML/PNG/DEFLATE checks, and exact reconstruction hash match.
8. Compare semantic invariants for the requested edit. Examples: no dangling `xs.ref`, triangle indices within vertex bounds, all keyform position counts equal the base mesh count, and every XML `file path` resolves to an archive entry.
9. Report both what changed and what intentionally remains. In particular, deleting model ArtMeshes does not automatically remove embedded ModelImage/PNG assets.

## Scope and evidence level

Treat the outer CAFF layout as reverse-engineered, not an official Live2D specification. Treat `main.xml` class semantics as Editor-version-dependent observations. Prefer exact preservation and explicit failure over guessing. The bundled implementation was validated against a Cubism 5.3.03 CMO3 containing 505 entries, but future versions may introduce unsupported fields or compression modes.
