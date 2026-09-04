"""Collections open every image-like node beneath them with the per-kind rules of the plan."""

from pathlib import Path

import numpy as np
import pytest
from napari.components import ViewerModel
from npe2 import PluginManager

from napari_sp_ops.settings import Settings
from spops_store import ISS_LAYOUT


@pytest.fixture(scope="module", autouse=True)
def discover_plugins():
    PluginManager.instance().discover()


def open_layers(path: Path) -> list:
    return ViewerModel().open(str(path), plugin="napari-sp-ops")


def level0(layer) -> tuple[int, ...]:
    return layer.data[0].shape if layer.multiscale else layer.data.shape


def test_raw_tile_stacks_rounds_per_channel(synthetic_screen):
    layers = open_layers(synthetic_screen.raw_tile)
    assert [layer.name for layer in layers] == ["DAPI (unaligned)", "Cy3 (unaligned)"]
    for layer in layers:
        assert tuple(layer.axis_labels) == ("round", "y", "x")
        assert level0(layer) == (2, 16, 16)
        assert tuple(layer.scale) == (1.0, 1.3, 1.3)
        assert [entry["value"] for entry in layer.metadata["sp-ops"]["rounds"]] == [1, 2]


def test_raw_round_names_carry_index_and_cycle(synthetic_screen):
    layers = open_layers(synthetic_screen.raw_round)
    assert [layer.name for layer in layers] == ["round0 (cycle 1) DAPI", "round0 (cycle 1) Cy3"]
    assert all(level0(layer) == (16, 16) for layer in layers)


def test_tiles_place_each_tile_at_its_layout_corner(synthetic_screen):
    layers = open_layers(synthetic_screen.raw_tiles)
    assert [type(layer).__name__ for layer in layers] == ["Shapes"] + ["Image"] * 4
    layout = layers[0]
    assert layout.name == "layout"
    assert list(layout.features["tile"]) == [0, 1]
    assert len(layout.data) == 2
    for layer in layers[1:]:
        tile = layer.metadata["sp-ops"]["tile"]
        x_min, y_min = ISS_LAYOUT[tile][:2]
        assert layer.name.startswith(f"tile{tile} ")
        assert tuple(layer.translate) == (0.0, y_min, x_min)


def test_well_opens_every_modality_with_a_prefix(synthetic_screen):
    layers = open_layers(synthetic_screen.plate_raw / "A" / "1")
    names = [layer.name for layer in layers]
    assert names[:2] == ["iss layout", "iss tile0 DAPI (unaligned)"]
    assert names[-1] == "pheno tile0 AF750"
    assert len(layers) == 6


def test_merged_opens_image_hidden_labels_and_rgb(synthetic_screen):
    layers = open_layers(synthetic_screen.merged)
    assert [(type(layer).__name__, layer.name, layer.visible) for layer in layers] == [
        ("Image", "GFP", True),
        ("Image", "nuclei_prediction", True),
        ("Labels", "cells", False),
        ("Image", "overlay", True),
    ]
    assert layers[-1].rgb is True


def test_processed_merged_with_points(synthetic_screen):
    layers = open_layers(synthetic_screen.iss_image.parent)
    assert [type(layer).__name__ for layer in layers] == ["Image", "Image", "Points"]
    points = layers[-1]
    assert points.name == "reads"
    np.testing.assert_allclose(points.data, [[2.6, 1.3], [6.5, 13.0], [19.5, 20.8]])
    assert list(points.features["barcode"]) == ["b1", "b2", "b1"]


def test_screen_root_follows_the_stage_preference(synthetic_screen, monkeypatch):
    layers = open_layers(synthetic_screen.root)
    assert [layer.name for layer in layers][:3] == ["iss DAPI", "iss A", "iss reads"]
    assert len(layers) == 7
    monkeypatch.setenv("NAPARI_SP_OPS_STAGE", "raw")
    assert Settings.from_env().stage == "raw"
    raw_layers = open_layers(synthetic_screen.root)
    assert [layer.name for layer in raw_layers][:2] == ["iss layout", "iss tile0 DAPI (unaligned)"]


def test_layer_budget_stops_recursion_and_names_the_skipped(synthetic_screen, monkeypatch):
    monkeypatch.setenv("NAPARI_SP_OPS_LAYER_BUDGET", "3")
    with pytest.warns(UserWarning, match=r"stopped after 3 layers \(budget 3\); skipped overlay, cells_features"):
        layers = open_layers(synthetic_screen.merged)
    assert [layer.name for layer in layers] == ["GFP", "nuclei_prediction", "cells"]


def test_raw_example_collections(raw_example):
    well = raw_example / "plate1_raw" / "A" / "1"
    tile = open_layers(well / "iss" / "tiles" / "tile0")
    assert len(tile) == 5
    assert all(level0(layer) == (11, 1200, 1200) and tuple(layer.axis_labels) == ("round", "y", "x") for layer in tile)
    tiles = open_layers(well / "iss" / "tiles")
    assert [type(layer).__name__ for layer in tiles] == ["Shapes"] + ["Image"] * 10
    assert all(tuple(layer.scale)[1:] == (1.3, 1.3) for layer in tiles[1:])
    assert tuple(tiles[1].translate) != tuple(tiles[6].translate)
    whole_well = open_layers(well)
    assert len(whole_well) == 20
    pheno = [layer for layer in whole_well if layer.name.startswith("pheno tile")]
    assert len(pheno) == 8 and all(tuple(layer.scale) == (1.5, 0.325, 0.325) for layer in pheno)
    with pytest.warns(UserWarning, match="opens well A/1; the plate also has A/2"):
        assert len(open_layers(raw_example)) == 20


def test_processed_example_collections(processed_example):
    merged = open_layers(processed_example / "plate1_processed" / "A" / "1" / "pheno" / "merged")
    kinds = [type(layer).__name__ for layer in merged]
    assert kinds.count("Image") == 9 and kinds.count("Labels") == 12
    assert all(not layer.visible for layer in merged if type(layer).__name__ == "Labels")
    assert sum(getattr(layer, "rgb", False) for layer in merged) == 3
    assert len(open_layers(processed_example)) == len(merged)
