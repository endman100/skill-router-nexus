# Direct PSD-to-CMO3 compilation

## When this document is mandatory

Read this document in full whenever the task requires converting, exporting,
packaging, or compiling a layered PSD directly to an editable `.cmo3` without
launching or controlling Cubism Editor. Use the bundled compiler and template
described below; do not replace this workflow with GUI automation unless the
user explicitly asks for Editor control.

## Scope

Use `scripts/cmo3_compile_psd.py` to create a static editable Cubism 5.3
`.cmo3` directly from a flat layered PSD without launching Cubism Editor. The
result has one root-level quad ArtMesh per visible, non-empty top-level PSD
layer. It is a separated model project, not an automatically rigged model.

The bundled `assets/static-artmesh-83.cmo3` is a scrubbed 85 KB template. It
contains 83 generic ArtMesh slots, transparent 16/32/64 px icons, one
transparent 2048 px atlas, and `main.xml`; it contains no source character
artwork. Its CAFF and XML serializer metadata came from a verified Cubism
5.3.03 project and must be preserved.

## Command

The script requires Pillow and `psd-tools` in addition to the standard library.

```powershell
python "<skill-dir>\scripts\cmo3_compile_psd.py" `
  "<skill-dir>\assets\static-artmesh-83.cmo3" `
  "parts.psd" "parts.cmo3" `
  --report "parts.cmo3.report.json"
```

The output path and optional report path must not already exist. The default
atlas is 2048×2048 with two transparent padding pixels. Use `--atlas-size`
only when every retained crop still fits and the target Cubism version supports
that texture size.

## Compilation model

1. Read visible, non-empty top-level PSD layers in bottom-to-top order.
2. Trim fully transparent borders and retain each crop's canvas registration.
3. Pack crops losslessly into one RGBA PNG atlas.
4. Select reusable template ArtMeshes and rewrite each to one four-vertex,
   two-triangle root-level mesh.
5. Set canvas positions from the PSD crop bounds and UVs from the atlas bounds.
6. Reduce every selected source to one unbound keyform; clear clipping,
   deformer, and affecter dependencies.
7. Assign Parts by normalized layer prefix: hair, eye/eyeball, brow, ear, face,
   nose, mouth, neck, or Body fallback.
8. Replace only `main.xml` and the atlas entry, then rebuild the CAFF table,
   offsets, compression record, XOR state, and hashes.

Keep template icon paths unchanged. CAFF names such as `image_0.png` do not
encode dimensions, so guessing icon size from the filename is unsafe.

## Required validation

- Active ArtMesh count equals retained PSD layer count.
- Every active ArtMesh has eight position scalars, eight UV scalars, indices
  `1 0 2 1 2 3`, one keyform, and a ROOT target deformer.
- Every non-`ROOT` `xs.ref` resolves.
- Atlas UV rectangles are in range and reproduce the registered PSD crops.
- Repacked CAFF has zero range errors, gaps, or overlaps; replacement payloads
  byte-match; full dump reports valid XML, PNG, DEFLATE, guard, and exact
  reconstruction hash.
- For visual proof without Editor, independently render the active quads from
  the extracted atlas and compare the flattened image with the PSD composite.
  A maximum two-level RGB difference is acceptable for alpha-rounding.

## Limits

- Maximum 83 retained layers with the bundled template.
- Top-level pixel layers only; flatten or reject groups and unsupported layer
  types deliberately.
- ArtMeshes are static quads. Parameters remain available in the project, but
  no deformation, physics, clipping, masks, or parameter keyforms are inferred.
- The method targets the observed Cubism 5.3 serializer. Treat another major
  version as unsupported until tested with a valid template from that version.
- `.dmo3` is not a standard Cubism extension. Use `.cmo3` for the editable
  project and `.moc3` only for a separately exported runtime model.
