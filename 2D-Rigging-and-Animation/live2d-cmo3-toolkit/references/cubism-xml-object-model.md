# Cubism `main.xml` object graph

## Contents

- Serialization model
- Definitions and references
- Active source sets
- Safe parsing and writing
- Dependency-safe deletion

## Serialization model

The canonical inner model is a version-dependent Java-style XML serialization, not a flat settings document.

```xml
<root fileFormatVersion="...">
  <shared>...</shared>
  <main><CModelSource>...</CModelSource></main>
</root>
```

The prefix commonly contains `<?version Class:n?>` and `<?import package.Class?>` processing instructions. Preserve it byte-for-byte.

Primitive tags include `s`, `i`, `l`, `f`, `b`, and `null`. Arrays include `float-array`, `int-array`, `short-array`, `byte-array`, and `long-array`. Containers include `array_list`, `carray_list`, `hash_map`, `linked_map`, and `linked_set`.

## Definitions and references

- `xs.id`: shared object identity, typically `#number`.
- `xs.ref`: reference to a shared identity or the special value `ROOT`.
- `xs.idx`: serialized shared-table index; preserve unless fully rebuilding the serializer.
- `xs.n`: field name.

Build a map of every direct `<shared>` child by `xs.id`. After editing, every non-`ROOT` `xs.ref` must resolve. Do not renumber IDs merely to make them contiguous.

## Active source sets

The `<CModelSource>` under `<main>` roots the active editable model through sets such as:

- `CParameterSourceSet`
- `CDrawableSourceSet`
- `CDeformerSourceSet`
- `CAffecterSourceSet`
- `CPartSourceSet`
- `CPhysicsSettingsSourceSet`
- `CParameterGroupSet`
- `CTextureManager`

Removing a shared definition alone is insufficient if an active source set or Part `_childGuids` still points to it. Conversely, removing an object from a source set but leaving compatibility metadata can preserve stale semantic GUID mappings.

## Safe parsing and writing

Split the exact prefix before `<root`, parse only the root body, and concatenate the untouched prefix with the serialized root:

```python
marker = xml_bytes.find(b"<root")
prefix = xml_bytes[:marker]
root = ET.fromstring(xml_bytes[marker:])

# Modify root here.

result = prefix + ET.tostring(
    root, encoding="utf-8", short_empty_elements=True
)
```

ElementTree normalizes line endings inside the parsed body. That is acceptable for XML semantics but means a modified document is not byte-identical. Never use a generic XML-to-JSON round trip because it can lose processing instructions, order, typed containers, repeated map entries, and identity cycles.

Whenever children of `array_list`, `carray_list`, `linked_set`, or `hash_map` change, update the `count` attribute to the number of child elements. Primitive-array `count` describes scalar values, not XML child nodes.

## Dependency-safe deletion

1. Select active seed sources by stable IDs/Part membership, not display-name substring alone.
2. Follow `targetDeformerGuid` ancestry until `ROOT` or an unsourced root GUID.
3. Retain owning Parts and their parent chain.
4. Retain clipping-mask Drawable GUIDs.
5. Filter source sets and each Part `_childGuids` list.
6. Filter parameter groups, effect groups, physics, random-pose, viewer, and compatibility mappings.
7. Compute reachability from `<main>` through `xs.ref`; remove only unreachable shared definitions.
8. Assert zero dangling references and consistent container counts.

Do not delete texture-manager definitions merely because no ArtMesh is visible. Decide separately whether the request concerns the editable model graph or physical embedded assets.

