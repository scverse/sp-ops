"""GeoParquet shapes and Parquet points through pyarrow and shapely."""

import numpy as np
import pytest
import zarr

from napari_sp_ops import nodes, vector
from napari_sp_ops.images import Placement
from spops_store import ISS_LAYOUT


def node_at(path) -> nodes.Node:
    return nodes.Node(zarr.open_group(str(path), mode="r"), str(path))


def test_layout_polygons_become_yx_shapes_with_tile_features(synthetic_screen):
    polygons, metadata, layer_type = vector.read_shapes(node_at(synthetic_screen.layout), Placement(name_prefix="iss "))
    assert layer_type == "shapes"
    assert metadata["name"] == "iss layout"
    assert metadata["shape_type"] == "polygon"
    assert metadata["text"]["string"] == "{tile}"
    assert list(metadata["features"]["tile"]) == [0, 1]
    x_min, y_min, x_max, y_max = ISS_LAYOUT[0]
    assert polygons[0].min(axis=0).tolist() == [y_min, x_min]
    assert polygons[0].max(axis=0).tolist() == [y_max, x_max]


def test_polygon_min_corners_are_y_then_x(synthetic_screen):
    polygons, metadata, _ = vector.read_shapes(node_at(synthetic_screen.layout))
    assert vector.min_corners(polygons, metadata["features"]["tile"]) == {0: (200.0, 100.0), 1: (200.0, 120.8)}


def test_points_are_yx_capped_and_translated(synthetic_screen):
    node = node_at(synthetic_screen.reads)
    coordinates, metadata, layer_type = vector.read_points(node, cap=10, placement=Placement(translation_yx=(1.0, 2.0)))
    assert layer_type == "points"
    np.testing.assert_allclose(coordinates, [[2.6, 1.3], [6.5, 13.0], [19.5, 20.8]])
    assert metadata["translate"] == [1.0, 2.0]
    assert metadata["name"] == "reads"
    assert set(metadata["features"]) == {"read", "barcode"}
    with pytest.warns(UserWarning, match="first 2 of 3 points"):
        coordinates, _, _ = vector.read_points(node, cap=2)
    assert coordinates.shape == (2, 2)
