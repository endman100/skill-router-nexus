#!/usr/bin/env python3
"""Create an eye-only Live2D Cubism CMO3 from a Cubism 5 CAFF archive.

The tool keeps the eye and eyeball Parts, their ArtMeshes, the six eye
parameters, and the deformer ancestry required to preserve coordinates. Any
retained deformer controlled by a non-eye parameter is collapsed to its
default keyform. The original file is never overwritten.

This is an independently reverse-engineered utility, not an official Live2D
format implementation. It uses only the Python standard library plus the
sibling ``cmo3_dump.py`` module.
"""

from __future__ import annotations

import argparse
import binascii
import copy
import json
import math
import os
import struct
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET

import cmo3_dump


PROGRAM_VERSION = "1.1.0"
DEFAULT_EYE_PART_NAMES = ("Eye", "Eyeball")
DEFAULT_EYE_PARAMETER_NAMES = frozenset(
    {
        "Eye L Open",
        "Eye L Smile",
        "Eye R Open",
        "Eye R Smile",
        "Eyeball X",
        "Eyeball Y",
    }
)
ZIP_LOCAL = struct.Struct("<4s5H3I2H")


class EyeSubsetError(Exception):
    """The input cannot be reduced or repacked safely."""


def xs_attr(element: ET.Element, name: str) -> str | None:
    return element.attrib.get(f"xs.{name}")


def named_text(element: ET.Element, name: str) -> str:
    return next(
        (
            child.text or ""
            for child in element.iter("s")
            if xs_attr(child, "n") == name
        ),
        "",
    )


def named_ref(element: ET.Element, tag: str, name: str) -> str | None:
    return next(
        (
            xs_attr(child, "ref")
            for child in element.iter(tag)
            if xs_attr(child, "n") == name
        ),
        None,
    )


def parse_xml_document(xml_bytes: bytes) -> tuple[bytes, ET.Element]:
    """Return the exact processing-instruction prefix and parsed root."""

    marker = xml_bytes.find(b"<root")
    if marker < 0:
        raise EyeSubsetError("main.xml has no <root> element")
    prefix = xml_bytes[:marker]
    try:
        root = ET.fromstring(xml_bytes[marker:])
    except ET.ParseError as exc:
        raise EyeSubsetError(f"main.xml is not well-formed XML: {exc}") from exc
    if root.tag != "root":
        raise EyeSubsetError(f"unexpected document root: {root.tag!r}")
    return prefix, root


def serialize_xml_document(prefix: bytes, root: ET.Element) -> bytes:
    return prefix + ET.tostring(root, encoding="utf-8", short_empty_elements=True)


def _definitions(shared: ET.Element) -> dict[str, ET.Element]:
    definitions = {
        object_id: item
        for item in shared
        if (object_id := xs_attr(item, "id")) is not None
    }
    if len(definitions) != len(shared):
        raise EyeSubsetError("shared contains an entry without a unique xs.id")
    return definitions


def _list_child(parent: ET.Element, list_name: str) -> ET.Element:
    result = next(
        (
            child
            for child in parent
            if xs_attr(child, "n") == list_name and "count" in child.attrib
        ),
        None,
    )
    if result is None:
        raise EyeSubsetError(f"missing list {list_name!r} under {parent.tag}")
    return result


def _required_child(parent: ET.Element, tag: str, message: str) -> ET.Element:
    result = parent.find(tag)
    if result is None:
        raise EyeSubsetError(message)
    return result


def _set_list_items(container: ET.Element, retained: Iterable[ET.Element]) -> None:
    items = list(retained)
    for child in list(container):
        container.remove(child)
    container.extend(items)
    container.set("count", str(len(items)))


def _source_guid(source: ET.Element, tag: str) -> str | None:
    return named_ref(source, tag, "guid")


def _parameter_inventory(
    model: ET.Element,
) -> tuple[ET.Element, dict[str, ET.Element], dict[str, float]]:
    source_list = _list_child(
        _required_child(
            model, "CParameterSourceSet", "model has no CParameterSourceSet"
        ),
        "_sources",
    )
    by_name: dict[str, ET.Element] = {}
    defaults: dict[str, float] = {}
    for source in source_list:
        name = next(
            (
                child.text or ""
                for child in source
                if child.tag == "s" and xs_attr(child, "n") == "name"
            ),
            "",
        )
        guid = named_ref(source, "CParameterGuid", "guid")
        default_text = next(
            (
                child.text
                for child in source
                if child.tag == "f" and xs_attr(child, "n") == "defaultValue"
            ),
            None,
        )
        if name:
            by_name[name] = source
        if guid and default_text is not None:
            defaults[guid] = float(default_text)
    return source_list, by_name, defaults


def _grid_for_source(
    source: ET.Element, definitions: dict[str, ET.Element]
) -> ET.Element:
    grid_ref = next(
        (
            item
            for item in source.iter("KeyformGridSource")
            if xs_attr(item, "n") == "keyformGridSource"
        ),
        None,
    )
    if grid_ref is None:
        raise EyeSubsetError(
            f"{named_text(source, 'localName')!r} has no keyformGridSource"
        )
    reference = xs_attr(grid_ref, "ref")
    if reference:
        try:
            return definitions[reference]
        except KeyError as exc:
            raise EyeSubsetError(f"missing grid definition {reference}") from exc
    return grid_ref


def _binding_parameter_guid(
    binding_ref: str, definitions: dict[str, ET.Element]
) -> str:
    try:
        binding = definitions[binding_ref]
    except KeyError as exc:
        raise EyeSubsetError(f"missing binding definition {binding_ref}") from exc
    guid = named_ref(binding, "CParameterGuid", "parameterGuid")
    if not guid:
        raise EyeSubsetError(f"binding {binding_ref} has no parameterGuid")
    return guid


def _binding_keys(binding_ref: str, definitions: dict[str, ET.Element]) -> list[float]:
    binding = definitions[binding_ref]
    keys = next(
        (
            child
            for child in binding
            if child.tag == "array_list" and xs_attr(child, "n") == "keys"
        ),
        None,
    )
    if keys is None:
        raise EyeSubsetError(f"binding {binding_ref} has no keys")
    return [float(child.text or "0") for child in keys]


def _grid_parameter_guids(
    grid: ET.Element, definitions: dict[str, ET.Element]
) -> set[str]:
    result: set[str] = set()
    for item in grid.iter("KeyformBindingSource"):
        if reference := xs_attr(item, "ref"):
            result.add(_binding_parameter_guid(reference, definitions))
    return result


def _default_form_guid(
    grid: ET.Element,
    definitions: dict[str, ET.Element],
    parameter_defaults: dict[str, float],
) -> str:
    keyforms = _list_child(grid, "keyformsOnGrid")
    best: tuple[float, str] | None = None
    for keyform in keyforms:
        guid = named_ref(keyform, "CFormGuid", "keyformGuid")
        if not guid:
            continue
        score = 0.0
        access = next(keyform.iter("KeyformGridAccessKey"), None)
        if access is None:
            continue
        for key_on_parameter in access.iter("KeyOnParameter"):
            binding_ref = named_ref(
                key_on_parameter, "KeyformBindingSource", "binding"
            )
            index_text = next(
                (
                    item.text
                    for item in key_on_parameter
                    if item.tag == "i" and xs_attr(item, "n") == "keyIndex"
                ),
                None,
            )
            if binding_ref is None or index_text is None:
                raise EyeSubsetError("malformed KeyOnParameter")
            parameter_guid = _binding_parameter_guid(binding_ref, definitions)
            keys = _binding_keys(binding_ref, definitions)
            index = int(index_text)
            if index < 0 or index >= len(keys):
                raise EyeSubsetError(f"keyIndex {index} is out of range")
            if parameter_guid not in parameter_defaults:
                raise EyeSubsetError(
                    f"no default value for parameter {parameter_guid}"
                )
            score += abs(keys[index] - parameter_defaults[parameter_guid])
        candidate = (score, guid)
        if best is None or candidate < best:
            best = candidate
    if best is None or not math.isclose(best[0], 0.0, abs_tol=1e-6):
        raise EyeSubsetError("keyform grid has no exact default-value form")
    return best[1]


def _collapse_deformer_to_default(
    source: ET.Element,
    definitions: dict[str, ET.Element],
    parameter_defaults: dict[str, float],
) -> None:
    grid = _grid_for_source(source, definitions)
    default_guid = _default_form_guid(grid, definitions, parameter_defaults)

    keyforms_on_grid = _list_child(grid, "keyformsOnGrid")
    selected_grid_form = next(
        (
            item
            for item in keyforms_on_grid
            if named_ref(item, "CFormGuid", "keyformGuid") == default_guid
        ),
        None,
    )
    if selected_grid_form is None:
        raise EyeSubsetError(f"default form {default_guid} is absent from grid")
    access_parameters = next(
        (
            item
            for item in selected_grid_form.iter()
            if xs_attr(item, "n") == "_keyOnParameterList"
        ),
        None,
    )
    if access_parameters is None:
        raise EyeSubsetError("default form has no parameter access list")
    _set_list_items(access_parameters, [])
    _set_list_items(keyforms_on_grid, [selected_grid_form])
    _set_list_items(_list_child(grid, "keyformBindings"), [])

    forms = _list_child(source, "keyforms")
    selected_form = next(
        (
            item
            for item in forms
            if named_ref(item, "CFormGuid", "guid") == default_guid
        ),
        None,
    )
    if selected_form is None:
        raise EyeSubsetError(
            f"source {named_text(source, 'localName')!r} lacks default form"
        )
    _set_list_items(forms, [selected_form])


def _filter_part_children(
    part: ET.Element,
    active_part_guids: set[str],
    active_deformer_guids: set[str],
    active_drawable_guids: set[str],
) -> None:
    child_list = next(
        (
            item
            for item in part.iter()
            if xs_attr(item, "n") == "_childGuids" and "count" in item.attrib
        ),
        None,
    )
    if child_list is None:
        raise EyeSubsetError(f"part {named_text(part, 'localName')!r} has no child list")
    allowed = active_part_guids | active_deformer_guids | active_drawable_guids
    _set_list_items(
        child_list,
        [item for item in child_list if xs_attr(item, "ref") in allowed],
    )


def _filter_parameter_groups(
    model: ET.Element,
    definitions: dict[str, ET.Element],
    wanted_group_names: set[str],
) -> None:
    group_set = model.find("CParameterGroupSet")
    if group_set is None:
        raise EyeSubsetError("model has no CParameterGroupSet")
    groups = _list_child(group_set, "_groups")
    root_ref = next((item for item in groups if xs_attr(item, "ref")), None)
    if root_ref is None:
        raise EyeSubsetError("parameter group set has no root group")
    retained_inline = [
        item for item in groups if not xs_attr(item, "ref") and named_text(item, "name") in wanted_group_names
    ]
    retained_guids = {
        named_ref(item, "CParameterGroupGuid", "guid") for item in retained_inline
    }
    retained_guids.discard(None)
    _set_list_items(groups, [root_ref, *retained_inline])

    root_id = xs_attr(root_ref, "ref")
    root_group = definitions.get(root_id or "")
    if root_group is None:
        raise EyeSubsetError("root parameter group definition is missing")
    children = next(
        (
            item
            for item in root_group.iter()
            if xs_attr(item, "n") == "_childGuids" and "count" in item.attrib
        ),
        None,
    )
    if children is None:
        raise EyeSubsetError("root parameter group has no child list")
    _set_list_items(
        children,
        [item for item in children if xs_attr(item, "ref") in retained_guids],
    )


def _clear_non_eye_behaviors(model: ET.Element, eye_parameter_guids: set[str]) -> None:
    model_info = model.find("CModelInfo")
    if model_info is not None:
        effect_groups = next(
            (
                item
                for item in model_info.iter("hash_map")
                if xs_attr(item, "n") == "_parameterGroups"
            ),
            None,
        )
        if effect_groups is not None:
            _set_list_items(
                effect_groups,
                [
                    item
                    for item in effect_groups
                    if {
                        xs_attr(ref, "ref")
                        for ref in item.iter("CParameterGuid")
                        if xs_attr(ref, "ref")
                    }
                    <= eye_parameter_guids
                ],
            )

    physics = model.find("CPhysicsSettingsSourceSet")
    if physics is not None:
        sources = next(
            (item for item in physics if xs_attr(item, "n") == "_sourceCubismPhysics"),
            None,
        )
        if sources is not None:
            _set_list_items(sources, [])
        selected = next(
            (item for item in physics if xs_attr(item, "n") == "selectedCubismPhysics"),
            None,
        )
        if selected is not None:
            selected.tag = "null"
            selected.attrib.clear()
            selected.set("xs.n", "selectedCubismPhysics")
            selected.text = None
            for child in list(selected):
                selected.remove(child)

    random_pose = model.find("CRandomPoseSettingManager")
    if random_pose is not None:
        settings = next(
            (item for item in random_pose if xs_attr(item, "n") == "_settings"),
            None,
        )
        if settings is not None:
            _set_list_items(settings, [])
        current = next(
            (item for item in random_pose if xs_attr(item, "n") == "currentIndex"),
            None,
        )
        if current is not None:
            current.text = "-1"

    viewer = model.find("ModelViewerSetting")
    if viewer is not None:
        tracks = next(
            (item for item in viewer if xs_attr(item, "n") == "trackCursorSettings"),
            None,
        )
        if tracks is not None:
            _set_list_items(
                tracks,
                [
                    item
                    for item in tracks
                    if all(
                        xs_attr(ref, "ref") in eye_parameter_guids
                        for ref in item.iter("CParameterGuid")
                        if xs_attr(ref, "ref")
                    )
                ],
            )


def _filter_compatibility_id_sets(
    model: ET.Element, active_semantic_guids: set[str]
) -> int:
    model_options = next(
        (
            item
            for item in model.findall("hash_map")
            if xs_attr(item, "n") == "modelOptions"
        ),
        None,
    )
    if model_options is None:
        return 0
    compatibility = next(
        model_options.iter("CompatibilityOption_Cubism21to30"), None
    )
    if compatibility is None:
        return 0
    id_sets = next(
        (
            item
            for item in compatibility
            if xs_attr(item, "n") == "idSets" and "count" in item.attrib
        ),
        None,
    )
    if id_sets is None:
        return 0
    semantic_tags = {
        "CParameterGuid",
        "CDrawableGuid",
        "CDeformerGuid",
        "CPartGuid",
        "CAffecterGuid",
    }
    retained: list[ET.Element] = []
    for id_set in id_sets:
        references = {
            xs_attr(item, "ref")
            for item in id_set.iter()
            if item.tag in semantic_tags and xs_attr(item, "ref")
        }
        if not references or references <= active_semantic_guids:
            retained.append(id_set)
    _set_list_items(id_sets, retained)
    return len(retained)


def _garbage_collect_shared(root: ET.Element) -> int:
    shared = root.find("shared")
    main = root.find("main")
    if shared is None or main is None:
        raise EyeSubsetError("document lacks shared or main")
    definitions = _definitions(shared)

    def references(element: ET.Element) -> set[str]:
        return {
            reference
            for item in element.iter()
            if (reference := xs_attr(item, "ref")) and reference != "ROOT"
        }

    pending = list(references(main))
    retained: set[str] = set()
    while pending:
        object_id = pending.pop()
        if object_id in retained:
            continue
        if object_id not in definitions:
            raise EyeSubsetError(f"dangling reference before GC: {object_id}")
        retained.add(object_id)
        pending.extend(references(definitions[object_id]) - retained)

    removed = 0
    for item in list(shared):
        if xs_attr(item, "id") not in retained:
            shared.remove(item)
            removed += 1
    return removed


def _assert_closed_references(root: ET.Element) -> None:
    shared = root.find("shared")
    if shared is None:
        raise EyeSubsetError("document has no shared section")
    ids = {xs_attr(item, "id") for item in shared if xs_attr(item, "id")}
    dangling = sorted(
        {
            reference
            for item in root.iter()
            if (reference := xs_attr(item, "ref"))
            and reference != "ROOT"
            and reference not in ids
        }
    )
    if dangling:
        raise EyeSubsetError(f"reduced XML has dangling references: {dangling[:8]}")


def reduce_to_eye_model(
    xml_bytes: bytes,
    eye_part_names: Iterable[str] = DEFAULT_EYE_PART_NAMES,
    eye_parameter_names: Iterable[str] = DEFAULT_EYE_PARAMETER_NAMES,
) -> tuple[bytes, dict]:
    prefix, parsed_root = parse_xml_document(xml_bytes)
    root = copy.deepcopy(parsed_root)
    shared = root.find("shared")
    main_container = root.find("main")
    if shared is None or main_container is None or len(main_container) != 1:
        raise EyeSubsetError("unexpected Cubism XML shared/main layout")
    model = main_container[0]
    definitions = _definitions(shared)

    wanted_part_names = set(eye_part_names)
    wanted_parameter_names = set(eye_parameter_names)
    part_sources = list(shared.findall("CPartSource"))
    part_by_guid = {
        guid: source
        for source in part_sources
        if (guid := _source_guid(source, "CPartGuid"))
    }
    eye_part_guids = {
        guid
        for guid, source in part_by_guid.items()
        if named_text(source, "localName") in wanted_part_names
    }
    missing_parts = wanted_part_names - {
        named_text(source, "localName")
        for source in part_sources
        if _source_guid(source, "CPartGuid") in eye_part_guids
    }
    if missing_parts:
        raise EyeSubsetError(f"eye Parts not found: {sorted(missing_parts)}")

    selected_art_meshes = [
        source
        for source in shared.findall("CArtMeshSource")
        if named_ref(source, "CPartGuid", "parentGuid") in eye_part_guids
    ]
    if not selected_art_meshes:
        raise EyeSubsetError("no ArtMesh belongs to the selected eye Parts")
    selected_art_ids = {xs_attr(source, "id") for source in selected_art_meshes}
    selected_art_ids.discard(None)
    selected_drawable_guids = {
        guid
        for source in selected_art_meshes
        if (guid := _source_guid(source, "CDrawableGuid"))
    }

    parameter_list, parameters_by_name, parameter_defaults = _parameter_inventory(model)
    missing_parameters = wanted_parameter_names - parameters_by_name.keys()
    if missing_parameters:
        raise EyeSubsetError(
            f"eye parameters not found: {sorted(missing_parameters)}"
        )
    retained_parameters = [parameters_by_name[name] for name in parameters_by_name if name in wanted_parameter_names]
    eye_parameter_guids = {
        guid
        for source in retained_parameters
        if (guid := named_ref(source, "CParameterGuid", "guid"))
    }
    _set_list_items(parameter_list, retained_parameters)

    deformer_sources = [
        *shared.findall("CWarpDeformerSource"),
        *shared.findall("CRotationDeformerSource"),
    ]
    deformer_by_guid = {
        guid: source
        for source in deformer_sources
        if (guid := _source_guid(source, "CDeformerGuid"))
    }
    required_deformer_guids = {
        guid
        for source in selected_art_meshes
        if (guid := named_ref(source, "CDeformerGuid", "targetDeformerGuid"))
        and guid != "ROOT"
    }
    pending = list(required_deformer_guids)
    while pending:
        guid = pending.pop()
        source = deformer_by_guid.get(guid)
        if source is None:
            raise EyeSubsetError(f"required deformer has no source: {guid}")
        parent = named_ref(source, "CDeformerGuid", "targetDeformerGuid")
        if parent and parent != "ROOT" and parent in deformer_by_guid and parent not in required_deformer_guids:
            required_deformer_guids.add(parent)
            pending.append(parent)
    retained_deformers = [
        source
        for source in deformer_sources
        if _source_guid(source, "CDeformerGuid") in required_deformer_guids
    ]

    animated_deformer_guids: set[str] = set()
    static_deformer_guids: set[str] = set()
    for source in retained_deformers:
        guid = _source_guid(source, "CDeformerGuid")
        grid = _grid_for_source(source, definitions)
        grid_parameters = _grid_parameter_guids(grid, definitions)
        if grid_parameters and grid_parameters <= eye_parameter_guids:
            animated_deformer_guids.add(guid or "")
        else:
            _collapse_deformer_to_default(source, definitions, parameter_defaults)
            static_deformer_guids.add(guid or "")

    required_part_guids = set(eye_part_guids)
    for source in [*selected_art_meshes, *retained_deformers]:
        if guid := named_ref(source, "CPartGuid", "parentGuid"):
            required_part_guids.add(guid)
    pending_parts = list(required_part_guids)
    while pending_parts:
        guid = pending_parts.pop()
        source = part_by_guid.get(guid)
        if source is None:
            raise EyeSubsetError(f"required Part has no source: {guid}")
        parent = named_ref(source, "CPartGuid", "parentGuid")
        if parent and parent not in required_part_guids:
            required_part_guids.add(parent)
            pending_parts.append(parent)
    retained_parts = [
        source
        for source in part_sources
        if _source_guid(source, "CPartGuid") in required_part_guids
    ]

    drawable_set = _list_child(
        _required_child(model, "CDrawableSourceSet", "model has no drawable set"),
        "_sources",
    )
    _set_list_items(
        drawable_set,
        [item for item in drawable_set if xs_attr(item, "ref") in selected_art_ids],
    )

    deformer_ids = {xs_attr(source, "id") for source in retained_deformers}
    deformer_ids.discard(None)
    deformer_set = _list_child(
        _required_child(model, "CDeformerSourceSet", "model has no deformer set"),
        "_sources",
    )
    _set_list_items(
        deformer_set,
        [item for item in deformer_set if xs_attr(item, "ref") in deformer_ids],
    )

    affecter_set = _list_child(
        _required_child(model, "CAffecterSourceSet", "model has no affecter set"),
        "_sources",
    )
    _set_list_items(affecter_set, [])

    part_ids = {xs_attr(source, "id") for source in retained_parts}
    part_ids.discard(None)
    part_set = _list_child(
        _required_child(model, "CPartSourceSet", "model has no Part set"),
        "_sources",
    )
    _set_list_items(
        part_set,
        [item for item in part_set if xs_attr(item, "ref") in part_ids],
    )

    for part in retained_parts:
        _filter_part_children(
            part,
            required_part_guids,
            required_deformer_guids,
            selected_drawable_guids,
        )

    _filter_parameter_groups(model, definitions, {"Eye", "Eyeball"})
    _clear_non_eye_behaviors(model, eye_parameter_guids)
    semantic_guid_tags = {
        "CParameterGuid",
        "CDrawableGuid",
        "CDeformerGuid",
        "CPartGuid",
        "CAffecterGuid",
    }
    active_semantic_guids = set(eye_parameter_guids)
    for source in [*selected_art_meshes, *retained_deformers, *retained_parts]:
        active_semantic_guids.update(
            xs_attr(item, "ref")
            for item in source.iter()
            if item.tag in semantic_guid_tags and xs_attr(item, "ref")
        )
    compatibility_id_count = _filter_compatibility_id_sets(
        model, active_semantic_guids
    )
    removed_shared_count = _garbage_collect_shared(root)
    _assert_closed_references(root)

    reduced = serialize_xml_document(prefix, root)
    report = {
        "art_mesh_count": len(selected_art_meshes),
        "art_mesh_names": [named_text(source, "localName") for source in selected_art_meshes],
        "parameter_count": len(retained_parameters),
        "parameter_names": [
            next(
                child.text or ""
                for child in source
                if child.tag == "s" and xs_attr(child, "n") == "name"
            )
            for source in retained_parameters
        ],
        "deformer_count": len(retained_deformers),
        "animated_deformer_count": len(animated_deformer_guids),
        "static_deformer_count": len(static_deformer_guids),
        "part_count": len(retained_parts),
        "compatibility_id_count": compatibility_id_count,
        "removed_shared_definition_count": removed_shared_count,
        "original_xml_size": len(xml_bytes),
        "reduced_xml_size": len(reduced),
    }
    return reduced, report


def _clear_entry_bytes(path: Path, entry: cmo3_dump.CaffEntry, key8: int) -> bytes:
    with path.open("rb") as stream:
        stream.seek(entry.start_pos)
        stored = stream.read(entry.file_size)
    if len(stored) != entry.file_size:
        raise EyeSubsetError(f"short read for entry {entry.index}")
    if entry.is_obfuscated:
        return bytes(value ^ key8 for value in stored)
    return stored


def _zip_record_payload(record: bytes) -> tuple[bytes, dict]:
    if len(record) < ZIP_LOCAL.size:
        raise EyeSubsetError("main.xml ZIP record is truncated")
    fields = ZIP_LOCAL.unpack_from(record)
    (
        signature,
        version,
        flags,
        method,
        mod_time,
        mod_date,
        header_crc,
        header_compressed_size,
        header_uncompressed_size,
        name_length,
        extra_length,
    ) = fields
    if signature != b"PK\x03\x04" or method != 8:
        raise EyeSubsetError("main.xml is not a raw-DEFLATE ZIP local record")
    data_start = ZIP_LOCAL.size + name_length + extra_length
    if data_start > len(record):
        raise EyeSubsetError("main.xml ZIP name/extra fields are truncated")
    descriptor_signature = False
    descriptor_length = 0
    crc = header_crc
    compressed_size = header_compressed_size
    uncompressed_size = header_uncompressed_size
    if flags & 0x0008:
        if len(record) < data_start + 12:
            raise EyeSubsetError("main.xml ZIP descriptor is truncated")
        descriptor_signature = record[-16:-12] == b"PK\x07\x08"
        descriptor_length = 16 if descriptor_signature else 12
        offset = len(record) - descriptor_length + (4 if descriptor_signature else 0)
        crc, compressed_size, uncompressed_size = struct.unpack_from("<3I", record, offset)
    data_end = data_start + compressed_size
    if data_end + descriptor_length != len(record):
        raise EyeSubsetError("main.xml ZIP record has an unexpected trailing layout")
    try:
        payload = zlib.decompress(record[data_start:data_end], wbits=-15)
    except zlib.error as exc:
        raise EyeSubsetError(f"cannot inflate main.xml: {exc}") from exc
    if len(payload) != uncompressed_size:
        raise EyeSubsetError("main.xml uncompressed size does not match descriptor")
    if (binascii.crc32(payload) & 0xFFFFFFFF) != crc:
        raise EyeSubsetError("main.xml CRC-32 does not match descriptor")
    metadata = {
        "version": version,
        "flags": flags,
        "method": method,
        "mod_time": mod_time,
        "mod_date": mod_date,
        "name": record[ZIP_LOCAL.size : ZIP_LOCAL.size + name_length],
        "extra": record[
            ZIP_LOCAL.size + name_length : ZIP_LOCAL.size + name_length + extra_length
        ],
        "descriptor_signature": descriptor_signature,
    }
    return payload, metadata


def _build_zip_record(payload: bytes, metadata: dict) -> bytes:
    compressor = zlib.compressobj(level=1, method=zlib.DEFLATED, wbits=-15)
    compressed = compressor.compress(payload) + compressor.flush()
    crc = binascii.crc32(payload) & 0xFFFFFFFF
    flags = int(metadata["flags"])
    uses_descriptor = bool(flags & 0x0008)
    header = ZIP_LOCAL.pack(
        b"PK\x03\x04",
        int(metadata["version"]),
        flags,
        8,
        int(metadata["mod_time"]),
        int(metadata["mod_date"]),
        0 if uses_descriptor else crc,
        0 if uses_descriptor else len(compressed),
        0 if uses_descriptor else len(payload),
        len(metadata["name"]),
        len(metadata["extra"]),
    )
    descriptor = b""
    if uses_descriptor:
        if metadata["descriptor_signature"]:
            descriptor += b"PK\x07\x08"
        descriptor += struct.pack("<3I", crc, len(compressed), len(payload))
    return header + metadata["name"] + metadata["extra"] + compressed + descriptor


def extract_main_xml(input_path: Path) -> bytes:
    input_path = Path(input_path).resolve()
    header, entries, _ = cmo3_dump.parse_caff(input_path, 1_000_000)
    candidates = [entry for entry in entries if entry.file_path.replace("\\", "/").endswith("main.xml")]
    if len(candidates) != 1:
        raise EyeSubsetError(f"expected exactly one main.xml entry, got {len(candidates)}")
    entry = candidates[0]
    clear = _clear_entry_bytes(input_path, entry, header.obfuscation_key_signed & 0xFF)
    if entry.compression_option in (0x21, 0x25):
        payload, _ = _zip_record_payload(clear)
        return payload
    if entry.compression_option == 0x10:
        return clear
    raise EyeSubsetError(
        f"unsupported main.xml compression option 0x{entry.compression_option:02X}"
    )


def _encode_beb128(value: int) -> bytes:
    if value < 0:
        raise EyeSubsetError("cannot encode a negative length")
    groups = [value & 0x7F]
    value >>= 7
    while value:
        groups.append(value & 0x7F)
        value >>= 7
    groups.reverse()
    return bytes(group | (0x80 if index + 1 < len(groups) else 0) for index, group in enumerate(groups))


def _xor(data: bytes, key8: int) -> bytes:
    return bytes(value ^ key8 for value in data)


def _encode_toc_entry(
    entry: cmo3_dump.CaffEntry,
    start_pos: int,
    file_size: int,
    key_signed: int,
) -> bytes:
    key8 = key_signed & 0xFF
    key32 = key_signed & 0xFFFFFFFF
    key64 = cmo3_dump.xor_u64_mask(key_signed)
    path_raw = bytes.fromhex(entry.file_path_bytes_hex)
    tag_raw = bytes.fromhex(entry.tag_bytes_hex)
    result = bytearray()
    result += _xor(_encode_beb128(len(path_raw)), key8)
    result += _xor(path_raw, key8)
    result += _xor(_encode_beb128(len(tag_raw)), key8)
    result += _xor(tag_raw, key8)
    result += struct.pack(">Q", start_pos ^ key64)
    result += struct.pack(">I", file_size ^ key32)
    result += bytes([entry.is_obfuscated_value ^ key8])
    result += bytes([entry.compression_option ^ key8])
    result += bytes.fromhex(entry.unused0_hex)
    return bytes(result)


def repack_cmo3(input_path: Path, output_path: Path, replacement_xml: bytes) -> dict:
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    if output_path == input_path:
        raise EyeSubsetError("refusing to overwrite the input CMO3")
    if output_path.exists():
        raise EyeSubsetError(f"output already exists: {output_path}")
    header, entries, source_size = cmo3_dump.parse_caff(input_path, 1_000_000)
    if header.preview.file_size:
        raise EyeSubsetError("archives with embedded CAFF previews are not supported")
    main_entries = [entry for entry in entries if entry.file_path.replace("\\", "/").endswith("main.xml")]
    if len(main_entries) != 1:
        raise EyeSubsetError(f"expected exactly one main.xml entry, got {len(main_entries)}")
    main_entry = main_entries[0]
    key8 = header.obfuscation_key_signed & 0xFF

    original_main_clear = _clear_entry_bytes(input_path, main_entry, key8)
    if main_entry.compression_option in (0x21, 0x25):
        original_xml, zip_metadata = _zip_record_payload(original_main_clear)
    elif main_entry.compression_option == 0x10:
        original_xml, zip_metadata = original_main_clear, None
    else:
        raise EyeSubsetError("unsupported main.xml compression option")
    use_original = replacement_xml == original_xml
    if use_original:
        replacement_stored = None
    else:
        clear_record = (
            _build_zip_record(replacement_xml, zip_metadata)
            if zip_metadata is not None
            else replacement_xml
        )
        replacement_stored = _xor(clear_record, key8) if main_entry.is_obfuscated else clear_record

    with input_path.open("rb") as source:
        source_prefix = source.read(0x36)
        source.seek(source_size - 2)
        guard = source.read(2)
    if len(source_prefix) != 0x36 or guard != b"bc":
        raise EyeSubsetError("input CAFF header or guard is malformed")

    payload_sizes = [
        len(replacement_stored) if entry is main_entry and replacement_stored is not None else entry.file_size
        for entry in entries
    ]
    toc_lengths = [
        len(_encode_toc_entry(entry, 0, payload_sizes[index], header.obfuscation_key_signed))
        for index, entry in enumerate(entries)
    ]
    index_end = 0x3A + sum(toc_lengths)
    starts: list[int] = []
    cursor = index_end
    for size in payload_sizes:
        starts.append(cursor)
        cursor += size

    toc = b"".join(
        _encode_toc_entry(entry, starts[index], payload_sizes[index], header.obfuscation_key_signed)
        for index, entry in enumerate(entries)
    )
    encoded_count = struct.pack(">I", len(entries) ^ (header.obfuscation_key_signed & 0xFFFFFFFF))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as target, input_path.open("rb") as source:
            temporary_path = Path(target.name)
            target.write(source_prefix)
            target.write(encoded_count)
            target.write(toc)
            for entry in entries:
                if entry is main_entry and replacement_stored is not None:
                    target.write(replacement_stored)
                else:
                    source.seek(entry.start_pos)
                    remaining = entry.file_size
                    while remaining:
                        chunk = source.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise EyeSubsetError(
                                f"short payload read for entry {entry.index}"
                            )
                        target.write(chunk)
                        remaining -= len(chunk)
            target.write(guard)
            target.flush()
            os.fsync(target.fileno())

        verify_header, verify_entries, verify_size = cmo3_dump.parse_caff(
            temporary_path, 1_000_000
        )
        range_errors, intervals = cmo3_dump.validate_entry_ranges(
            verify_header, verify_entries, verify_size
        )
        gaps, overlaps, covered = cmo3_dump.find_gaps_and_overlaps(
            intervals, verify_size
        )
        if range_errors or gaps or overlaps or covered != verify_size:
            raise EyeSubsetError(
                "temporary archive failed CAFF range/coverage validation"
            )
        if extract_main_xml(temporary_path) != replacement_xml:
            raise EyeSubsetError(
                "temporary archive main.xml does not match replacement bytes"
            )
        if output_path.exists():
            raise EyeSubsetError(f"output appeared while packing: {output_path}")
        temporary_path.rename(output_path)
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return {
        "source": str(input_path),
        "output": str(output_path),
        "entry_count": len(entries),
        "used_original_main_record": use_original,
        "original_main_xml_size": len(original_xml),
        "replacement_main_xml_size": len(replacement_xml),
        "output_size": output_path.stat().st_size,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an eye-only Cubism 5 CMO3 without launching Cubism Editor."
    )
    parser.add_argument("input", type=Path, help="source .cmo3")
    parser.add_argument("output", type=Path, help="new eye-only .cmo3")
    parser.add_argument("--report", type=Path, help="write a JSON reduction report")
    parser.add_argument(
        "--eye-part-name",
        action="append",
        dest="eye_part_names",
        help="Part localName to retain; repeatable (default: Eye and Eyeball)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {PROGRAM_VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not input_path.is_file():
        print(f"error: input is not a file: {input_path}", file=sys.stderr)
        return 2
    try:
        report_path = args.report.expanduser().resolve() if args.report else None
        if output_path.exists():
            raise EyeSubsetError(f"output already exists: {output_path}")
        if report_path is not None and report_path.exists():
            raise EyeSubsetError(f"report already exists: {report_path}")
        original_xml = extract_main_xml(input_path)
        reduced_xml, reduction_report = reduce_to_eye_model(
            original_xml,
            eye_part_names=args.eye_part_names or DEFAULT_EYE_PART_NAMES,
        )
        archive_report = repack_cmo3(input_path, output_path, reduced_xml)
        report = {
            "tool": {"name": "cmo3_eye_subset.py", "version": PROGRAM_VERSION},
            "reduction": reduction_report,
            "archive": archive_report,
        }
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with report_path.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (EyeSubsetError, cmo3_dump.CaffError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
