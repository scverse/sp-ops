"""Classify sp-ops nodes by the attributes they carry, never by their names."""

import warnings
from dataclasses import dataclass
from typing import Any

import zarr

from napari_sp_ops import rfc8

ELEMENT_KINDS = frozenset({"table", "shapes", "points"})
LEAF_TYPES = {f"{rfc8.SP_OPS_PREFIX}{kind}": kind for kind in ELEMENT_KINDS}
TABLE_TYPE = f"{rfc8.SP_OPS_PREFIX}table"


@dataclass(frozen=True)
class Node:
    """An opened sp-ops node: its group, the string path it was opened from, and its descriptor.

    An inline node shares its parent's group and carries only descriptor
    attributes. A table node is never opened; it keeps the parent group too.
    """

    group: zarr.Group
    path: str
    ref: rfc8.NodeRef | None = None

    @property
    def name(self) -> str:
        return self.ref.name if self.ref else rfc8.last_segment(self.path)

    @property
    def opened(self) -> bool:
        return self.ref is None or not (self.ref.inline or self.ref.type == TABLE_TYPE)

    @property
    def attributes(self) -> dict[str, Any]:
        merged = dict(self.ref.attributes) if self.ref else {}
        if self.opened:
            merged.update(rfc8.ome_attributes(self.group))
        return merged

    def child_refs(self) -> list[rfc8.NodeRef]:
        """Descriptors of the children, from the inline descriptor or the group metadata."""
        if self.ref is not None and self.ref.inline:
            return rfc8.parse_refs(self.ref.nodes or [])
        return rfc8.child_refs(self.group) if self.opened else []

    def child(self, ref: rfc8.NodeRef) -> "Node | None":
        """Open one child descriptor, or warn and return ``None`` when its group is missing."""
        if ref.inline or ref.type == TABLE_TYPE:
            path = self.path if ref.inline else rfc8.resolve_child_path(self.path, ref.path or "")
            return Node(self.group, path, ref)
        try:
            group, path = rfc8.open_child(self.group, self.path, ref.path or "")
        except Exception as exc:
            warnings.warn(f"napari-sp-ops skips {ref.name}: {exc}", stacklevel=2)
            return None
        if not isinstance(group, zarr.Group):
            warnings.warn(f"napari-sp-ops skips {ref.name}: not a zarr group", stacklevel=2)
            return None
        return Node(group, path, ref)

    def children(self) -> list["Node"]:
        return [child for child in (self.child(ref) for ref in self.child_refs()) if child is not None]


def kind(node: Node) -> str:
    """Return the sp-ops kind of a node, from its descriptor type and attributes."""
    if node.ref and node.ref.type in LEAF_TYPES:
        return LEAF_TYPES[node.ref.type]
    if node.opened:
        element = node.group.attrs.get("spatialdata_attrs", {}).get("element_type")
        if element in ELEMENT_KINDS:
            return element
        node_type = rfc8.ome_type(node.group)
        if node_type == "multiscale":
            return "multiscale" if "multiscales" in rfc8.ome(node.group) else "unknown"
    else:
        node_type = "collection"
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


def channel_position(node: Node) -> int | None:
    """Array position of a raw channel multiscale from ``sp-ops:axis``, if declared."""
    value = node.attributes.get("sp-ops:axis", {}).get("index")
    return int(value) if value is not None else None
