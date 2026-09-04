"""Leaf multiscale nodes open with sp-ops names, colormaps, squeezed axes and placement."""

from pathlib import Path

import numpy as np
import pytest
import zarr
from napari.components import ViewerModel
from npe2 import PluginManager

from napari_sp_ops import rfc8
from napari_sp_ops.channels import Channel, colormaps, parse_channels
from spops_store import YX, write_plain_multiscale


@pytest.fixture(scope="module", autouse=True)
def discover_plugins():
    PluginManager.instance().discover()


def open_layers(path: Path) -> list:
    return ViewerModel().open(str(path), plugin="napari-sp-ops")


def full_resolution(layer) -> tuple[int, ...]:
    """Shape of level 0; a one-level pyramid is stored by napari as a plain array."""
    return layer.data[0].shape if layer.multiscale else layer.data.shape


def test_image_splits_into_named_channels_without_singleton_sliders(synthetic_screen):
    layers = open_layers(synthetic_screen.image)
    assert [layer.name for layer in layers] == ["GFP", "nuclei_prediction"]
    assert [layer.colormap.name for layer in layers] == ["green", "gray"]
    for layer in layers:
        assert type(layer).__name__ == "Image"
        assert tuple(layer.axis_labels) == ("y", "x")
        assert full_resolution(layer) == (16, 16)
        assert tuple(layer.scale) == (0.325, 0.325)
        assert tuple(layer.translate) == (15600.0, 15600.0)
        assert layer.units == ("micrometer", "micrometer")
        assert layer.metadata["sp-ops"]["channel"]["name"] == layer.name


def test_rfc8_labels_open_hidden_at_their_own_scale(synthetic_screen):
    (layer,) = open_layers(synthetic_screen.labels)
    assert type(layer).__name__ == "Labels"
    assert layer.name == "cells"
    assert layer.visible is False
    assert full_resolution(layer) == (16, 16)
    assert tuple(layer.scale) == (0.65, 0.65)
    assert tuple(layer.translate) == (15600.0, 15600.0)
    assert layer.metadata["sp-ops"]["label_kind"] == "biological"


def test_rgba_raster_opens_as_one_rgb_layer(synthetic_screen):
    (layer,) = open_layers(synthetic_screen.overlay)
    assert type(layer).__name__ == "Image"
    assert layer.rgb is True
    assert layer.name == "overlay"
    assert full_resolution(layer) == (16, 16, 4)
    assert tuple(layer.axis_labels) == ("y", "x")


@pytest.mark.parametrize(
    ("attribute", "name", "colormap", "axis_labels", "scale"),
    [
        ("raw_channel_yx", "DAPI", "blue", ("y", "x"), (1.3, 1.3)),
        ("raw_channel_zyx", "AF750", "green", ("z", "y", "x"), (1.5, 0.325, 0.325)),
    ],
)
def test_raw_channel_takes_its_channel_name(synthetic_screen, attribute, name, colormap, axis_labels, scale):
    (layer,) = open_layers(getattr(synthetic_screen, attribute))
    assert layer.name == name
    assert layer.colormap.name == colormap
    assert tuple(layer.axis_labels) == axis_labels
    assert tuple(layer.scale) == scale


def test_round_axis_becomes_a_slider(synthetic_screen):
    layers = open_layers(synthetic_screen.iss_image)
    assert [layer.name for layer in layers] == ["DAPI", "A"]
    assert [layer.colormap.name for layer in layers] == ["blue", "green"]
    for layer in layers:
        assert tuple(layer.axis_labels) == ("round", "y", "x")
        assert full_resolution(layer) == (2, 16, 16)
        assert tuple(layer.scale) == (1.0, 1.3, 1.3)


def test_plain_ome_zarr_is_delegated_to_napari_ome_zarr(tmp_path):
    image = tmp_path / "plain.zarr"
    write_plain_multiscale(image, np.zeros((8, 8), dtype=np.uint16), YX, [2.0, 2.0])
    group = zarr.open_group(str(image), mode="r")
    assert rfc8.inside_sp_ops_store(group, str(image)) is False
    (layer,) = open_layers(image)
    assert layer.name == "plain"
    assert tuple(layer.scale) == (2.0, 2.0)


def test_detection_walks_up_past_metadata_less_directories(synthetic_screen):
    """A plain image placed inside the store is claimed because an ancestor is a collection."""
    image = synthetic_screen.plate_processed / "A" / "1" / "pheno" / "merged" / "plain"
    write_plain_multiscale(image, np.zeros((8, 8), dtype=np.uint16), YX, [2.0, 2.0])
    group = zarr.open_group(str(image), mode="r")
    assert rfc8.inside_sp_ops_store(group, str(image)) is True
    assert rfc8.parent_path("https://host/bucket/screen.zarr") == "https://host/bucket"
    assert rfc8.parent_path("https://host") is None
    assert rfc8.parent_path("/screen.zarr") is None


def test_channel_palette_by_role():
    channels = [
        Channel("DAPI", "nuclear"),
        Channel("A", "base"),
        Channel("G", "base"),
        Channel("C", "base"),
        Channel("T", "base"),
        Channel("GFP", "stain"),
        Channel("mCherry", "stain"),
        Channel("Phase", "other", "labelfree"),
        Channel("fake", "stain", "predicted"),
    ]
    assert colormaps(channels) == ["blue", "green", "red", "magenta", "cyan", "green", "magenta", "gray", "gray"]
    padded = parse_channels({"sp-ops:channels": [{"name": None, "role": "base"}]}, 2)
    assert [channel.name for channel in padded] == ["channel0", "channel1"]
    per_round = parse_channels({"sp-ops:channels": [[{"name": "DAPI", "role": "nuclear"}], [{"name": "GFP", "role": "stain"}]]}, 1)
    assert per_round[0].name == "DAPI"


def test_processed_example_leaves(processed_example):
    merged = processed_example / "plate1_processed" / "A" / "1" / "pheno" / "merged"
    layers = open_layers(merged / "image")
    assert [layer.name for layer in layers] == ["Phase2D", "Focus3D", "GFP", "mCherry", "nuclei_prediction", "membrane_prediction"]
    assert [layer.colormap.name for layer in layers] == ["gray", "gray", "green", "magenta", "gray", "gray"]
    assert all(layer.ndim == 2 and tuple(layer.translate) == (15600.0, 15600.0) for layer in layers)
    (labels,) = open_layers(merged / "cell_seg")
    assert (type(labels).__name__, labels.visible, tuple(labels.scale)) == ("Labels", False, (0.65, 0.65))
    (overlay,) = open_layers(merged / "grid_overlay")
    assert overlay.rgb is True and overlay.ndim == 2


def test_raw_example_leaves(raw_example):
    well = raw_example / "plate1_raw" / "A" / "1"
    (layer,) = open_layers(well / "iss" / "tiles" / "tile0" / "round0" / "channel4")
    assert (layer.name, layer.colormap.name, tuple(layer.scale)) == ("DAPI_SBS", "blue", (1.3, 1.3))
    (layer,) = open_layers(well / "pheno" / "tiles" / "tile0" / "channel0")
    assert (layer.name, tuple(layer.axis_labels)) == ("AF750", ("z", "y", "x"))
