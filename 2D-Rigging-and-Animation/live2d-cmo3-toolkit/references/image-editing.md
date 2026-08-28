# Image and texture editing

## Contents

- Identify image entries
- Replace pixels safely
- Coordinate image and XML changes
- Remove physical assets
- Validation

## Identify image entries

Use the full dump’s `inventory.csv` and `manifest.json` to map CAFF paths to canonical PNGs. Cross-check every XML `<file path="...">` reference.

Common observed roles:

- `imageFileBuf*.png`: larger imported/source image buffers.
- `image*.png`: cached images, icons, layer/model images, or atlas-related images.

Names are observations, not a permanent schema. Resolve each image through `CTextureManager`, `CImageResource`, `CModelImage`, layer structures, `GTexture2D`, and ArtMesh `CTextureInputExtension` references before deciding its role.

## Replace pixels safely

Prefer a replacement with identical width, height, bit depth, color type, and pixel registration. Then run:

```powershell
python "<skill-dir>\scripts\cmo3_pack.py" "model.cmo3" "model_image_edit.cmo3" `
  --replace "image_321.png=edited_eye.png"
```

The packer accepts canonical clear file bytes. It applies the template entry’s compression wrapper and XOR state, updates stored size and every following offset, validates the temporary archive, then renames it.

Do not edit `stored_entries` or `deobfuscated_entries` and pass those wrappers as canonical PNG data. Use the PNG under `files/<entry-index>/...`.

## Coordinate image and XML changes

If dimensions or registration change, inspect and update:

- ArtMesh UV pairs;
- `CTextureInput_TextureAtlasRegion` transforms;
- texture-atlas region/size metadata;
- `CImageResource` width/height or cached-image metadata;
- ModelImage/layer transforms and canvas placement.

A pixel-only edit with identical geometry normally requires no UV or mesh change. Moving artwork inside the bitmap changes its relationship to UVs even when width/height remain equal.

If an imported source layer and an atlas/cached image both represent the same artwork, decide whether both must be updated. Cubism may regenerate caches after opening, so keep a backup and compare what Editor saves.

## Remove physical assets

Deleting ArtMeshes from active source sets does not remove embedded PNGs. Physical pruning requires all of the following:

1. Determine the exact image dependency closure of retained ArtMeshes.
2. Filter `CTextureManager`, ModelImage groups, layered-image/layer metadata, resources, filters, and every `<file>` reference.
3. Remove the corresponding CAFF entries and rebuild the entry count/table/offsets.
4. Confirm Cubism Editor can still open and edit the model.

The bundled `cmo3_pack.py` intentionally does not add/delete entries; it replaces existing entries only. Do not claim physical asset pruning when only the model graph was reduced.

## Validation

- Validate PNG signature, IHDR, every chunk CRC, IDAT zlib stream, and IEND.
- Ensure replacement dimensions match the intended texture metadata.
- Ensure each XML file path has exactly one CAFF entry.
- Ensure no retained XML reference points to a deleted image resource.
- Re-unpack and compare the replacement’s canonical SHA-256 with the supplied local file.
- Inspect atlas alignment, clipping masks, alpha edges, and mesh UV registration in Cubism Editor.

