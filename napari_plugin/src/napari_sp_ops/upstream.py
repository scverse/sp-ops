"""The only module that imports napari-ome-zarr internals.

napari-ome-zarr declares no public API beyond its reader entry point. The
symbols re-exported here are the ones this plugin relies on, and the
dependency is pinned to ``napari-ome-zarr>=0.10,<0.11`` for that reason.
"""

from napari_ome_zarr.ome_zarr_reader import read_ome_zarr

__all__ = ["read_ome_zarr"]
