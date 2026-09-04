"""napari reader entry point for sp-ops stores."""

import warnings
from collections.abc import Callable

import zarr

from napari_sp_ops import upstream


def napari_get_reader(path: str | list[str]) -> Callable | None:
    """Return a layer reader when ``path`` opens as a zarr group, else ``None``.

    Every group is handed to napari-ome-zarr unchanged.
    """
    if isinstance(path, list):
        if len(path) > 1:
            warnings.warn(f"napari-sp-ops opens one path at a time; using {path[0]}", stacklevel=2)
        path = path[0]
    try:
        group = zarr.open_group(path, mode="r")
    except Exception as exc:
        warnings.warn(f"napari-sp-ops could not open {path} as a zarr group: {exc}", stacklevel=2)
        return None
    return upstream.read_ome_zarr(group)
