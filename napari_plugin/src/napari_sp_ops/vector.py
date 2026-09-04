"""Parquet points and GeoParquet shapes to napari layer data, through pyarrow and shapely."""

import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
import zarr

from napari_sp_ops.images import Placement

VectorLayerData = tuple[Any, dict[str, Any], str]

SHAPES_FILE = "shapes.parquet"
POINTS_FILE = "points.parquet"
SCALAR_TYPES = (pa.types.is_integer, pa.types.is_floating, pa.types.is_string, pa.types.is_boolean)


def element_file(group: zarr.Group, filename: str) -> str:
    """Path or URL of a file stored inside an element group."""
    root = getattr(group.store, "root", None)
    if root is not None:
        return str(Path(root) / group.path / filename)
    return f"{str(group.store_path).rstrip('/')}/{filename}"


def read_table(path: str) -> pa.Table:
    return pq.read_table(path)


def features_from(table: pa.Table, exclude: tuple[str, ...]) -> dict[str, np.ndarray]:
    features: dict[str, np.ndarray] = {}
    for name in table.column_names:
        column = table.column(name)
        if name in exclude or not any(check(column.type) for check in SCALAR_TYPES):
            continue
        features[name] = column.to_numpy(zero_copy_only=False)
    return features


def read_shapes(group: zarr.Group, placement: Placement | None = None) -> VectorLayerData:
    """A GeoParquet polygon file becomes a napari shapes layer with its columns as features."""
    placement = placement or Placement()
    table = read_table(element_file(group, SHAPES_FILE))
    geometries = shapely.from_wkb(table.column("geometry").to_numpy(zero_copy_only=False))
    polygons = [np.asarray(shapely.get_coordinates(geometry))[:, ::-1] for geometry in geometries]
    features = features_from(table, exclude=("geometry",))
    metadata: dict[str, Any] = {
        "name": placement.name_prefix + "layout",
        "shape_type": "polygon",
        "edge_color": "yellow",
        "face_color": "transparent",
        "edge_width": 2,
        "features": features,
        "metadata": {"sp-ops": {**placement.metadata, "path": str(group.store_path)}},
    }
    if "tile" in features:
        metadata["text"] = {"string": "{tile}", "color": "yellow", "anchor": "upper_left"}
    return polygons, metadata, "shapes"


def read_points(group: zarr.Group, cap: int, placement: Placement | None = None) -> VectorLayerData:
    """A Parquet file with ``x`` and ``y`` columns becomes a napari points layer, capped at ``cap`` rows."""
    placement = placement or Placement()
    table = read_table(element_file(group, POINTS_FILE))
    if table.num_rows > cap:
        warnings.warn(f"napari-sp-ops shows the first {cap} of {table.num_rows} points in {group.path or 'points'}", stacklevel=2)
        table = table.slice(0, cap)
    coordinates = np.column_stack([table.column("y").to_numpy(), table.column("x").to_numpy()])
    if placement.translation_yx is not None:
        coordinates = coordinates + np.asarray(placement.translation_yx)
    metadata: dict[str, Any] = {
        "name": placement.name_prefix + (group.path.rsplit("/", 1)[-1] or "points"),
        "size": 4,
        "features": features_from(table, exclude=("x", "y")),
        "metadata": {"sp-ops": {**placement.metadata, "path": str(group.store_path)}},
    }
    return coordinates, metadata, "points"


def polygon_min_corners(group: zarr.Group, key: str = "tile") -> dict[int, tuple[float, float]]:
    """Map each polygon's ``key`` column to the y, x minimum corner of its bounds."""
    table = read_table(element_file(group, SHAPES_FILE))
    geometries = shapely.from_wkb(table.column("geometry").to_numpy(zero_copy_only=False))
    keys = table.column(key).to_pylist()
    bounds = shapely.bounds(geometries)
    return {int(index): (float(box[1]), float(box[0])) for index, box in zip(keys, bounds, strict=True)}
