"""napari reader entry point for sp-ops stores."""

import warnings
from collections.abc import Callable
from typing import Any

import zarr

from napari_sp_ops import nodes, rfc8, traverse, upstream


def napari_get_reader(path: str | list[str]) -> Callable | None:
    """Return a layer reader when ``path`` opens as a zarr group, else ``None``.

    Groups inside an sp-ops store are read here. Every other group is handed
    to napari-ome-zarr unchanged.
    """
    if isinstance(path, list):
        if not path:
            return None
        if len(path) > 1:
            warnings.warn(f"napari-sp-ops opens one path at a time; using {path[0]}", stacklevel=2)
        path = path[0]
    try:
        group = zarr.open_group(path, mode="r")
    except Exception as exc:
        warnings.warn(f"napari-sp-ops could not open {path} as a zarr group: {exc}", stacklevel=2)
        return None
    if not rfc8.inside_sp_ops_store(group, str(path)):
        return upstream.read_ome_zarr(group)

    def read(*_: Any, **__: Any) -> list[traverse.AnyLayerData]:
        return read_node(group, str(path))

    return read


def read_node(group: zarr.Group, path: str) -> list[traverse.AnyLayerData]:
    """Return the layers for one sp-ops node of any kind."""
    return traverse.read_node(nodes.Node(group, path))
