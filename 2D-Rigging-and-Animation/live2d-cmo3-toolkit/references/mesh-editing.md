# ArtMesh editing

## Contents

- Locate a mesh
- Coordinate arrays
- Position-only edits
- Topology edits
- UV edits
- Required validation

## Locate a mesh

Resolve active `CArtMeshSource` objects through `CDrawableSourceSet`. Identify the source by its `CDrawableId idstr`, `CDrawableGuid`, Part GUID, and `localName`. Display names are not guaranteed unique.

## Coordinate arrays

A typical ArtMesh contains:

- `CEditableMeshExtension/GEditableMesh2/float-array xs.n="point"`: editor mesh points in canvas/basic coordinates.
- Direct `float-array xs.n="positions"`: base source positions, two floats per vertex.
- `carray_list xs.n="keyforms"/CArtMeshForm/float-array xs.n="positions"`: deformed positions for every keyform.
- Direct `float-array xs.n="uvs"`: two floats per vertex.
- Direct `int-array xs.n="indices"`: triangle vertex indices, three per triangle.
- Editable-mesh `short-array xs.n="edge"`: endpoint pairs.
- `pointUid`, point/edge priority, mesh GUID, and coordinate-type references.

Do not confuse base positions with keyform positions. A mesh may use basic/canvas coordinates for its editable source but deformer-local coordinates for forms.

## Position-only edits

For a rigid translation `(dx, dy)`, update both base editor/source positions and every keyform consistently in the coordinate system where each array is expressed. If a parent deformer exists, a canvas-space delta may not equal its local-space delta; transform through the parent default form or keep the parent hierarchy unchanged.

For a scale around `(cx, cy)`:

```python
x2 = cx + (x - cx) * sx
y2 = cy + (y - cy) * sy
```

Apply the same intended geometric operation to all relevant forms. Leave `indices`, `edge`, `pointUid`, and UVs unchanged when vertex count and topology do not change.

## Topology edits

Adding or deleting a vertex requires coordinated updates to:

1. `GEditableMesh2/point`
2. base `positions`
3. `uvs`
4. every `CArtMeshForm/positions`
5. `pointUid` and `nextPointUid`
6. point priorities
7. `edge` and edge priorities
8. `indices`
9. every affected `count` attribute

Allocate a new unique point UID; do not reuse an existing UID. Re-triangulate deliberately. Every index must be within `[0, vertex_count - 1]`; `indices.count` must be divisible by three and `edge.count` by two.

Deleting vertices requires remapping every old index to its new index and removing triangles/edges that reference deleted vertices. Never truncate coordinate arrays without rebuilding topology.

## UV edits

UVs are paired coordinates aligned one-to-one with mesh vertices. Modify UVs when the source image changes placement inside a texture or atlas. Keep UV count equal to position count. If replacing an image with identical dimensions and pixel registration, UVs normally remain unchanged.

Changing atlas geometry may also require updating `CTextureInput_TextureAtlasRegion`, atlas transforms, and texture metadata. Prefer replacing pixels at identical dimensions when possible.

## Required validation

- Base position scalar count is even; vertex count is `count / 2`.
- UV scalar count equals base position scalar count.
- Every keyform position scalar count equals the base count.
- Actual token counts equal declared primitive-array counts.
- Indices are non-negative, in range, and grouped by three.
- Edges are in range and grouped by two.
- `pointUid` values are unique and match vertex count.
- All form GUIDs referenced by the keyform grid exist and point back to the correct source.

After XML validation, repack the new file. If the user requests or authorizes GUI verification, open only the new output in Cubism Editor for visual/manual confirmation.
