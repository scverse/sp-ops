"""``omero`` colors and windows override the role palette, and image layers blend additively."""

from pathlib import Path

import numpy as np
import pytest
import zarr
from napari.components import ViewerModel
from npe2 import PluginManager

from napari_sp_ops import rendering
from spops_store import YX, write_multiscale

CYX = [{"name": "c", "type": "channel"}, *YX]


@pytest.fixture(scope="module", autouse=True)
def discover_plugins():
    PluginManager.instance().discover()


def open_layers(path: Path) -> list:
    return ViewerModel().open(str(path), plugin="napari-sp-ops")


def _channel(color: str | None, window: tuple[float, float] | None) -> dict:
    entry: dict = {"active": True}
    if color is not None:
        entry["color"] = color
    if window is not None:
        entry["window"] = {"start": window[0], "end": window[1], "min": 0.0, "max": 65535.0}
    return entry


def test_omero_overrides_role_colormap_and_window_per_channel(tmp_path):
    """A stain that the palette would paint green takes its omero color; a channel without a window keeps the estimate."""
    store = tmp_path / "image.zarr"
    attrs = {"sp-ops:channels": [{"name": "AF750", "role": "stain"}, {"name": "GFP", "role": "stain"}, {"name": "DAPI", "role": "nuclear"}]}
    omero = {"version": "0.5", "channels": [_channel("FF00FF", (100.0, 900.0)), _channel("00ff00", None), _channel(None, (50.0, 3000.0))]}
    data = np.random.default_rng(0).integers(0, 4000, (3, 16, 16), dtype=np.uint16)
    write_multiscale(store, data, CYX, [1.0, 1.0, 1.0], attrs, "px", omero=omero)
    layers = open_layers(store)
    assert [layer.name for layer in layers] == ["AF750", "GFP", "DAPI"]
    assert [layer.colormap.name for layer in layers] == ["magenta", "green", "blue"]
    assert layers[0].contrast_limits == [100.0, 900.0]
    assert layers[2].contrast_limits == [50.0, 3000.0]
    assert layers[1].contrast_limits[0] == pytest.approx(np.percentile(data[1], 1.0))
    assert {layer.blending for layer in layers} == {"additive"}


def test_single_channel_node_takes_its_omero_hints(tmp_path):
    store = tmp_path / "channel0"
    attrs = {"sp-ops:axis": {"name": "c", "index": 1}, "sp-ops:channels": [{"name": "Cy5", "role": "base"}]}
    omero = {"version": "0.5", "channels": [_channel("FF0000", (500.0, 4000.0))]}
    write_multiscale(store, np.zeros((16, 16), dtype=np.uint16), YX, [1.3, 1.3], attrs, "px", omero=omero)
    (layer,) = open_layers(store)
    assert (layer.name, layer.colormap.name, layer.contrast_limits, layer.blending) == ("Cy5", "red", [500.0, 4000.0], "additive")


def test_images_blend_additively_and_labels_and_rgb_keep_their_defaults(synthetic_screen):
    images = open_layers(synthetic_screen.image)
    assert {layer.blending for layer in images} == {"additive"}
    (labels,) = open_layers(synthetic_screen.labels)
    assert labels.blending == "translucent"
    (overlay,) = open_layers(synthetic_screen.overlay)
    assert overlay.rgb is True and overlay.blending == "translucent_no_depth"


def test_malformed_omero_entries_are_ignored(tmp_path):
    store = tmp_path / "bad"
    omero = {"version": "0.5", "channels": [{"color": "green", "window": {"start": 5, "end": 1}}, "not a dict", {"window": {"start": "a"}}]}
    write_multiscale(store, np.zeros((16, 16), dtype=np.uint16), YX, [1.0, 1.0], {"sp-ops:channels": []}, "px", omero=omero)
    hints = rendering.parse_omero(zarr.open_group(str(store), mode="r"))
    assert hints == [rendering.Rendering(), rendering.Rendering(), rendering.Rendering()]
    plain = zarr.open_group(str(tmp_path / "plain"), mode="w")
    assert rendering.parse_omero(plain) == []
    colormaps, limits = rendering.apply([rendering.Rendering("#FF0000", (1.0, 2.0))], ["gray", "gray"], None)
    assert (colormaps, limits) == (["#FF0000", "gray"], [[1.0, 2.0], None])
