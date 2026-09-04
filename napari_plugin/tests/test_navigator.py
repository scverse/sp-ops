"""The store tree expands one collection at a time and the dock widget opens what is checked."""

import os

import pytest
import zarr

from napari_sp_ops import nodes
from napari_sp_ops.navigator import StoreTree, TreeItem


def find(items: list[TreeItem], label: str) -> TreeItem:
    return next(item for item in items if item.label == label)


def test_root_lists_plates_and_expands_lazily(synthetic_screen):
    tree = StoreTree.from_path(str(synthetic_screen.root))
    assert tree.root.kind == "screen"
    assert tree.root.expanded is False
    plates = tree.root.expand()
    assert [(item.label, item.kind) for item in plates] == [("plate1_processed", "plate"), ("plate1_raw", "plate")]
    assert tree.root.expanded is True
    assert all(not plate.expanded for plate in plates)
    assert tree.root.expand() is plates


def test_well_children_are_modalities(synthetic_screen):
    tree = StoreTree.from_path(str(synthetic_screen.well))
    assert tree.root.kind == "well"
    assert [(item.label, item.kind) for item in tree.root.expand()] == [("iss", "modality"), ("pheno", "modality")]


def test_merged_children_kinds_and_table_is_not_openable(synthetic_screen):
    pheno = StoreTree.from_path(str(synthetic_screen.merged)).root
    kinds = {item.label: item.kind for item in pheno.expand()}
    assert kinds == {"image": "multiscale", "cells": "multiscale", "overlay": "multiscale", "cells_features": "table"}
    assert all(item.is_leaf and item.expand() == [] for item in pheno.expand())
    assert [item.label for item in pheno.expand() if not item.openable] == ["cells_features"]

    iss = StoreTree.from_path(str(synthetic_screen.iss_image.parent)).root
    assert find(iss.expand(), "reads").kind == "points"

    table = TreeItem.from_node(nodes.Node(zarr.open_group(str(synthetic_screen.table), mode="r"), str(synthetic_screen.table)))
    assert table.kind == "table"
    assert table.openable is False


def test_walk_returns_levels_down_to_depth(synthetic_screen):
    tree = StoreTree.from_path(str(synthetic_screen.plate_raw))
    levels = tree.walk(depth=2)
    assert [(level, item.kind) for level, item in levels] == [(0, "plate"), (1, "well"), (2, "modality"), (2, "modality")]


def test_widget_loads_a_store_and_adds_checked_nodes(synthetic_screen):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("qtpy")
    from napari.components import ViewerModel
    from npe2 import PluginManager
    from qtpy.QtCore import Qt
    from qtpy.QtWidgets import QApplication

    from napari_sp_ops._widget import SpOpsNavigator

    PluginManager.instance().discover()
    app = QApplication.instance() or QApplication([])
    viewer = ViewerModel()
    widget = SpOpsNavigator(viewer)
    widget.path_edit.setText(str(synthetic_screen.root))
    widget.load()
    root = widget.tree.topLevelItem(0)
    assert root.text(0) == "screen.zarr"
    assert root.childCount() == 2
    plate = root.child(0)
    assert plate.text(1) == "plate"
    assert plate.childCount() == 0
    plate.setCheckState(0, Qt.CheckState.Checked)
    assert [item.label for item in widget.checked_items()] == ["plate1_processed"]
    widget.add_selected()
    assert len(viewer.layers) > 0
    assert widget.checked_items() == []
    widget.tree.expandItem(plate)
    assert plate.childCount() == 1
    app.processEvents()
