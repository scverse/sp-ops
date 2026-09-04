"""GeoParquet shapes and Parquet points through pyarrow and shapely."""

import numpy as np
import pytest
import zarr

from napari_sp_ops import vector
from napari_sp_ops.images import Placement
from spops_store import ISS_LAYOUT


def test_layout_polygons_become_yx_shapes_with_tile_features(synthetic_screen):
    group = zarr.open_group(str(synthetic_screen.layout), mode="r")
    polygons, metadata, layer_type = vector.read_shapes(group, Placement(name_prefix="iss "))
    assert layer_type == "shapes"
    assert metadata["name"] == "iss layout"
    assert metadata["shape_type"] == "polygon"
    assert metadata["text"]["string"] == "{tile}"
    assert list(metadata["features"]["tile"]) == [0, 1]
    x_min, y_min, x_max, y_max = ISS_LAYOUT[0]
    assert polygons[0].min(axis=0).tolist() == [y_min, x_min]
    assert polygons[0].max(axis=0).tolist() == [y_max, x_max]


def test_polygon_min_corners_are_y_then_x(synthetic_screen):
    group = zarr.open_group(str(synthetic_screen.layout), mode="r")
    assert vector.polygon_min_corners(group) == {0: (200.0, 100.0), 1: (200.0, 120.8)}


def test_points_are_yx_capped_and_translated(synthetic_screen):
    group = zarr.open_group(str(synthetic_screen.reads), mode="r")
    coordinates, metadata, layer_type = vector.read_points(group, cap=10, placement=Placement(translation_yx=(1.0, 2.0)))
    assert layer_type == "points"
    np.testing.assert_allclose(coordinates, [[3.6, 3.3], [7.5, 15.0], [20.5, 22.8]])
    assert set(metadata["features"]) == {"read", "barcode"}
    with pytest.warns(UserWarning, match="first 2 of 3 points"):
        coordinates, _, _ = vector.read_points(group, cap=2)
    assert coordinates.shape == (2, 2)
