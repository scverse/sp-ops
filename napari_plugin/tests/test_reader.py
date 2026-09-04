"""Open the synthetic screen through napari's Qt-free viewer model.

``ViewerModel.open(..., plugin="napari-sp-ops")`` exercises the manifest, the
reader entry point, and napari's layer construction in one call.
"""

import pytest
from napari.components import ViewerModel
from npe2 import PluginManager

from napari_sp_ops import napari_get_reader


@pytest.fixture(scope="module", autouse=True)
def discover_plugins():
    PluginManager.instance().discover()


def test_napari_opens_a_multiscale_through_the_plugin(synthetic_screen):
    viewer = ViewerModel()
    layers = viewer.open(str(synthetic_screen.image), plugin="napari-sp-ops")
    assert [(type(layer).__name__, layer.name) for layer in layers] == [("Image", "GFP"), ("Image", "nuclei_prediction")]


def test_napari_reports_no_data_for_a_table(synthetic_screen):
    """A table has no napari layer type, so dropping one directly yields napari's no-data error."""
    from spops_store import write_element_group

    table = synthetic_screen.merged / "cells_features"
    write_element_group(table, "table")
    with pytest.raises(ValueError, match="returned no data"):
        ViewerModel().open(str(table), plugin="napari-sp-ops")


def test_declines_a_directory_without_zarr_metadata(tmp_path):
    """napari rejects missing paths itself; a directory with no zarr.json is what reaches the reader."""
    with pytest.warns(UserWarning, match="could not open"):
        assert napari_get_reader(str(tmp_path)) is None
    with pytest.warns(UserWarning, match="could not open"):
        assert napari_get_reader([str(tmp_path)]) is None
    assert napari_get_reader([]) is None
