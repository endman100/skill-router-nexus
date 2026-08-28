#!/usr/bin/env python3
"""Compile a flat layered PSD into a static editable Cubism CMO3 project.

The compiler never launches Cubism Editor.  It reuses the serializer/container
metadata of a verified Cubism 5.3 CMO3, replaces a bounded set of ArtMesh
sources with root-level quads, packs PSD layers into one atlas, and rebuilds the
CAFF archive through the toolkit's validated packer.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from PIL import Image
from psd_tools import PSDImage

import cmo3_dump
import cmo3_eye_subset
import cmo3_pack


PROGRAM_VERSION = "0.1.0"
DEFAULT_ATLAS_SIZE = 2048
DEFAULT_PADDING = 2


class CompileError(Exception):
    """The PSD cannot be compiled safely with the supplied template."""


@dataclass
class LayerAsset:
    name: str
    image: Image.Image
    canvas_bbox: tuple[int, int, int, int]
    draw_order: int
    atlas_bbox: tuple[int, int, int, int] | None = None


@dataclass
class Slot:
    source_id: str
    source: ET.Element
    texture_extension_id: str
    texture_extension: ET.Element
    atlas_region: ET.Element
    drawable_guid_ref: str


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return cmo3_dump.sha256_file(path)


def direct_named(parent: ET.Element, tag: str, name: str) -> ET.Element:
    for child in parent:
        if child.tag == tag and child.attrib.get("xs.n") == name:
            return child
    raise CompileError(f"{parent.tag}: missing direct {tag} xs.n={name!r}")


def descendant_named(parent: ET.Element, tag: str, name: str) -> ET.Element:
    for child in parent.iter(tag):
        if child.attrib.get("xs.n") == name:
            return child
    raise CompileError(f"{parent.tag}: missing {tag} xs.n={name!r}")


def optional_direct_named(
    parent: ET.Element, tag: str, name: str
) -> ET.Element | None:
    for child in parent:
        if child.tag == tag and child.attrib.get("xs.n") == name:
            return child
    return None


def replace_child(parent: ET.Element, old: ET.Element, new: ET.Element) -> None:
    index = list(parent).index(old)
    parent.remove(old)
    parent.insert(index, new)


def set_list_items(container: ET.Element, items: Iterable[ET.Element]) -> None:
    values = list(items)
    container[:] = values
    container.set("count", str(len(values)))


def set_number_array(element: ET.Element, values: Iterable[int | float]) -> None:
    materialized = list(values)
    element.set("count", str(len(materialized)))
    element.text = " ".join(format_number(value) for value in materialized)


def format_number(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    rounded = round(float(value), 10)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.10g}"


def load_psd_layers(psd_path: Path) -> tuple[tuple[int, int], list[LayerAsset]]:
    psd = PSDImage.open(psd_path)
    layers: list[LayerAsset] = []
    for layer in psd:
        if not layer.visible:
            continue
        if layer.is_group():
            raise CompileError(
                f"top-level groups are not supported by the direct compiler: {layer.name!r}"
            )
        image = layer.composite(force=True)
        if image is None:
            continue
        image = image.convert("RGBA")
        alpha_bounds = image.getchannel("A").getbbox()
        if alpha_bounds is None:
            continue
        left, top, right, bottom = map(int, layer.bbox)
        ax1, ay1, ax2, ay2 = alpha_bounds
        cropped = image.crop(alpha_bounds)
        canvas_bbox = (left + ax1, top + ay1, left + ax2, top + ay2)
        layers.append(
            LayerAsset(
                name=layer.name,
                image=cropped,
                canvas_bbox=canvas_bbox,
                draw_order=500 + len(layers),
            )
        )
    if not layers:
        raise CompileError("PSD has no visible, non-empty top-level pixel layers")
    return (int(psd.width), int(psd.height)), layers


def pack_atlas(
    layers: list[LayerAsset],
    atlas_size: int = DEFAULT_ATLAS_SIZE,
    padding: int = DEFAULT_PADDING,
) -> Image.Image:
    if atlas_size <= 0 or padding < 0:
        raise CompileError("atlas size must be positive and padding non-negative")
    order = sorted(
        range(len(layers)),
        key=lambda index: (
            -layers[index].image.height,
            -layers[index].image.width,
            index,
        ),
    )
    cursor_x = padding
    cursor_y = padding
    row_height = 0
    for index in order:
        layer = layers[index]
        width, height = layer.image.size
        if width + padding * 2 > atlas_size or height + padding * 2 > atlas_size:
            raise CompileError(
                f"layer {layer.name!r} ({width}x{height}) exceeds "
                f"{atlas_size}x{atlas_size} atlas"
            )
        if cursor_x + width + padding > atlas_size:
            cursor_x = padding
            cursor_y += row_height + padding
            row_height = 0
        if cursor_y + height + padding > atlas_size:
            raise CompileError(
                f"{len(layers)} layer rectangles do not fit in a "
                f"{atlas_size}x{atlas_size} atlas"
            )
        layer.atlas_bbox = (
            cursor_x,
            cursor_y,
            cursor_x + width,
            cursor_y + height,
        )
        cursor_x += width + padding
        row_height = max(row_height, height)

    atlas = Image.new("RGBA", (atlas_size, atlas_size), (0, 0, 0, 0))
    for layer in layers:
        if layer.atlas_bbox is None:
            raise AssertionError("atlas placement was not assigned")
        atlas.alpha_composite(layer.image, layer.atlas_bbox[:2])
    return atlas


def png_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=6)
    return output.getvalue()


def split_xml_document(xml_bytes: bytes) -> tuple[bytes, ET.Element]:
    marker = xml_bytes.find(b"<root")
    if marker < 0:
        raise CompileError("main.xml has no <root> element")
    try:
        root = ET.fromstring(xml_bytes[marker:])
    except ET.ParseError as exc:
        raise CompileError(f"main.xml cannot be parsed: {exc}") from exc
    return xml_bytes[:marker], root


def shared_definitions(root: ET.Element) -> tuple[ET.Element, dict[str, ET.Element]]:
    shared = root.find("shared")
    if shared is None:
        raise CompileError("main.xml has no <shared> table")
    definitions: dict[str, ET.Element] = {}
    for child in shared:
        identity = child.attrib.get("xs.id")
        if identity:
            if identity in definitions:
                raise CompileError(f"duplicate shared identity: {identity}")
            definitions[identity] = child
    return shared, definitions


def model_source(root: ET.Element) -> ET.Element:
    model = root.find("./main/CModelSource")
    if model is None:
        raise CompileError("main.xml has no main/CModelSource")
    return model


def source_set_list(model: ET.Element, set_tag: str) -> ET.Element:
    source_set = model.find(set_tag)
    if source_set is None:
        raise CompileError(f"model has no {set_tag}")
    return direct_named(source_set, "carray_list", "_sources")


def discover_atlas(
    model: ET.Element,
    definitions: dict[str, ET.Element],
) -> tuple[str, ET.Element, str, ET.Element, str, ET.Element, str]:
    drawable_list = source_set_list(model, "CDrawableSourceSet")
    texture_counts: collections.Counter[str] = collections.Counter()
    for reference in drawable_list:
        source = definitions.get(reference.attrib.get("xs.ref", ""))
        if source is None or source.tag != "CArtMeshSource":
            continue
        texture = optional_direct_named(source, "GTexture2D", "texture")
        state = optional_direct_named(source, "TextureState", "textureState")
        if (
            texture is not None
            and state is not None
            and state.attrib.get("v") == "TEXTURE_ATLAS"
            and texture.attrib.get("xs.ref")
        ):
            texture_counts[texture.attrib["xs.ref"]] += 1
    if not texture_counts:
        raise CompileError("template has no active texture-atlas ArtMesh")
    texture_ref, _ = texture_counts.most_common(1)[0]
    texture = definitions.get(texture_ref)
    if texture is None or texture.tag != "GTexture2D":
        raise CompileError(f"texture reference does not resolve: {texture_ref}")
    image_ref = direct_named(
        texture, "CImageResource", "srcImageResource"
    ).attrib.get("xs.ref")
    if not image_ref or image_ref not in definitions:
        raise CompileError("atlas texture image resource does not resolve")
    image_resource = definitions[image_ref]
    image_path = direct_named(image_resource, "file", "imageFileBuf").attrib.get(
        "path"
    )
    if not image_path:
        raise CompileError("atlas image resource has no CAFF path")

    atlas_ref = ""
    atlas: ET.Element | None = None
    atlas_guid_ref = ""
    for identity, candidate in definitions.items():
        if candidate.tag != "CTextureAtlas":
            continue
        cached = optional_direct_named(
            candidate, "CImageResource", "cachedAtlasImage"
        )
        if cached is not None and cached.attrib.get("xs.ref") == image_ref:
            atlas_ref = identity
            atlas = candidate
            guid = direct_named(candidate, "CTextureAtlasGuid", "guid")
            atlas_guid_ref = guid.attrib.get("xs.ref", "")
            break
    if atlas is None or not atlas_ref or not atlas_guid_ref:
        raise CompileError("cannot locate the active CTextureAtlas metadata")
    return (
        texture_ref,
        texture,
        image_ref,
        image_resource,
        atlas_ref,
        atlas,
        atlas_guid_ref,
    )


def resolve_slot(
    source_id: str,
    source: ET.Element,
    definitions: dict[str, ET.Element],
    texture_ref: str,
    atlas_guid_ref: str,
) -> Slot | None:
    texture = optional_direct_named(source, "GTexture2D", "texture")
    if texture is None or texture.attrib.get("xs.ref") != texture_ref:
        return None
    try:
        ac_drawable = direct_named(source, "ACDrawableSource", "super")
        ac_parameter = direct_named(
            ac_drawable, "ACParameterControllableSource", "super"
        )
        extensions = direct_named(ac_parameter, "carray_list", "_extensions")
        extension_ref_node = next(
            child
            for child in extensions
            if child.tag == "CTextureInputExtension" and child.attrib.get("xs.ref")
        )
        extension_id = extension_ref_node.attrib["xs.ref"]
        extension = definitions[extension_id]
        current = next(
            child
            for child in extension
            if child.attrib.get("xs.n") == "currentTextureInputData"
            and child.tag == "CTextureInput_TextureAtlasRegion"
            and child.attrib.get("xs.ref")
        )
        region = definitions[current.attrib["xs.ref"]]
        region_guid = direct_named(
            region, "CTextureAtlasGuid", "textureAtlasGuid"
        ).attrib.get("xs.ref")
        if region_guid != atlas_guid_ref:
            return None
        keyforms = direct_named(source, "carray_list", "keyforms")
        if not len(keyforms):
            return None
        descendant_named(source, "GEditableMesh2", "editableMesh")
        drawable_guid_ref = direct_named(
            ac_drawable, "CDrawableGuid", "guid"
        ).attrib["xs.ref"]
        if drawable_guid_ref not in definitions:
            return None
        direct_named(source, "float-array", "positions")
        direct_named(source, "float-array", "uvs")
        direct_named(source, "int-array", "indices")
    except (CompileError, KeyError, StopIteration):
        return None
    return Slot(
        source_id=source_id,
        source=source,
        texture_extension_id=extension_id,
        texture_extension=extension,
        atlas_region=region,
        drawable_guid_ref=drawable_guid_ref,
    )


def choose_slots(
    model: ET.Element,
    definitions: dict[str, ET.Element],
    count: int,
    texture_ref: str,
    atlas_guid_ref: str,
) -> list[Slot]:
    drawable_list = source_set_list(model, "CDrawableSourceSet")
    candidates: list[tuple[int, int, int, Slot]] = []
    for source_order, reference in enumerate(drawable_list):
        source_id = reference.attrib.get("xs.ref", "")
        source = definitions.get(source_id)
        if source is None or source.tag != "CArtMeshSource":
            continue
        slot = resolve_slot(
            source_id, source, definitions, texture_ref, atlas_guid_ref
        )
        if slot is None:
            continue
        keyform_count = len(direct_named(source, "carray_list", "keyforms"))
        vertex_count = int(direct_named(source, "float-array", "positions").attrib[
            "count"
        ]) // 2
        candidates.append((keyform_count, vertex_count, source_order, slot))
    candidates.sort(key=lambda item: item[:3])
    if len(candidates) < count:
        raise CompileError(
            f"template provides {len(candidates)} reusable atlas ArtMeshes; "
            f"PSD needs {count}"
        )
    return [item[3] for item in candidates[:count]]


def make_coord_type(name: str = "Canvas") -> ET.Element:
    coordinate = ET.Element("CoordType", {"xs.n": "coordType"})
    label = ET.SubElement(coordinate, "s", {"xs.n": "coordName"})
    label.text = name
    return coordinate


def make_keyform_grid(form_guid_ref: str) -> ET.Element:
    grid = ET.Element("KeyformGridSource", {"xs.n": "keyformGridSource"})
    on_grid = ET.SubElement(
        grid, "array_list", {"xs.n": "keyformsOnGrid", "count": "1"}
    )
    keyform = ET.SubElement(on_grid, "KeyformOnGrid")
    access = ET.SubElement(keyform, "KeyformGridAccessKey", {"xs.n": "accessKey"})
    ET.SubElement(
        access, "array_list", {"xs.n": "_keyOnParameterList", "count": "0"}
    )
    ET.SubElement(
        keyform, "CFormGuid", {"xs.n": "keyformGuid", "xs.ref": form_guid_ref}
    )
    ET.SubElement(
        grid, "array_list", {"xs.n": "keyformBindings", "count": "0"}
    )
    return grid


def set_affine(element: ET.Element, tx: float = 0.0, ty: float = 0.0) -> None:
    element.attrib.update(
        {
            "m00": "1.0",
            "m01": "0.0",
            "m02": format_number(tx),
            "m10": "0.0",
            "m11": "1.0",
            "m12": format_number(ty),
        }
    )


def part_bucket(layer_name: str) -> str:
    name = layer_name.split("|", 1)[0].strip().lower()
    if name == "back hair":
        return "Back Hair"
    if name == "front hair":
        return "Front Hair"
    if name.startswith("ears"):
        return "Ear"
    if name.startswith("irides"):
        return "Eyeball"
    if name.startswith("eyewhite") or name.startswith("eyelash"):
        return "Eye"
    if name.startswith("eyebrow"):
        return "Brow"
    if name == "neck":
        return "Neck"
    if name == "face":
        return "Face"
    if name == "nose":
        return "Nose"
    if name == "mouth":
        return "Mouth"
    return "Body"


def prepare_parts(
    model: ET.Element, definitions: dict[str, ET.Element]
) -> tuple[dict[str, tuple[ET.Element, str]], dict[str, ET.Element]]:
    part_list = source_set_list(model, "CPartSourceSet")
    by_name: dict[str, tuple[ET.Element, str]] = {}
    child_lists: dict[str, ET.Element] = {}
    for reference in part_list:
        source = definitions.get(reference.attrib.get("xs.ref", ""))
        if source is None or source.tag != "CPartSource":
            continue
        ac_parameter = direct_named(
            source, "ACParameterControllableSource", "super"
        )
        local_name = direct_named(ac_parameter, "s", "localName").text or ""
        guid_ref = direct_named(source, "CPartGuid", "guid").attrib.get("xs.ref")
        children = direct_named(source, "carray_list", "_childGuids")
        retained_parts = [child for child in children if child.tag == "CPartGuid"]
        set_list_items(children, retained_parts)
        if guid_ref:
            by_name[local_name] = (source, guid_ref)
            child_lists[guid_ref] = children
    required = {
        "Back Hair",
        "Front Hair",
        "Ear",
        "Eyeball",
        "Eye",
        "Brow",
        "Neck",
        "Face",
        "Nose",
        "Mouth",
        "Body",
    }
    missing = sorted(required - set(by_name))
    if missing:
        raise CompileError(f"template lacks required Parts: {missing}")
    return by_name, child_lists


def rewrite_slot(
    slot: Slot,
    layer: LayerAsset,
    definitions: dict[str, ET.Element],
    part_guid_ref: str,
    part_children: ET.Element,
    texture_ref: str,
    atlas_guid_ref: str,
    atlas_size: int,
    root_uuid: str,
    slot_index: int,
) -> None:
    if layer.atlas_bbox is None:
        raise CompileError(f"layer has no atlas placement: {layer.name}")
    source = slot.source
    ac_drawable = direct_named(source, "ACDrawableSource", "super")
    ac_parameter = direct_named(
        ac_drawable, "ACParameterControllableSource", "super"
    )
    direct_named(ac_parameter, "s", "localName").text = layer.name
    direct_named(ac_parameter, "b", "isVisible").text = "true"
    direct_named(ac_parameter, "b", "isLocked").text = "false"
    parent_guid = direct_named(ac_parameter, "CPartGuid", "parentGuid")
    parent_guid.attrib.clear()
    parent_guid.attrib.update({"xs.n": "parentGuid", "xs.ref": part_guid_ref})

    drawable_id = direct_named(ac_drawable, "CDrawableId", "id")
    drawable_id.set("idstr", f"ArtMesh{slot_index + 1:03d}")
    drawable_guid = definitions[slot.drawable_guid_ref]
    drawable_guid.set("note", f"ArtMesh{slot_index + 1:03d}")
    part_children.append(
        ET.Element("CDrawableGuid", {"xs.ref": slot.drawable_guid_ref})
    )
    part_children.set("count", str(len(part_children)))

    target = direct_named(ac_drawable, "CDeformerGuid", "targetDeformerGuid")
    target.attrib.clear()
    target.attrib.update(
        {
            "xs.n": "targetDeformerGuid",
            "uuid": root_uuid,
            "note": "ROOT",
        }
    )
    clipping = direct_named(ac_drawable, "carray_list", "clipGuidList")
    set_list_items(clipping, [])
    direct_named(ac_drawable, "b", "invertClippingMask").text = "false"
    # Keep each template slot's existing 16/32 px icon metadata and payload.
    # Re-pointing icons by filename alone is unsafe because CAFF image names do
    # not encode dimensions.

    keyforms = direct_named(source, "carray_list", "keyforms")
    first_form = keyforms[0]
    set_list_items(keyforms, [first_form])
    form_guid = descendant_named(first_form, "CFormGuid", "guid")
    form_guid_ref = form_guid.attrib.get("xs.ref")
    if not form_guid_ref:
        raise CompileError(f"{layer.name}: first ArtMesh form has no shared GUID")
    form_source = descendant_named(first_form, "CArtMeshSource", "_source")
    form_source.set("xs.ref", slot.source_id)
    grid = direct_named(ac_parameter, "KeyformGridSource", "keyformGridSource")
    replace_child(ac_parameter, grid, make_keyform_grid(form_guid_ref))

    drawable_form = direct_named(first_form, "ACDrawableForm", "super")
    draw_order = direct_named(drawable_form, "i", "drawOrder")
    draw_order.text = str(layer.draw_order)
    direct_named(drawable_form, "f", "opacity").text = "1.0"
    coord = direct_named(drawable_form, "CoordType", "coordType")
    replace_child(drawable_form, coord, make_coord_type())

    x1, y1, x2, y2 = layer.canvas_bbox
    positions = [x2, y1, x1, y1, x2, y2, x1, y2]
    ax1, ay1, ax2, ay2 = layer.atlas_bbox
    uvs = [
        ax2 / atlas_size,
        ay1 / atlas_size,
        ax1 / atlas_size,
        ay1 / atlas_size,
        ax2 / atlas_size,
        ay2 / atlas_size,
        ax1 / atlas_size,
        ay2 / atlas_size,
    ]
    indices = [1, 0, 2, 1, 2, 3]
    set_number_array(direct_named(source, "int-array", "indices"), indices)
    set_number_array(direct_named(source, "float-array", "positions"), positions)
    set_number_array(direct_named(source, "float-array", "uvs"), uvs)
    set_number_array(descendant_named(first_form, "float-array", "positions"), positions)

    editable = descendant_named(source, "GEditableMesh2", "editableMesh")
    editable.set("nextPointUid", "4")
    editable.set("useDelaunayTriangulation", "true")
    set_number_array(direct_named(editable, "float-array", "point"), positions)
    set_number_array(
        direct_named(editable, "byte-array", "pointPriority"), [20] * 4
    )
    set_number_array(
        direct_named(editable, "short-array", "edge"),
        [0, 1, 0, 2, 1, 3, 2, 3, 1, 2],
    )
    set_number_array(
        direct_named(editable, "byte-array", "edgePriority"), [30, 30, 30, 30, 10]
    )
    set_number_array(
        direct_named(editable, "int-array", "pointUid"), [0, 1, 2, 3]
    )
    editable_coord = direct_named(editable, "CoordType", "coordType")
    replace_child(editable, editable_coord, make_coord_type())

    texture = direct_named(source, "GTexture2D", "texture")
    texture.set("xs.ref", texture_ref)
    direct_named(source, "TextureState", "textureState").set(
        "v", "TEXTURE_ATLAS"
    )
    direct_named(source, "ColorComposition", "colorComposition").set(
        "v", "NORMAL"
    )
    direct_named(source, "b", "culling").text = "false"
    direct_named(source, "AlphaComposition", "alphaComposition").set("v", "OVER")

    extension = slot.texture_extension
    extension_owner = descendant_named(extension, "CArtMeshSource", "_owner")
    extension_owner.set("xs.ref", slot.source_id)
    texture_inputs = direct_named(extension, "carray_list", "_textureInputs")
    region_id = slot.atlas_region.attrib.get("xs.id")
    if not region_id:
        raise CompileError(f"{layer.name}: atlas region is not a shared object")
    set_list_items(
        texture_inputs,
        [ET.Element("CTextureInput_TextureAtlasRegion", {"xs.ref": region_id})],
    )
    current = next(
        child
        for child in extension
        if child.attrib.get("xs.n") == "currentTextureInputData"
    )
    new_current = ET.Element(
        "CTextureInput_TextureAtlasRegion",
        {"xs.n": "currentTextureInputData", "xs.ref": region_id},
    )
    replace_child(extension, current, new_current)

    region = slot.atlas_region
    region_owner = descendant_named(region, "CTextureInputExtension", "_owner")
    region_owner.set("xs.ref", slot.texture_extension_id)
    region_guid = direct_named(region, "CTextureAtlasGuid", "textureAtlasGuid")
    region_guid.set("xs.ref", atlas_guid_ref)
    optional_transform = descendant_named(
        region, "CAffine", "optionalTransformOnCanvas"
    )
    set_affine(optional_transform)
    input_transform = direct_named(
        region, "CAffine", "inputImageLocalToCanvasTransform"
    )
    set_affine(input_transform, x1, y1)


def discover_root_uuid(
    model: ET.Element, definitions: dict[str, ET.Element]
) -> str:
    for reference in source_set_list(model, "CDrawableSourceSet"):
        source = definitions.get(reference.attrib.get("xs.ref", ""))
        if source is None or source.tag != "CArtMeshSource":
            continue
        try:
            ac_drawable = direct_named(source, "ACDrawableSource", "super")
            target = direct_named(
                ac_drawable, "CDeformerGuid", "targetDeformerGuid"
            )
        except CompileError:
            continue
        if target.attrib.get("note") == "ROOT" and target.attrib.get("uuid"):
            return target.attrib["uuid"]
    return "71fae776-e218-4aee-873e-78e8ac0cb48a"


def update_canvas(model: ET.Element, width: int, height: int) -> None:
    canvas = model.find("CImageCanvas")
    if canvas is None:
        raise CompileError("model has no CImageCanvas")
    direct_named(canvas, "i", "pixelWidth").text = str(width)
    direct_named(canvas, "i", "pixelHeight").text = str(height)


def update_texture_manager(model: ET.Element, atlas_ref: str) -> None:
    manager = model.find("CTextureManager")
    if manager is None:
        raise CompileError("model has no CTextureManager")
    texture_list = direct_named(manager, "TextureImageGroup", "textureList")
    set_list_items(direct_named(texture_list, "carray_list", "children"), [])
    set_list_items(direct_named(manager, "carray_list", "_rawImages"), [])
    set_list_items(direct_named(manager, "carray_list", "_modelImageGroups"), [])
    set_list_items(
        direct_named(manager, "carray_list", "_textureAtlases"),
        [ET.Element("CTextureAtlas", {"xs.ref": atlas_ref})],
    )
    direct_named(manager, "b", "isTextureInputModelImageMode").text = "false"


def update_atlas_metadata(
    atlas: ET.Element,
    image_resource: ET.Element,
    atlas_size: int,
    atlas_png_size: int,
) -> None:
    image_resource.set("width", str(atlas_size))
    image_resource.set("height", str(atlas_size))
    image_resource.set("type", "INT_ARGB")
    image_resource.set("imageFileBuf_size", str(atlas_png_size))
    image_resource.set("previewFileBuf_size", "0")
    optional_name = optional_direct_named(atlas, "s", "name")
    if optional_name is not None:
        optional_name.text = "codex_direct_atlas"
    direct_named(atlas, "i", "width").text = str(atlas_size)
    direct_named(atlas, "i", "height").text = str(atlas_size)
    model_images = direct_named(atlas, "carray_list", "modelImages")
    set_list_items(model_images, [])
    for size in atlas.iter("CSize"):
        if size.attrib.get("xs.n") == "rawImageSize":
            size.set("width", str(atlas_size))
            size.set("height", str(atlas_size))


def assert_closed_references(
    root: ET.Element, definitions: dict[str, ET.Element]
) -> list[str]:
    missing = sorted(
        {
            reference
            for element in root.iter()
            if (reference := element.attrib.get("xs.ref"))
            and reference != "ROOT"
            and reference not in definitions
        }
    )
    return missing


def validate_modified_xml(
    root: ET.Element,
    expected_layers: int,
) -> dict:
    _, definitions = shared_definitions(root)
    model = model_source(root)
    active = source_set_list(model, "CDrawableSourceSet")
    active_sources = [definitions[item.attrib["xs.ref"]] for item in active]
    art_meshes = [source for source in active_sources if source.tag == "CArtMeshSource"]
    root_count = 0
    quad_count = 0
    names: list[str] = []
    for source in art_meshes:
        ac_drawable = direct_named(source, "ACDrawableSource", "super")
        ac_parameter = direct_named(
            ac_drawable, "ACParameterControllableSource", "super"
        )
        names.append(direct_named(ac_parameter, "s", "localName").text or "")
        target = direct_named(
            ac_drawable, "CDeformerGuid", "targetDeformerGuid"
        )
        if target.attrib.get("note") == "ROOT":
            root_count += 1
        positions = direct_named(source, "float-array", "positions")
        uvs = direct_named(source, "float-array", "uvs")
        indices = direct_named(source, "int-array", "indices")
        keyforms = direct_named(source, "carray_list", "keyforms")
        if (
            int(positions.attrib.get("count", "-1")) == 8
            and int(uvs.attrib.get("count", "-1")) == 8
            and (indices.text or "").split() == ["1", "0", "2", "1", "2", "3"]
            and len(keyforms) == 1
        ):
            quad_count += 1
    missing = assert_closed_references(root, definitions)
    if len(active) != expected_layers:
        raise CompileError(
            f"modified XML has {len(active)} active drawables, expected {expected_layers}"
        )
    if len(art_meshes) != expected_layers:
        raise CompileError("not every active drawable is an ArtMesh")
    if root_count != expected_layers or quad_count != expected_layers:
        raise CompileError("modified ArtMesh root/quad validation failed")
    if missing:
        raise CompileError(f"modified XML has dangling shared refs: {missing[:10]}")
    return {
        "active_art_mesh_count": len(art_meshes),
        "root_deformer_count": root_count,
        "quad_mesh_count": quad_count,
        "dangling_reference_count": len(missing),
        "active_names": names,
    }


def build_main_xml(
    template_xml: bytes,
    layers: list[LayerAsset],
    canvas_size: tuple[int, int],
    atlas_size: int,
    atlas_png_size: int,
) -> tuple[bytes, str, dict]:
    prefix, root = split_xml_document(template_xml)
    _, definitions = shared_definitions(root)
    model = model_source(root)
    (
        texture_ref,
        _texture,
        _image_ref,
        image_resource,
        atlas_ref,
        atlas,
        atlas_guid_ref,
    ) = discover_atlas(model, definitions)
    slots = choose_slots(
        model,
        definitions,
        len(layers),
        texture_ref,
        atlas_guid_ref,
    )
    root_uuid = discover_root_uuid(model, definitions)
    parts, part_children = prepare_parts(model, definitions)

    update_canvas(model, *canvas_size)
    update_texture_manager(model, atlas_ref)
    update_atlas_metadata(atlas, image_resource, atlas_size, atlas_png_size)
    set_list_items(source_set_list(model, "CDeformerSourceSet"), [])
    set_list_items(source_set_list(model, "CAffecterSourceSet"), [])

    active_refs: list[ET.Element] = []
    for index, (slot, layer) in enumerate(zip(slots, layers)):
        bucket = part_bucket(layer.name)
        _, part_guid_ref = parts[bucket]
        rewrite_slot(
            slot=slot,
            layer=layer,
            definitions=definitions,
            part_guid_ref=part_guid_ref,
            part_children=part_children[part_guid_ref],
            texture_ref=texture_ref,
            atlas_guid_ref=atlas_guid_ref,
            atlas_size=atlas_size,
            root_uuid=root_uuid,
            slot_index=index,
        )
        active_refs.append(
            ET.Element("CArtMeshSource", {"xs.ref": slot.source_id})
        )
    set_list_items(source_set_list(model, "CDrawableSourceSet"), active_refs)

    validation = validate_modified_xml(root, len(layers))
    output_xml = prefix + ET.tostring(
        root, encoding="utf-8", short_empty_elements=True
    )
    atlas_path = direct_named(image_resource, "file", "imageFileBuf").attrib[
        "path"
    ]
    return output_xml, atlas_path, validation


def compile_psd(
    template_path: Path,
    psd_path: Path,
    output_path: Path,
    report_path: Path | None = None,
    atlas_size: int = DEFAULT_ATLAS_SIZE,
    padding: int = DEFAULT_PADDING,
) -> dict:
    template_path = Path(template_path).expanduser().resolve()
    psd_path = Path(psd_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    report_path = (
        Path(report_path).expanduser().resolve() if report_path is not None else None
    )
    if not template_path.is_file():
        raise CompileError(f"template is not a file: {template_path}")
    if not psd_path.is_file():
        raise CompileError(f"PSD is not a file: {psd_path}")
    if output_path.exists():
        raise CompileError(f"output already exists: {output_path}")
    if report_path is not None and report_path.exists():
        raise CompileError(f"report already exists: {report_path}")

    canvas_size, layers = load_psd_layers(psd_path)
    atlas = pack_atlas(layers, atlas_size=atlas_size, padding=padding)
    atlas_payload = png_bytes(atlas)
    template_xml = cmo3_eye_subset.extract_main_xml(template_path)
    main_xml, atlas_internal_path, xml_validation = build_main_xml(
        template_xml=template_xml,
        layers=layers,
        canvas_size=canvas_size,
        atlas_size=atlas_size,
        atlas_png_size=len(atlas_payload),
    )
    pack_report = cmo3_pack.repack_entries(
        template_path,
        output_path,
        {
            "main.xml": main_xml,
            atlas_internal_path: atlas_payload,
        },
    )
    verified_xml = cmo3_eye_subset.extract_main_xml(output_path)
    _, verified_root = split_xml_document(verified_xml)
    post_validation = validate_modified_xml(verified_root, len(layers))
    if post_validation != xml_validation:
        raise CompileError("post-pack XML validation differs from pre-pack validation")

    report = {
        "tool": {"name": "cmo3_compile_psd.py", "version": PROGRAM_VERSION},
        "template": str(template_path),
        "template_sha256": sha256_file(template_path),
        "psd": str(psd_path),
        "psd_sha256": sha256_file(psd_path),
        "output": str(output_path),
        "output_sha256": sha256_file(output_path),
        "canvas_size": list(canvas_size),
        "layer_count": len(layers),
        "layers": [
            {
                "index_bottom_to_top": index,
                "name": layer.name,
                "draw_order": layer.draw_order,
                "canvas_bbox": list(layer.canvas_bbox),
                "atlas_bbox": list(layer.atlas_bbox or ()),
                "pixel_size": list(layer.image.size),
            }
            for index, layer in enumerate(layers)
        ],
        "atlas": {
            "archive_path": atlas_internal_path,
            "size": [atlas_size, atlas_size],
            "padding": padding,
            "png_size": len(atlas_payload),
            "sha256": sha256_bytes(atlas_payload),
        },
        "validation": {
            **post_validation,
            "caff_range_errors": pack_report["validation"]["range_errors"],
            "caff_gaps": pack_report["validation"]["gaps"],
            "caff_overlaps": pack_report["validation"]["overlaps"],
            "replacement_byte_matches": pack_report["validation"][
                "replacement_byte_matches"
            ],
        },
        "packer": pack_report,
        "limitations": [
            "Static root-level quad ArtMeshes; no parameter rigging is generated.",
            "Unused template shared definitions are preserved for conservative compatibility.",
        ],
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile a flat layered PSD into a static Cubism 5.3 CMO3 without "
            "launching Cubism Editor."
        )
    )
    parser.add_argument("template", type=Path, help="verified Cubism 5.3 CMO3")
    parser.add_argument("psd", type=Path, help="flat layered PSD")
    parser.add_argument("output", type=Path, help="new .cmo3 output")
    parser.add_argument("--report", type=Path, help="write a new JSON report")
    parser.add_argument(
        "--atlas-size", type=int, default=DEFAULT_ATLAS_SIZE, help="atlas edge"
    )
    parser.add_argument(
        "--padding", type=int, default=DEFAULT_PADDING, help="atlas padding"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {PROGRAM_VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = compile_psd(
            template_path=args.template,
            psd_path=args.psd,
            output_path=args.output,
            report_path=args.report,
            atlas_size=args.atlas_size,
            padding=args.padding,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (CompileError, cmo3_dump.CaffError, cmo3_pack.PackError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
