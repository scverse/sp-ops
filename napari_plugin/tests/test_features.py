"""Labels layers take their features from a table joined by a computed edge."""

import numpy as np
import pytest
import zarr
from napari.components import ViewerModel
from npe2 import PluginManager

from napari_sp_ops import features, nodes


@pytest.fixture(scope="module", autouse=True)
def discover_plugins():
    PluginManager.instance().discover()


def test_obs_reader_decodes_arrays_strings_and_categoricals(synthetic_screen):
    columns = features.read_obs(zarr.open_group(str(synthetic_screen.table), mode="r"))
    assert list(columns) == ["label", "area", "barcode", "gene"]
    assert columns["label"].tolist() == [1, 2, 3, 4]
    assert columns["barcode"].tolist() == ["ACGT", "TTGA", "ACGT", None]


def test_edge_lookup_finds_the_table_and_its_label_column(synthetic_screen):
    merged = nodes.Node(zarr.open_group(str(synthetic_screen.merged), mode="r"), str(synthetic_screen.merged))
    assert features.table_for_labels(merged, "cells") == ("cells_features", "label")
    assert features.table_for_labels(merged, "overlay") is None


def test_labels_layer_carries_table_features(synthetic_screen):
    layers = ViewerModel().open(str(synthetic_screen.merged), plugin="napari-sp-ops")
    (cells,) = [layer for layer in layers if type(layer).__name__ == "Labels"]
    assert list(cells.features.columns) == ["index", "area", "barcode", "gene"]
    assert cells.features["index"].tolist() == [1, 2, 3, 4]
    assert cells._label_index == {1: 0, 2: 1, 3: 2, 4: 3}
    assert sum(getattr(layer, "rgb", False) for layer in layers) == 1


def test_image_contrast_limits_come_from_the_lowest_level(synthetic_screen):
    layers = ViewerModel().open(str(synthetic_screen.image), plugin="napari-sp-ops")
    for layer in layers:
        low, high = layer.contrast_limits
        data = layer.data[-1] if layer.multiscale else layer.data
        assert 0.0 <= low < high <= 1.0
        assert low == pytest.approx(np.percentile(np.asarray(data), 1.0))


def test_processed_example_table_reads_through_zarr(processed_example):
    table = processed_example / "plate1_processed" / "A" / "1" / "pheno" / "merged" / "cells_features"
    columns = features.read_obs(zarr.open_group(str(table), mode="r"))
    assert set(columns) >= {"barcode", "tile", "cell_uid"}
    assert columns["barcode"].dtype == object
    assert len(columns["tile"]) == 267449
    merged = nodes.Node(zarr.open_group(str(table.parent), mode="r"), str(table.parent))
    assert features.table_for_labels(merged, "cell_seg") is None, "the example edge is a suggested spatial join"
