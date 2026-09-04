"""Record how napari-ome-zarr and zarr behave on sp-ops stores today.

Every assertion here is a behaviour the plugin works around or relies on. A
failure means the pinned upstream changed, and the matching code in
``napari_sp_ops`` needs a second look.
"""

import warnings

import pytest
import zarr
from napari_ome_zarr._reader import napari_get_reader as upstream_get_reader


def upstream_layers(path) -> list:
    reader = upstream_get_reader(str(path))
    assert reader is not None, f"napari-ome-zarr declined {path}"
    return reader(str(path))


def only_layer(path) -> tuple:
    layers = upstream_layers(path)
    assert len(layers) == 1, [meta.get("name") for _, meta, _ in layers]
    return layers[0]


COLLECTION_NODES = ["root", "plate_processed", "well", "modality", "merged", "plate_raw", "raw_tiles", "raw_tile", "raw_round"]

# attribute, channel_axis, axis_labels, scale, shape of the full-resolution array
LEAF_IMAGES = [
    ("image", 1, ("T", "Z", "Y", "X"), [1.0, 2.0, 0.325, 0.325], (1, 2, 1, 16, 16)),
    ("labels", 1, ("T", "Z", "Y", "X"), [1.0, 2.0, 0.65, 0.65], (1, 1, 1, 16, 16)),
    ("overlay", 2, ("y", "x"), [1.0, 1.0], (16, 16, 4)),
    ("raw_channel_yx", None, ("y", "x"), [1.3, 1.3], (16, 16)),
    ("raw_channel_zyx", None, ("z", "y", "x"), [1.5, 0.325, 0.325], (2, 16, 16)),
]


@pytest.mark.parametrize("attribute", COLLECTION_NODES)
def test_collection_yields_no_layers(synthetic_screen, attribute):
    assert upstream_layers(getattr(synthetic_screen, attribute)) == []


@pytest.mark.parametrize(("attribute", "channel_axis", "axis_labels", "scale", "shape"), LEAF_IMAGES)
def test_leaf_opens_as_unnamed_image_layer(synthetic_screen, attribute, channel_axis, axis_labels, scale, shape):
    """Labels and RGBA overlays come back as plain image layers; nothing gets a name or colormap."""
    data, meta, layer_type = only_layer(getattr(synthetic_screen, attribute))
    assert layer_type == "image"
    assert meta.get("channel_axis") == channel_axis
    assert meta["axis_labels"] == axis_labels
    assert meta["scale"] == scale
    assert meta.get("name") is None
    assert "colormap" not in meta
    assert data[0].shape == shape


def test_well_path_resolves_without_intermediate_metadata(synthetic_screen):
    """``plate/A`` has no zarr.json, so the well is reachable only by its full path."""
    plate = zarr.open_group(str(synthetic_screen.plate_processed), mode="r")
    assert plate["A/1"].attrs["ome"]["type"] == "collection"
    with pytest.raises(KeyError):
        plate["A"]
    with pytest.raises(zarr.errors.GroupNotFoundError):
        zarr.open_group(str(synthetic_screen.plate_processed / "A"), mode="r")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert list(plate.keys()) == []


def test_processed_example_matches_synthetic_baseline(processed_example):
    merged = processed_example / "plate1_processed" / "A" / "1" / "pheno" / "merged"
    assert upstream_layers(processed_example) == []
    assert upstream_layers(processed_example / "library") == []
    assert upstream_layers(merged) == []
    _, meta, layer_type = only_layer(merged / "image")
    assert (layer_type, meta["channel_axis"], meta["axis_labels"]) == ("image", 1, ("T", "Z", "Y", "X"))
    _, meta, layer_type = only_layer(merged / "cell_seg")
    assert (layer_type, meta["channel_axis"]) == ("image", 1)
    _, meta, layer_type = only_layer(merged / "grid_overlay")
    assert (layer_type, meta["channel_axis"]) == ("image", 2)


def test_raw_example_matches_synthetic_baseline(raw_example):
    tiles = raw_example / "plate1_raw" / "A" / "1" / "iss" / "tiles"
    assert upstream_layers(raw_example) == []
    assert upstream_layers(tiles) == []
    assert upstream_layers(tiles / "layout") == []
    assert upstream_layers(tiles / "tile0") == []
    assert upstream_layers(tiles / "tile0" / "round0") == []
    _, meta, _ = only_layer(tiles / "tile0" / "round0" / "channel0")
    assert meta["axis_labels"] == ("y", "x")
    _, meta, _ = only_layer(raw_example / "plate1_raw" / "A" / "1" / "pheno" / "tiles" / "tile0" / "channel0")
    assert meta["axis_labels"] == ("z", "y", "x")
