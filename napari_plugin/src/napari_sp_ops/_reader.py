"""napari reader entry point for sp-ops stores."""

import logging
from collections.abc import Callable

import zarr

from napari_sp_ops import upstream

log = logging.getLogger(__name__)


def napari_get_reader(path: str | list[str]) -> Callable | None:
    """Return a layer reader when ``path`` opens as a zarr group, else ``None``.

    Every group is handed to napari-ome-zarr unchanged.
    """
    if isinstance(path, list):
        if len(path) > 1:
            log.warning("napari-sp-ops opens one path at a time; using %s", path[0])
        path = path[0]
    try:
        group = zarr.open_group(path, mode="r")
    except Exception as exc:
        log.debug("%s is not a zarr group: %s", path, exc)
        return None
    return upstream.read_ome_zarr(group)
