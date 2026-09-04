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
    assert [type(layer).__name__ for layer in layers] == ["Image", "Image"]
    for layer in layers:
        assert tuple(layer.axis_labels) == ("T", "Z", "Y", "X")
        assert tuple(layer.scale) == (1.0, 2.0, 0.325, 0.325)
        assert layer.data[0].shape == (1, 16, 16)


def test_napari_reports_no_data_for_a_collection(synthetic_screen):
    with pytest.raises(ValueError, match="returned no data"):
        ViewerModel().open(str(synthetic_screen.merged), plugin="napari-sp-ops")


def test_declines_a_directory_without_zarr_metadata(tmp_path):
    """napari rejects missing paths itself; a directory with no zarr.json is what reaches the reader."""
    with pytest.warns(UserWarning, match="could not open"):
        assert napari_get_reader(str(tmp_path)) is None
