"""Parquet points and GeoParquet shapes to napari layer data, through pyarrow and shapely."""

import json
import warnings
from typing import Any

import fsspec
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from napari_sp_ops import nodes
from napari_sp_ops.images import Placement

VectorLayerData = tuple[Any, dict[str, Any], str]

SHAPES_FILE = "shapes.parquet"
POINTS_FILE = "points.parquet"
DEFAULT_GEOMETRY_COLUMN = "geometry"
TILE_COLUMN = "tile"
SHAPES_EDGE_WIDTH = 2
POINTS_SIZE = 4
SCALAR_TYPES = (pa.types.is_integer, pa.types.is_floating, pa.types.is_string, pa.types.is_boolean)


def element_file(node: nodes.Node, filename: str) -> str:
    """Path or URL of a file stored inside an element group."""
    return f"{node.path.rstrip('/')}/{filename}"


def features_from(table: pa.Table, exclude: tuple[str, ...]) -> dict[str, np.ndarray]:
    features: dict[str, np.ndarray] = {}
    for name in table.column_names:
        column = table.column(name)
        if name in exclude or not any(check(column.type) for check in SCALAR_TYPES):
            continue
        features[name] = column.to_numpy(zero_copy_only=False)
    return features


def geometry_column(table: pa.Table) -> str:
    metadata = table.schema.metadata or {}
    geo = metadata.get(b"geo")
    if geo:
        try:
            return json.loads(geo).get("primary_column", DEFAULT_GEOMETRY_COLUMN)
        except ValueError:
            pass
    return DEFAULT_GEOMETRY_COLUMN


def exterior_rings(geometries: np.ndarray) -> list[np.ndarray]:
    """Outer ring of every polygon part, as y, x vertices; holes are dropped."""
    rings: list[np.ndarray] = []
    for geometry in geometries:
        for part in shapely.get_parts(geometry):
            ring = shapely.get_exterior_ring(part) if shapely.get_type_id(part) == shapely.GeometryType.POLYGON else part
            rings.append(shapely.get_coordinates(ring)[:, ::-1])
    return rings


def read_shapes(node: nodes.Node, placement: Placement | None = None) -> VectorLayerData:
    """A GeoParquet polygon file becomes a napari shapes layer with its columns as features.

    Only the exterior ring of the first part of each geometry is drawn, so a
    multipolygon or a polygon with holes contributes one polygon per part.
    """
    placement = placement or Placement()
    with fsspec.open(element_file(node, SHAPES_FILE), "rb") as handle:
        table = pq.read_table(handle)
    column = geometry_column(table)
    geometries = shapely.from_wkb(table.column(column).to_numpy(zero_copy_only=False))
    parts = [len(shapely.get_parts(geometry)) for geometry in geometries]
    polygons = exterior_rings(geometries)
    features = features_from(table, exclude=(column,))
    if any(count != 1 for count in parts):
        features = {name: np.repeat(values, parts) for name, values in features.items()}
    metadata: dict[str, Any] = {
        "name": placement.name_prefix + node.name,
        "shape_type": "polygon",
        "edge_color": "yellow",
        "face_color": "transparent",
        "edge_width": SHAPES_EDGE_WIDTH,
        "features": features,
        "metadata": {"sp-ops": {**placement.metadata, "path": node.path, "node": node.name}},
    }
    if placement.translation_yx is not None:
        metadata["translate"] = list(placement.translation_yx)
    if TILE_COLUMN in features:
        metadata["text"] = {"string": "{tile}", "color": "yellow", "anchor": "upper_left"}
    return polygons, metadata, "shapes"


def min_corners(polygons: list[np.ndarray], keys: np.ndarray) -> dict[int, tuple[float, float]]:
    """Map each polygon's key to the y, x minimum corner of its vertices."""
    return {int(key): (float(polygon[:, 0].min()), float(polygon[:, 1].min())) for key, polygon in zip(keys, polygons, strict=True)}


def read_points(node: nodes.Node, cap: int, placement: Placement | None = None) -> VectorLayerData:
    """A Parquet file with ``x`` and ``y`` columns becomes a points layer, reading at most ``cap`` rows.

    Coordinates are taken as written, in the element's coordinate system;
    the placement offset goes to the layer's ``translate``.
    """
    placement = placement or Placement()
    with fsspec.open(element_file(node, POINTS_FILE), "rb") as handle:
        parquet = pq.ParquetFile(handle)
        total = parquet.metadata.num_rows
        columns = [name for name in parquet.schema_arrow.names if any(check(parquet.schema_arrow.field(name).type) for check in SCALAR_TYPES)]
        batches: list[pa.RecordBatch] = []
        rows = 0
        for batch in parquet.iter_batches(columns=columns):
            batches.append(batch.slice(0, max(0, cap - rows)))
            rows += batch.num_rows
            if rows >= cap:
                break
        table = pa.Table.from_batches(batches, schema=pa.schema([parquet.schema_arrow.field(name) for name in columns]))
    if total > cap:
        warnings.warn(f"napari-sp-ops shows the first {cap} of {total} points in {node.name}", stacklevel=2)
    coordinates = np.column_stack([table.column("y").to_numpy(), table.column("x").to_numpy()])
    metadata: dict[str, Any] = {
        "name": placement.name_prefix + node.name,
        "size": POINTS_SIZE,
        "features": features_from(table, exclude=("x", "y")),
        "metadata": {"sp-ops": {**placement.metadata, "path": node.path, "node": node.name}},
    }
    if placement.translation_yx is not None:
        metadata["translate"] = list(placement.translation_yx)
    return coordinates, metadata, "points"
