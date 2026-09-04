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


COLLECTION_NODES = ["root", "plate_processed", "well", "modality", "merged", "plate_raw", "raw_tile", "raw_round"]


@pytest.mark.parametrize("attribute", COLLECTION_NODES)
def test_collection_yields_no_layers(synthetic_screen, attribute):
    assert upstream_layers(getattr(synthetic_screen, attribute)) == []


def test_processed_image_splits_channels_and_keeps_singleton_axes(synthetic_screen):
    data, meta, layer_type = only_layer(synthetic_screen.image)
    assert layer_type == "image"
    assert meta["channel_axis"] == 1
    assert meta["axis_labels"] == ("T", "Z", "Y", "X")
    assert meta["scale"] == [1.0, 2.0, 0.325, 0.325]
    assert meta.get("name") is None
    assert "colormap" not in meta
    assert data[0].shape == (1, 2, 1, 16, 16)


def test_rfc8_labels_open_as_an_image_layer(synthetic_screen):
    _, meta, layer_type = only_layer(synthetic_screen.labels)
    assert layer_type == "image"
    assert meta["channel_axis"] == 1


def test_rgba_overlay_opens_as_four_channels(synthetic_screen):
    data, meta, layer_type = only_layer(synthetic_screen.overlay)
    assert layer_type == "image"
    assert meta["channel_axis"] == 2
    assert data[0].shape == (16, 16, 4)


def test_raw_channel_opens_unnamed(synthetic_screen):
    _, meta, _ = only_layer(synthetic_screen.raw_channel_yx)
    assert meta["axis_labels"] == ("y", "x")
    assert meta["scale"] == [1.3, 1.3]
    assert "channel_axis" not in meta
    assert meta.get("name") is None

    _, meta, _ = only_layer(synthetic_screen.raw_channel_zyx)
    assert meta["axis_labels"] == ("z", "y", "x")
    assert meta["scale"] == [1.5, 0.325, 0.325]


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
    assert upstream_layers(merged) == []
    _, meta, layer_type = only_layer(merged / "image")
    assert (layer_type, meta["channel_axis"], meta["axis_labels"]) == ("image", 1, ("T", "Z", "Y", "X"))
    _, meta, layer_type = only_layer(merged / "cell_seg")
    assert (layer_type, meta["channel_axis"]) == ("image", 1)
    _, meta, layer_type = only_layer(merged / "grid_overlay")
    assert (layer_type, meta["channel_axis"]) == ("image", 2)


def test_raw_example_matches_synthetic_baseline(raw_example):
    tile = raw_example / "plate1_raw" / "A" / "1" / "iss" / "tiles" / "tile0"
    assert upstream_layers(raw_example) == []
    assert upstream_layers(tile) == []
    assert upstream_layers(tile / "round0") == []
    _, meta, _ = only_layer(tile / "round0" / "channel0")
    assert meta["axis_labels"] == ("y", "x")
    _, meta, _ = only_layer(raw_example / "plate1_raw" / "A" / "1" / "pheno" / "tiles" / "tile0" / "channel0")
    assert meta["axis_labels"] == ("z", "y", "x")
