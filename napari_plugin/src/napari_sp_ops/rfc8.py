"""Generic OME-NGFF RFC-8 helpers: attribute lookup and store detection.

RFC-8 puts ``plate``, ``well``, ``labels`` and every extension key under
``ome.attributes`` and keeps ``multiscales`` at the top of ``ome``. Nothing in
this module knows about sp-ops beyond the ``sp-ops:`` key prefix, so it is the
candidate for an upstream proposal to napari-ome-zarr.
"""

from dataclasses import dataclass
from typing import Any

import zarr

SP_OPS_PREFIX = "sp-ops:"
MAX_ANCESTORS = 12


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
    """Return the RFC-8 node type (``collection``, ``multiscale``...) when declared."""
    metadata = ome(group)
    node_type = metadata.get("type")
    if node_type is None and "multiscales" in metadata:
        return "multiscale"
    return node_type


def is_sp_ops_group(group: zarr.Group) -> bool:
    """True when the group is an RFC-8 collection or carries an ``sp-ops:*`` key."""
    if ome_type(group) == "collection":
        return True
    return any(key.startswith(SP_OPS_PREFIX) for key in ome_attributes(group))


def parent_path(path: str) -> str | None:
    """Return the parent of a local path or URL, or ``None`` at the top."""
    trimmed = path.rstrip("/")
    head, separator, _ = trimmed.rpartition("/")
    if not separator or not head or head.endswith(":") or head.endswith("/"):
        return None
    return head


def inside_sp_ops_store(group: zarr.Group, path: str) -> bool:
    """True when ``group`` or one of its ancestors up to the store root is sp-ops.

    Ancestors that do not open as a zarr group are skipped rather than
    stopping the walk, because well names such as ``A/1`` leave ``plate/A``
    without metadata of its own.
    """
    if is_sp_ops_group(group):
        return True
    current: str | None = path
    for _ in range(MAX_ANCESTORS):
        current = parent_path(current) if current else None
        if current is None:
            return False
        try:
            ancestor = zarr.open_group(current, mode="r")
        except Exception:
            continue
        if is_sp_ops_group(ancestor):
            return True
    return False


def node_name(group: zarr.Group) -> str:
    """Return the last path segment of the group, whether or not it is a store root."""
    if group.path:
        return group.path.rsplit("/", 1)[-1]
    return str(group.store_path).rstrip("/").rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Axis:
    name: str
    type: str
    unit: str | None = None

    @property
    def is_yx(self) -> bool:
        return self.type == "space" and self.name.lower() in {"y", "x"}


def multiscale_axes(group: zarr.Group) -> list[Axis]:
    """Return the axes of the first multiscale of an RFC-8 or 0.4+ image group."""
    multiscale = ome(group)["multiscales"][0]
    axes = multiscale.get("axes")
    if axes is None:
        axes = multiscale["coordinateSystems"][0]["axes"]
    return [Axis(axis["name"], axis.get("type", "space"), axis.get("unit")) for axis in axes]


def dataset_transforms(group: zarr.Group) -> list[dict[str, Any]]:
    """Return every coordinate transformation of the full-resolution dataset."""
    dataset = ome(group)["multiscales"][0]["datasets"][0]
    return [dict(transform) for transform in dataset.get("coordinateTransformations", [])]
