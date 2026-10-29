"""A Qt-free tree of an sp-ops store, expanded one collection at a time."""

from dataclasses import dataclass, field

import zarr

from napari_sp_ops import nodes

UNOPENABLE_KINDS = {"table", "unknown"}


@dataclass
class TreeItem:
    """One node of the store with its kind, path and lazily loaded children."""

    node: nodes.Node
    kind: str
    _children: list["TreeItem"] | None = field(default=None, repr=False)

    @property
    def label(self) -> str:
        return self.node.name

    @property
    def path(self) -> str:
        return self.node.path

    @property
    def openable(self) -> bool:
        return self.kind not in UNOPENABLE_KINDS

    @property
    def is_leaf(self) -> bool:
        return self.kind in ("multiscale", "shapes", "points", "table", "unknown")

    @property
    def expanded(self) -> bool:
        return self._children is not None

    def expand(self) -> list["TreeItem"]:
        """Open the children once and cache them; leaves have none."""
        if self._children is None:
            self._children = [] if self.is_leaf else [TreeItem.from_node(child) for child in self.node.children()]
        return self._children

    @classmethod
    def from_node(cls, node: nodes.Node) -> "TreeItem":
        return cls(node, nodes.kind(node))


@dataclass
class StoreTree:
    """The tree rooted at whichever node a path points to."""

    root: TreeItem

    @classmethod
    def from_path(cls, path: str) -> "StoreTree":
        group = zarr.open_group(path, mode="r")
        return cls(TreeItem.from_node(nodes.Node(group, path)))

    def walk(self, depth: int) -> list[tuple[int, TreeItem]]:
        """Return items expanded down to ``depth`` levels, each with its level."""
        result: list[tuple[int, TreeItem]] = []

        def visit(item: TreeItem, level: int) -> None:
            result.append((level, item))
            if level < depth:
                for child in item.expand():
                    visit(child, level + 1)

        visit(self.root, 0)
        return result
