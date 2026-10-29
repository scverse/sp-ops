"""Feed a labels layer's ``features`` from a table joined to it by a computed edge."""

import posixpath
import warnings
from typing import Any

import numpy as np
import zarr

from napari_sp_ops import nodes

LABEL_KEYS = {"value", "label"}
MAX_ROWS = 2_000_000


def read_obs(table: zarr.Group) -> dict[str, np.ndarray]:
    """Return the ``obs`` columns of an AnnData zarr group as numpy arrays.

    Handles the AnnData encodings a cell table uses: plain arrays, string
    arrays and categoricals stored as ``codes`` plus ``categories``.
    """
    obs = table["obs"]
    attributes = dict(obs.attrs)
    members = list(obs.keys())
    names = list(attributes.get("column-order", [])) or [name for name in members if name != attributes.get("_index")]
    columns: dict[str, np.ndarray] = {}
    for name in names:
        member = obs[name]
        if not isinstance(member, zarr.Group):
            columns[name] = np.asarray(member[:])
        elif "codes" in member:
            codes = np.asarray(member["codes"][:])
            categories = np.asarray(member["categories"][:])
            values = categories[np.where(codes >= 0, codes, 0)].astype(object)
            values[codes < 0] = None
            columns[name] = values
        elif "values" in member:
            values = np.asarray(member["values"][:]).astype(object)
            if "mask" in member:
                values[np.asarray(member["mask"][:], dtype=bool)] = None
            columns[name] = values
        else:
            warnings.warn(f"napari-sp-ops skips obs column {name!r}: unknown encoding", stacklevel=2)
    return columns


def computed_edges(collection: nodes.Node) -> list[dict[str, Any]]:
    edges = collection.attributes.get("sp-ops:relationships", {}).get("edges", [])
    return [edge for edge in edges if edge.get("status") == "computed" and isinstance(edge.get("on"), dict)]


def tables_for_labels(collection: nodes.Node, labels_name: str) -> list[tuple[str, str]]:
    """Every ``(table path relative to the collection, label column)`` a computed key edge joins to the labels node."""
    matches: list[tuple[str, str]] = []
    for edge in computed_edges(collection):
        on = edge["on"]
        endpoints = {"from": (edge.get("from"), on.get("left")), "to": (edge.get("to"), on.get("right"))}
        for side, (name, key) in endpoints.items():
            other_name, other_key = endpoints["to" if side == "from" else "from"]
            if name == labels_name and key in LABEL_KEYS and other_name and other_key:
                matches.append((other_name, other_key))
    return matches


def table_for_labels(collection: nodes.Node, labels_name: str) -> tuple[str, str] | None:
    """The first table a computed key edge joins to the labels node, or ``None``."""
    matches = tables_for_labels(collection, labels_name)
    return matches[0] if matches else None


def open_table(collection: nodes.Node, relative: str) -> zarr.Group:
    """Open a table through the collection's store, so credentials and store type carry over."""
    inside = posixpath.normpath(posixpath.join(collection.group.path or ".", relative))
    return zarr.open_group(store=collection.group.store, path="" if inside == "." else inside, mode="r")


def label_features(ancestors: list[tuple[nodes.Node, str]]) -> dict[str, np.ndarray] | None:
    """Return napari label features for a labels node, from the nearest ancestor collection with a computed edge to it.

    ``ancestors`` pairs each collection above the node with the node's path
    relative to it, nearest collection last. The result has ``index`` as the
    label value, or is ``None`` when no edge matches.
    """
    for collection, labels_name in reversed(ancestors):
        for relative, key in tables_for_labels(collection, labels_name):
            result = _features_from_table(collection, labels_name, relative, key)
            if result is not None:
                return result
    return None


def _features_from_table(collection: nodes.Node, labels_name: str, relative: str, key: str) -> dict[str, np.ndarray] | None:
    """Features from one edge endpoint; a points or shapes endpoint has no ``obs`` and is skipped quietly."""
    try:
        table = open_table(collection, relative)
    except Exception as exc:
        warnings.warn(f"napari-sp-ops could not open {relative} for {labels_name}: {exc}", stacklevel=2)
        return None
    if "obs" not in table:
        return None
    try:
        columns = read_obs(table)
    except Exception as exc:
        warnings.warn(f"napari-sp-ops could not read the table {relative} for {labels_name}: {exc}", stacklevel=2)
        return None
    if key not in columns:
        warnings.warn(f"napari-sp-ops found no column {key!r} in {relative}", stacklevel=2)
        return None
    if len(columns[key]) > MAX_ROWS:
        warnings.warn(f"napari-sp-ops skips features for {labels_name}: {len(columns[key])} rows exceed {MAX_ROWS}", stacklevel=2)
        return None
    index = np.asarray(columns.pop(key)).astype(np.int64)
    return {"index": index, **columns}
