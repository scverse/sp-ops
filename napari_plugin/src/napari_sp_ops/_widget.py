"""A dock widget that shows an sp-ops store as a tree and adds checked nodes to the viewer."""

import warnings

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from napari_sp_ops.navigator import StoreTree, TreeItem

PLUGIN_NAME = "napari-sp-ops"
ITEM_ROLE = Qt.ItemDataRole.UserRole


class SpOpsNavigator(QWidget):
    """Browse the stages, plates, wells, modalities and tiles of a store and open a selection."""

    def __init__(self, napari_viewer) -> None:
        super().__init__()
        self.viewer = napari_viewer
        self.tree_model: StoreTree | None = None

        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText("Path or URL of an sp-ops store or any node in it")
        self.path_edit.setText(self._path_from_layers())
        self.load_button = QPushButton("Load", self)
        self.load_button.clicked.connect(self.load)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["node", "kind"])
        self.tree.itemExpanded.connect(self._fill_children)

        self.add_button = QPushButton("Add selected", self)
        self.add_button.clicked.connect(self.add_selected)

        header = QHBoxLayout()
        header.addWidget(self.path_edit)
        header.addWidget(self.load_button)
        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.tree)
        layout.addWidget(self.add_button)

    def _path_from_layers(self) -> str:
        for layer in self.viewer.layers:
            path = layer.metadata.get("sp-ops", {}).get("path")
            if path:
                return str(path)
        return ""

    def load(self) -> None:
        """Open the path in the text field and show its node as the tree root."""
        path = self.path_edit.text().strip()
        if not path:
            return
        try:
            self.tree_model = StoreTree.from_path(path)
        except Exception as exc:
            warnings.warn(f"napari-sp-ops could not open {path}: {exc}", stacklevel=2)
            return
        self.tree.clear()
        root = self._make_item(self.tree_model.root)
        self.tree.addTopLevelItem(root)
        self._fill_children(root)
        root.setExpanded(True)

    def _make_item(self, item: TreeItem) -> QTreeWidgetItem:
        widget_item = QTreeWidgetItem([item.label, item.kind])
        widget_item.setData(0, ITEM_ROLE, item)
        if item.openable:
            widget_item.setFlags(widget_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            widget_item.setCheckState(0, Qt.CheckState.Unchecked)
        else:
            widget_item.setFlags(widget_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        if not item.is_leaf:
            widget_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        return widget_item

    def _fill_children(self, widget_item: QTreeWidgetItem) -> None:
        item: TreeItem = widget_item.data(0, ITEM_ROLE)
        if item is None or item.expanded:
            return
        for child in item.expand():
            widget_item.addChild(self._make_item(child))
        widget_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicatorWhenChildless)

    def checked_items(self) -> list[TreeItem]:
        """Every checked, openable node currently shown in the tree."""
        checked: list[TreeItem] = []

        def visit(widget_item: QTreeWidgetItem) -> None:
            item: TreeItem = widget_item.data(0, ITEM_ROLE)
            if item is not None and item.openable and widget_item.checkState(0) == Qt.CheckState.Checked:
                checked.append(item)
            for index in range(widget_item.childCount()):
                visit(widget_item.child(index))

        for index in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(index))
        return checked

    def add_selected(self) -> None:
        """Open every checked node through the sp-ops reader and uncheck it."""
        for item in self.checked_items():
            self.viewer.open(item.path, plugin=PLUGIN_NAME)
        self._uncheck_all()

    def _uncheck_all(self) -> None:
        def visit(widget_item: QTreeWidgetItem) -> None:
            if widget_item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                widget_item.setCheckState(0, Qt.CheckState.Unchecked)
            for index in range(widget_item.childCount()):
                visit(widget_item.child(index))

        for index in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(index))
