"""Writers for the four element kinds an sp-ops store holds.

ome-zarr-py supplies the pixels and the pyramid; it never supplies the metadata.
RFC-8 says its `Multiscale` node "replaces the multiscale metadata defined in the
previous versions of the OME-Zarr specification", and assumption A2 says this
store writes RFC-8 nodes, so `group.attrs["ome"]` is overwritten after every
library call. The `multiscales` block that goes back in is this module's own,
built from the level numbers rather than left as ome-zarr-py wrote it, because
no reader in circulation finds a pyramid anywhere else; see `multiscales_block`. `write_labels`, `write_plate_metadata` and `write_well_metadata` are
structurally wrong here and are never used: labels are siblings of `image` inside
a `merged` collection, identified by the RFC-8 `labels.source` attribute.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import anndata as ad
import dask.array as da
import geopandas as gpd
import numpy as np
import pandas as pd
import zarr
from ome_zarr import writer as ozw
from ome_zarr.scale import Methods

from .rfc8 import SD_VERSION, image_axes, level_nodes, multiscales_block, node, set_ome

# ome-zarr-py names pyramid levels s0, s1, s2 (writer.py: `f"s{idx}"`), which is
# not configurable. The store uses 0, 1, 2, so they are renamed after the write.
LEVEL_PREFIX = "s"


def _local_root(group: zarr.Group) -> Path:
    """The group's directory, or a clear error if this is not a LocalStore.

    Renaming pyramid levels and writing the parquet sidecars both need a real
    directory. zarr-python 3 has no rename API at all -- `Group.move` does not
    exist and `AsyncGroup.move` is a stub that raises NotImplementedError -- so
    this is a hard requirement rather than a convenience.
    """
    root = getattr(group.store, "root", None)
    if root is None:
        raise TypeError(
            f"{type(group.store).__name__} has no `root`; sp-ops elements can only "
            "be written to a LocalStore (pyramid levels are renamed on disk and "
            "shapes/points are parquet sidecars inside the group directory)")
    return Path(root) / group.path


def _rename_levels(group: zarr.Group, n_levels: int) -> None:
    """s0, s1, s2 -> 0, 1, 2.

    Done before the RFC-8 node is written, so the store is never left with
    metadata that disagrees with disk. A Zarr v3 array's zarr.json does not record
    its own name, so this is purely a directory move with no metadata to repair.
    Level 0 must end up named `0`: check_sp_ops_zarr.py reads it by literal name
    in `extent_um`, and when that returns None the label-extent advisory is
    skipped silently, quietly lowering the check count.
    """
    base = _local_root(group)
    for i in range(n_levels):
        src = base / f"{LEVEL_PREFIX}{i}"
        if src.exists():
            src.rename(base / str(i))


def _storage_options(shapes: Sequence[tuple[int, ...]], *, max_chunk: int,
                     shard_factor: int | None) -> list[dict]:
    """Per-level chunk, and shard, sizes.

    Leading non-spatial axes get 1, so a chunk is one (round, channel) plane.
    In zarr v3 a sharded array's top level `chunk_grid` is the *shard* and the
    sharding codec's inner `chunk_shape` is the chunk, which is the way round
    ome-zarr-py passes these through: with `shards` set, the `chunks` given here
    become the zarr chunks. ome-zarr-py reconciles the two so a shard is always
    an integer multiple of a chunk, which is what the previous hand-rolled
    `min(1024, s)` / `min(2048, s)` pair did not guarantee.
    """
    opts = []
    for shape in shapes:
        lead = (1,) * (len(shape) - 2)
        chunk = lead + tuple(min(max_chunk, s) for s in shape[-2:])
        o: dict = {"chunks": chunk}
        if shard_factor is not None:
            o["shards"] = lead + tuple(min(shard_factor, s) for s in shape[-2:])
        opts.append(o)
    return opts


def write_multiscale(parent: zarr.Group, name: str, *,
                     data: np.ndarray | da.Array | None = None,
                     pyramid: Sequence[np.ndarray] | None = None,
                     axis_names: Sequence[str],
                     attributes: dict,
                     pixel_size_um: float,
                     levels: int = 3,
                     labels: bool = False,
                     cs_id: str = "px",
                     origin_um: tuple[float, float] = (0.0, 0.0),
                     max_chunk: int = 512,
                     shard_factor: int | None = None,
                     element_id: str | None = None) -> dict:
    """One RFC-8 multiscale of inlined singlescale levels.

    Pass `data` to have the pyramid derived, or `pyramid` to write levels that
    already exist -- a source store's own pyramid is copied rather than recomputed.

    The multiscale's coordinate system is in micrometres, so a level's transform
    carries the pixel size and the parent collection only has to translate.
    `origin_um` is where the array's first pixel sits in that frame, which is how
    a stitcher's fuse crop is recorded.
    """
    if (data is None) == (pyramid is None):
        raise ValueError("pass exactly one of data= or pyramid=")

    group = parent.create_group(name)
    axes = image_axes(axis_names)

    if pyramid is not None:
        pyramid = list(pyramid)
        opts = _storage_options([p.shape for p in pyramid],
                                max_chunk=max_chunk, shard_factor=shard_factor)
        ozw.write_multiscale(pyramid, group, axes=axes, storage_options=opts,
                             compute=True)
        n_levels = len(pyramid)
    else:
        # Only y and x are downsampled; round, t, c and z pass through.
        shapes = [tuple(data.shape[:-2])
                  + (data.shape[-2] // 2 ** i, data.shape[-1] // 2 ** i)
                  for i in range(levels)]
        opts = _storage_options(shapes, max_chunk=max_chunk,
                                shard_factor=shard_factor)
        ozw.write_image(
            da.asarray(data), group,
            scale_factors=[{"y": 2 ** i, "x": 2 ** i} for i in range(1, levels)],
            # NEAREST is the only method that preserves label values. Note it is
            # skimage.resize(order=0), not stepped slicing, so a label level above
            # 0 differs from `a[..., ::2, ::2]`; only level 0 is ever compared
            # against the source.
            method=Methods.NEAREST if labels else Methods.LOCAL_MEAN,
            axes=axes, storage_options=opts, compute=True)
        n_levels = levels

    _rename_levels(group, n_levels)

    element_type = "labels" if labels else "image"
    attrs = dict(attributes)
    attrs["coordinateSystems"] = [{"id": cs_id, "axes": axes}]
    set_ome(group, "multiscale", name, attributes=attrs,
            nodes=level_nodes(n_levels, axis_names, pixel_size_um=pixel_size_um,
                              out_cs=cs_id, origin_um=origin_um),
            multiscales=multiscales_block(name, n_levels, axis_names,
                                          pixel_size_um=pixel_size_um,
                                          origin_um=origin_um))
    group.attrs["spatialdata_attrs"] = {"element_type": element_type,
                                        "version": SD_VERSION[element_type]}
    return node("multiscale", name, f"./{name}", element_id=element_id)


def _stringify(df: pd.DataFrame) -> pd.DataFrame:
    """AnnData obs cannot hold list valued columns; keep them as JSON strings."""
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            sample = out[col].dropna()
            if len(sample) and isinstance(sample.iloc[0], (list, np.ndarray)):
                out[col] = out[col].map(
                    lambda v: json.dumps(np.asarray(v).tolist())
                    if isinstance(v, (list, np.ndarray)) else None)
            else:
                out[col] = out[col].astype(str).where(out[col].notna(), None)
    return out


def write_table(parent: zarr.Group, name: str, obs: pd.DataFrame, *,
                X: np.ndarray | None = None, var: pd.DataFrame | None = None,
                stringify: bool = True, clear_index_name: bool = True,
                element_id: str | None = None) -> dict:
    """A SpatialData table, AnnData on disk.

    `stringify` and `clear_index_name` are explicit because the two datasets
    genuinely differ: one has list valued columns that AnnData cannot hold, the
    other has object columns that coercing would change for no reason.
    """
    obs = _stringify(obs) if stringify else obs.copy()
    obs.index = obs.index.astype(str)
    if clear_index_name:
        obs.index = obs.index.rename(None)
    if X is None:
        X = np.zeros((len(obs), 0), dtype=np.float32)
    kwargs: dict = {"X": X, "obs": obs}
    if var is not None:
        var = var.copy()
        var.index = var.index.astype(str).rename(None)
        kwargs["var"] = var

    # Keyed by name under the parent. `write_elem(group, "/", ...)` would delete
    # every sibling at the store root.
    ad.io.write_elem(parent, name, ad.AnnData(**kwargs))
    path = f"{parent.path}/{name}" if parent.path else name
    grp = zarr.open_group(store=parent.store, path=path, mode="r+")
    grp.attrs["spatialdata_attrs"] = {"element_type": "table",
                                      "version": SD_VERSION["table"]}
    return node("sp-ops:table", name, f"./{name}", element_id=element_id)


def write_points(parent: zarr.Group, name: str, df: pd.DataFrame, *,
                 axes: Sequence[str] = ("y", "x"),
                 element_id: str | None = None) -> dict:
    """A SpatialData points element, Parquet inside the group directory."""
    group = parent.create_group(name)
    target = _local_root(group) / "points.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index(drop=True).to_parquet(target, index=False)
    group.attrs["spatialdata_attrs"] = {"element_type": "points",
                                        "version": SD_VERSION["points"],
                                        "axes": list(axes)}
    return node("sp-ops:points", name, f"./{name}", element_id=element_id)


def write_shapes(parent: zarr.Group, name: str, gdf: gpd.GeoDataFrame, *,
                 axes: Sequence[str] = ("y", "x"),
                 element_id: str | None = None) -> dict:
    """A SpatialData shapes element, GeoParquet inside the group directory."""
    group = parent.create_group(name)
    target = _local_root(group) / "shapes.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    gdf = gdf.copy()
    gdf.index = gdf.index.astype(str)
    gdf.to_parquet(target, index=True)
    group.attrs["spatialdata_attrs"] = {"element_type": "shapes",
                                        "version": SD_VERSION["shapes"],
                                        "axes": list(axes),
                                        "geos": {"name": "POLYGON", "type": 3}}
    return node("sp-ops:shapes", name, f"./{name}", element_id=element_id)
