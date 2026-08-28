# Parameter, keyform, and deformer editing

## Contents

- Data relationships
- Change parameter ranges
- Edit keyform motion
- Add or remove keys
- Freeze or remove dynamics
- Validation

## Data relationships

`CParameterSourceSet` defines parameter GUID, ID, name, min/max/default, type, repeat state, and group. A `KeyformGridSource` owns grid positions and `KeyformBindingSource` references. Each binding points to a `CParameterGuid` and stores numeric key values. `KeyformOnGrid` maps binding key indices to a `CFormGuid`; source `keyforms` contain the actual ArtMesh or deformer forms.

The same parameter GUID can control many sources. Modify by GUID and dependency graph, not by description text alone.

## Change parameter ranges

When changing min/max/default:

1. Update the matching `CParameterSource` values.
2. Decide whether existing binding `keys` remain valid or need remapping.
3. Keep `defaultValue` within `[minValue, maxValue]`.
4. Update interpolation/extended interpolation only when intentionally changing behavior.
5. Preserve Parameter ID/GUID mappings and parameter-group membership.

A linear range remap from `[a, b]` to `[c, d]` is:

```python
new_value = c + (old_value - a) * (d - c) / (b - a)
```

Apply it to defaults and all binding keys for that parameter.

## Edit keyform motion

For an ArtMesh form, edit its `positions`, draw order, opacity, multiply/screen colors, or other supported form values. Keep its `CFormGuid` stable so the grid continues to resolve it. For Warp/Rotation deformers, edit the appropriate form fields while preserving the source’s coordinate type and target hierarchy.

To change interpolation timing without changing shapes, edit binding keys or interpolation types. To change shapes without changing timing, edit form data while preserving access keys.

## Add or remove keys

Adding a key requires synchronized changes to:

- binding `keys` and its count;
- grid `keyformsOnGrid` access-key combinations;
- new `CFormGuid` definitions;
- source `keyforms` with matching forms;
- any morph-target constraints referring to forms.

Removing a key is the reverse operation. Remove only forms no longer referenced by any grid or constraint, then garbage-collect unreachable shared definitions.

For a multidimensional grid, keyforms represent combinations of key indices. Do not assume the number of forms equals the sum of parameter key counts.

## Freeze or remove dynamics

To freeze a non-required deformer while preserving default placement:

1. Read each binding’s parameter default.
2. Find the grid form whose binding keys exactly match all defaults.
3. Keep that one `KeyformOnGrid` and clear its `_keyOnParameterList`.
4. Clear `keyformBindings`.
5. Keep the source form with the same `CFormGuid`; set the source keyform count to one.
6. Remove now-unreachable bindings/forms during graph garbage collection.

To delete a parameter completely, also remove it from parameter groups, effect groups, physics, viewer/random-pose settings, compatibility ID sets, and every binding. A globally closed `xs.ref` graph is necessary but not sufficient: ensure no active semantic mapping points to a removed source.

## Validation

- Every retained parameter GUID has exactly one active parameter source.
- Every binding key index is in range.
- Every grid form GUID resolves to a form owned by the expected source.
- Form counts and declared container counts agree.
- Every ArtMesh keyform has the same position count as its base mesh.
- Deleted parameters do not survive in physics, lip-sync, eye-blink, random-pose, viewer, or compatibility maps unless deliberately retained.
- Parent-deformer chains end at `ROOT` or a retained root GUID and contain no cycles.

