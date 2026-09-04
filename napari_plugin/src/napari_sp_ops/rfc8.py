"""Generic OME-NGFF RFC-8 helpers: attribute lookup, node descriptors and store detection.

RFC-8 puts ``plate``, ``well``, ``labels`` and every extension key under
``ome.attributes`` and keeps ``multiscales`` at the top of ``ome``. Nothing in
this module knows about sp-ops beyond the ``sp-ops:`` key prefix, so it is the
candidate for an upstream proposal to napari-ome-zarr.
"""

import posixpath
import re
import warnings
from dataclasses import dataclass, field
from typing import Any

import zarr

SP_OPS_PREFIX = "sp-ops:"
MAX_ANCESTORS = 12
STORE_SUFFIX = ".zarr"
SEPARATORS = re.compile(r"[/\\]")


def ome(group: zarr.Group) -> dict[str, Any]:
    """Return the ``ome`` metadata of ``group``, or an empty dict."""
    value = group.attrs.get("ome")
    return value if isinstance(value, dict) else {}


def ome_attributes(group: zarr.Group) -> dict[str, Any]:
    """Return ``ome.attributes`` for an RFC-8 node, falling back to ``ome`` itself."""
    metadata = ome(group)
    attributes = metadata.get("attributes")
    return attributes if isinstance(attributes, dict) else metadata


def ome_type(group: zarr.Group) -> str | None:
    """Return the RFC-8 node type (``collection``, ``multiscale``...) when declared or implied."""
    metadata = ome(group)
    node_type = metadata.get("type")
    if node_type is None and "multiscales" in metadata:
        return "multiscale"
    return node_type


def has_sp_ops_keys(group: zarr.Group) -> bool:
    return any(key.startswith(SP_OPS_PREFIX) for key in ome_attributes(group))


def last_segment(path: str) -> str:
    """The final path or URL segment, whatever the separator."""
    parts = [part for part in SEPARATORS.split(path) if part]
    return parts[-1] if parts else path


def parent_path(path: str) -> str | None:
    """Return the parent of a local path (either separator) or URL, or ``None`` at the top."""
    trimmed = re.sub(r"[/\\]+$", "", path)
    match = list(SEPARATORS.finditer(trimmed))
    if not match:
        return None
    head = trimmed[: match[-1].start()]
    if not head or head.endswith(":") or head.endswith("/") or head.endswith("\\"):
        return None
    return head


def inside_sp_ops_store(group: zarr.Group, path: str) -> bool:
    """True when ``group`` or an ancestor up to the store root carries an ``sp-ops:`` key.

    A bare RFC-8 collection with no sp-ops key anywhere above it is also
    claimed, because napari-ome-zarr cannot open collections at all. Ancestors
    that do not open as a zarr group are skipped rather than stopping the
    walk, because well names such as ``A/1`` leave ``plate/A`` without
    metadata of its own. The walk stops at the first ``.zarr`` component.
    """
    if has_sp_ops_keys(group):
        return True
    current: str | None = path
    for _ in range(MAX_ANCESTORS):
        if current is None or last_segment(current).endswith(STORE_SUFFIX):
            break
        current = parent_path(current)
        if current is None:
            break
        try:
            ancestor = zarr.open_group(current, mode="r")
        except Exception:
            continue
        if has_sp_ops_keys(ancestor):
            return True
    return ome_type(group) == "collection"


@dataclass(frozen=True)
class Axis:
    name: str
    type: str
    unit: str | None = None

    @property
    def is_yx(self) -> bool:
        return self.type == "space" and self.name.lower() in {"y", "x"}


def multiscale_axes(group: zarr.Group) -> list[Axis]:
    """Axes of the first multiscale, from ``axes``, its ``coordinateSystems``, or the node's."""
    multiscale = ome(group)["multiscales"][0]
    axes = multiscale.get("axes")
    if axes is None and "coordinateSystems" in multiscale:
        axes = multiscale["coordinateSystems"][0]["axes"]
    if axes is None:
        axes = ome_attributes(group)["coordinateSystems"][0]["axes"]
    return [Axis(axis["name"], axis.get("type", "space"), axis.get("unit")) for axis in axes]


def dataset_transforms(group: zarr.Group) -> list[dict[str, Any]]:
    """Return every coordinate transformation of the full-resolution dataset."""
    dataset = ome(group)["multiscales"][0]["datasets"][0]
    return [dict(transform) for transform in dataset.get("coordinateTransformations", [])]


@dataclass(frozen=True)
class NodeRef:
    """One entry of an RFC-8 collection's ``nodes`` list.

    An entry with its own ``nodes`` and no ``path`` is an inline collection
    stored in the parent's metadata; its children carry paths relative to the
    parent group.
    """

    type: str
    name: str
    path: str | None
    id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    nodes: list[dict[str, Any]] | None = None

    @property
    def inline(self) -> bool:
        return self.path is None


def parse_refs(entries: list[dict[str, Any]]) -> list[NodeRef]:
    """Turn RFC-8 node descriptors into ``NodeRef`` objects, skipping unusable ones."""
    refs: list[NodeRef] = []
    for entry in entries:
        path = entry.get("path")
        if isinstance(path, dict):
            path = path.get("path") if path.get("type", "zarr") == "zarr" else None
        if path is None and not isinstance(entry.get("nodes"), list):
            warnings.warn(f"napari-sp-ops skips node {entry.get('name')!r}: no zarr path", stacklevel=2)
            continue
        refs.append(NodeRef(entry.get("type", ""), entry.get("name") or last_segment(path or ""), path, entry.get("id"), entry.get("attributes") or {}, entry.get("nodes")))
    return refs


def child_refs(group: zarr.Group) -> list[NodeRef]:
    """Return the node descriptors of a collection group."""
    return parse_refs(ome(group).get("nodes", []))


def resolve_child_path(path: str, relative: str) -> str:
    """Join an RFC-8 relative node path onto the string path of its collection."""
    base = path.rstrip("/")
    for part in relative.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            parent = parent_path(base)
            if parent is None:
                raise ValueError(f"{relative!r} climbs above {path!r}")
            base = parent
        else:
            base = f"{base}/{part}"
    return base


def open_child(group: zarr.Group, path: str, relative: str) -> tuple[zarr.Group, str]:
    """Open a child by its RFC-8 relative path, through the parent's store when it stays inside.

    Only a reference that climbs above the store root is reopened from its
    string path, which is how RFC-8 lets a plate live in another store.
    """
    child_path = resolve_child_path(path, relative)
    inside = posixpath.normpath(posixpath.join(group.path or ".", relative))
    if inside.startswith(".."):
        return zarr.open_group(child_path, mode="r"), child_path
    return zarr.open_group(store=group.store, path="" if inside == "." else inside, mode="r"), child_path


def resolve_reference(refs: list[NodeRef], reference: dict[str, Any] | None) -> NodeRef | None:
    """Find the descriptor an RFC-8 ``Reference`` (``id`` and/or ``path``) points at."""
    if not isinstance(reference, dict):
        return None
    target_id = reference.get("id")
    target_path = reference.get("path", {})
    target_path = target_path.get("path") if isinstance(target_path, dict) else target_path
    for ref in refs:
        if target_id is not None and ref.id == target_id:
            return ref
    for ref in refs:
        if target_path is not None and ref.path is not None and posixpath.normpath(ref.path) == posixpath.normpath(target_path):
            return ref
    return None
