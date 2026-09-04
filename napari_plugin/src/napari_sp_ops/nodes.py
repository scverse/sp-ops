"""Classify sp-ops nodes by the attributes they carry, never by their names."""

from dataclasses import dataclass
from typing import Any

import zarr

from napari_sp_ops import rfc8

COLLECTION_KINDS = ("screen", "plate", "well", "modality", "tiles", "tile", "round", "merged")
LEAF_TYPES = {"sp-ops:table": "table", "sp-ops:shapes": "shapes", "sp-ops:points": "points"}
ELEMENT_TYPES = {"table": "table", "shapes": "shapes", "points": "points"}


@dataclass(frozen=True)
class Node:
    """An opened sp-ops node: its group, the string path it was opened from, and its descriptor."""

    group: zarr.Group
    path: str
    ref: rfc8.NodeRef | None = None

    @property
    def name(self) -> str:
        return self.ref.name if self.ref else rfc8.node_name(self.group)

    @property
    def attributes(self) -> dict[str, Any]:
        merged = dict(self.ref.attributes) if self.ref else {}
        merged.update(rfc8.ome_attributes(self.group))
        return merged

    def children(self) -> list["Node"]:
        nodes: list[Node] = []
        for ref in rfc8.child_refs(self.group):
            if ref.type in LEAF_TYPES and ref.type == "sp-ops:table":
                nodes.append(Node(self.group, rfc8.resolve_child_path(self.path, ref.path), ref))
                continue
            group, path = rfc8.open_child(self.group, self.path, ref)
            nodes.append(Node(group, path, ref))
        return nodes


def kind(node: Node) -> str:
    """Return the sp-ops kind of a node, from its descriptor type and attributes."""
    if node.ref and node.ref.type in LEAF_TYPES:
        return LEAF_TYPES[node.ref.type]
    element = node.group.attrs.get("spatialdata_attrs", {}).get("element_type")
    if element in ELEMENT_TYPES:
        return ELEMENT_TYPES[element]
    node_type = rfc8.ome_type(node.group)
    if node_type == "multiscale":
        return "multiscale"
    attributes = node.attributes
    if "sp-ops:spec" in attributes:
        return "screen"
    if "sp-ops:plate" in attributes or "plate" in attributes:
        return "plate"
    if "well" in attributes:
        return "well"
    if "sp-ops:modality" in attributes:
        return "modality"
    if "sp-ops:tiles" in attributes:
        return "tiles"
    if "sp-ops:tile" in attributes:
        return "tile"
    if attributes.get("sp-ops:axis", {}).get("name") == "round":
        return "round"
    if "sp-ops:merged" in attributes:
        return "merged"
    return "collection" if node_type == "collection" else "unknown"


def round_label(node: Node) -> str:
    """``round0 (cycle 1)`` for a round collection, from ``sp-ops:axis``."""
    axis = node.attributes.get("sp-ops:axis", {})
    label = f"round{axis.get('index', '?')}"
    if "value" in axis:
        label += f" (cycle {axis['value']})"
    return label


def channel_position(node: Node) -> int:
    """Array position of a raw channel multiscale from ``sp-ops:axis``."""
    return int(node.attributes.get("sp-ops:axis", {}).get("index", 0))
