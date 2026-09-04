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
        if isinstance(member, zarr.Group):
            codes = np.asarray(member["codes"][:])
            categories = np.asarray(member["categories"][:])
            values = categories[np.where(codes >= 0, codes, 0)].astype(object)
            values[codes < 0] = None
            columns[name] = values
        else:
            columns[name] = np.asarray(member[:])
    return columns


def computed_edges(collection: nodes.Node) -> list[dict[str, Any]]:
    edges = collection.attributes.get("sp-ops:relationships", {}).get("edges", [])
    return [edge for edge in edges if edge.get("status") == "computed" and isinstance(edge.get("on"), dict)]


def table_for_labels(collection: nodes.Node, labels_name: str) -> tuple[str, str] | None:
    """Return the table's path relative to the collection and its label column, from a computed key edge."""
    for edge in computed_edges(collection):
        on = edge["on"]
        endpoints = {"from": (edge.get("from"), on.get("left")), "to": (edge.get("to"), on.get("right"))}
        for side, (name, key) in endpoints.items():
            other_name, other_key = endpoints["to" if side == "from" else "from"]
            if name == labels_name and key in LABEL_KEYS and other_name and other_key:
                return other_name, other_key
    return None


def open_table(collection: nodes.Node, relative: str) -> zarr.Group:
    """Open a table through the collection's store, so credentials and store type carry over."""
    inside = posixpath.normpath(posixpath.join(collection.group.path or ".", relative))
    return zarr.open_group(store=collection.group.store, path="" if inside == "." else inside, mode="r")


def label_features(collection: nodes.Node, labels_name: str) -> dict[str, np.ndarray] | None:
    """Return napari label features, with ``index`` as the label value, or ``None`` without a computed edge."""
    match = table_for_labels(collection, labels_name)
    if match is None:
        return None
    relative, key = match
    try:
        columns = read_obs(open_table(collection, relative))
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
