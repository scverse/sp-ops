"""Stores written in the RFC-8 singlescale form with a well-level scene open like the others."""

import os
from pathlib import Path

import pytest
import zarr
from napari.components import ViewerModel
from npe2 import PluginManager

from napari_sp_ops import features, rfc8


@pytest.fixture(scope="module", autouse=True)
def discover_plugins():
    PluginManager.instance().discover()


def open_layers(path: Path) -> list:
    return ViewerModel().open(str(path), plugin="napari-sp-ops")


def test_singlescale_levels_and_axes_are_read(synthetic_screen):
    group = zarr.open_group(str(synthetic_screen.iss_image), mode="r")
    assert rfc8.is_multiscale(group)
    assert [path for path, _ in rfc8.multiscale_levels(group)] == ["0", "1"]
    assert [axis.name for axis in rfc8.multiscale_axes(group)] == ["round", "c", "y", "x"]
    assert rfc8.dataset_transforms(group)[0]["scale"] == [1.0, 1.0, 1.3, 1.3]


def test_scene_translation_on_the_well_places_the_image(synthetic_screen):
    layers = open_layers(synthetic_screen.well)
    iss = [layer for layer in layers if layer.name.startswith("iss ") and type(layer).__name__ == "Image"]
    assert [layer.name for layer in iss] == ["iss DAPI", "iss A"]
    for layer in iss:
        assert layer.multiscale and layer.data[1].shape == (2, 8, 8)
        assert tuple(layer.scale) == (1.0, 1.3, 1.3)
        assert tuple(layer.translate) == (0.0, 100.0, 200.0)
    (reads,) = [layer for layer in layers if type(layer).__name__ == "Points"]
    assert tuple(reads.scale) == (1.3, 1.3) and tuple(reads.translate) == (100.0, 200.0)
    direct = open_layers(synthetic_screen.iss_image)
    assert tuple(direct[0].translate) == (0.0, 0.0, 0.0), "dropped alone, the image has no ancestor scene"


def test_nullable_obs_column_decodes(synthetic_screen):
    columns = features.read_obs(zarr.open_group(str(synthetic_screen.table), mode="r"))
    assert columns["gene"].tolist() == ["A", "B", None, "D"]
    layers = open_layers(synthetic_screen.merged)
    (cells,) = [layer for layer in layers if type(layer).__name__ == "Labels"]
    assert list(cells.features.columns) == ["index", "area", "barcode", "gene"]


def _collaborator_stores() -> Path:
    value = os.environ.get("SP_OPS_OME_ZARR_PY_STORES")
    if not value:
        pytest.skip("SP_OPS_OME_ZARR_PY_STORES is not set")
    return Path(value).expanduser()


def test_collaborator_biohub_store():
    root = _collaborator_stores() / "biohub_example" / "biohub_example.zarr"
    layers = open_layers(root)
    kinds = [type(layer).__name__ for layer in layers]
    assert kinds.count("Labels") == 12 and kinds.count("Image") == 9
    assert all(tuple(layer.translate) == (15600.0, 15600.0) for layer in layers)
    (cell_seg,) = [layer for layer in layers if layer.name == "pheno cell_seg"]
    assert "barcode" in cell_seg.features.columns


def test_collaborator_scallops_store():
    root = _collaborator_stores() / "experimentC_scallops" / "experimentC_scallops.zarr"
    layers = open_layers(root)
    names = [layer.name for layer in layers]
    assert names[:5] == ["iss DAPI", "iss G", "iss T", "iss A", "iss C"]
    assert all(tuple(layer.axis_labels) == ("round", "y", "x") and layer.data[0].shape[0] == 9 for layer in layers[:5])
    points = [layer for layer in layers if type(layer).__name__ == "Points"]
    assert [layer.name for layer in points] == ["iss peaks", "iss reads"]
    assert all(tuple(layer.scale) == (1.32, 1.32) for layer in points)
    labels = {layer.name: layer for layer in layers if type(layer).__name__ == "Labels"}
    assert set(labels) == {"pheno nuclei", "pheno cells", "pheno cytosol", "pheno nuclei_unfiltered", "pheno cells_unfiltered"}
    assert labels["pheno cells"].features.shape[1] > 1
