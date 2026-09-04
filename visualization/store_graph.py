"""Walk an sp-ops-conformant OME-Zarr store and build two graphs from its metadata:

- the **relationships graph**: the `sp-ops:relationships` edges declared on every
  collection (see docs/extension.md and docs/joinable-components.md).
- the **transformations graph**: the coordinate transformations that place an element
  into a shared coordinate system -- the group-level `scene` attribute RFC-5 describes
  (docs/layout.md#registration), and, since no store here writes `scene` yet, the
  per-multiscale `coordinateSystems` + base-level `coordinateTransformations` every
  image and labels node already carries.

Reads `zarr.json` files directly with the standard library -- no zarr/ome-zarr/spatialdata
dependency, so this works against any conformant store without an environment able to open
the arrays themselves.
"""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

# Node "kind" values used as the `kind` attribute on graph nodes, for styling.
COLLECTION = "collection"
MULTISCALE = "multiscale"
TABLE = "sp-ops:table"
SHAPES = "sp-ops:shapes"
POINTS = "sp-ops:points"
COORDINATE_SYSTEM = "coordinateSystem"
DANGLING = "dangling"

_LEAF_TYPES = {TABLE, SHAPES, POINTS}


@dataclass
class Node:
    """One node of the RFC-8 tree, keyed by its POSIX path relative to the store root."""

    path: str
    type: str
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    multiscales: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StoreTree:
    root: Path
    nodes: dict[str, Node]
    ids: dict[str, str]  # sp-ops/RFC-8 node "id" -> canonical path


def _read_ome(group_dir: Path) -> dict[str, Any]:
    zarr_json = group_dir / "zarr.json"
    payload = json.loads(zarr_json.read_text())
    return payload["attributes"]["ome"]


def walk_store(store_root: Path) -> StoreTree:
    """Recurse from the store root, following each collection's `nodes` list.

    Leaf elements (`sp-ops:table`/`sp-ops:shapes`/`sp-ops:points`) are recorded but not
    opened: `sp-ops:relationships` and `scene` are only ever attached to a collection
    (docs/extension.md), so there is nothing more to read from a leaf's own metadata for
    either graph built here.
    """
    nodes: dict[str, Node] = {}
    ids: dict[str, str] = {}

    def visit_collection(dir_path: Path, rel: str, name: str) -> None:
        ome = _read_ome(dir_path)
        nodes[rel] = Node(rel, ome["type"], name, ome.get("attributes", {}) or {})
        for child in ome.get("nodes", []):
            child_rel_str = child["path"]["path"]
            child_rel = posixpath.normpath(posixpath.join(rel, child_rel_str))
            child_dir = dir_path / child_rel_str
            child_name = child.get("name", child_rel)
            child_id = child.get("id")
            if child_id:
                ids[child_id] = child_rel
            ctype = child["type"]
            if ctype == COLLECTION:
                visit_collection(child_dir, child_rel, child_name)
            elif ctype == MULTISCALE:
                visit_multiscale(child_dir, child_rel, child_name)
            else:
                # Leaf types (sp-ops:table/shapes/points): the parent descriptor is all
                # there is to know for either graph, so nothing more to open.
                nodes[child_rel] = Node(child_rel, ctype, child_name)

    def visit_multiscale(dir_path: Path, rel: str, name: str) -> None:
        ome = _read_ome(dir_path)
        nodes[rel] = Node(
            rel,
            MULTISCALE,
            name,
            ome.get("attributes", {}) or {},
            ome.get("multiscales", []) or [],
        )

    visit_collection(store_root, "", "screen")
    return StoreTree(store_root, nodes, ids)


def drop_isolated_nodes(g: nx.DiGraph) -> nx.DiGraph:
    """Return a copy of `g` without nodes that have no edge at all.

    Every store element is added as a node up front so the raw graph reflects the whole
    tree, but a store is typically mostly elements with nothing declared about them (no
    `sp-ops:relationships` edge, no transform into a shared frame) -- rendering those adds
    nothing and, at the scale of a real store, drowns out the part that does.
    """
    isolated = list(nx.isolates(g))
    g2 = g.copy()
    g2.remove_nodes_from(isolated)
    return g2


def resolve_ref(base: str, ref: Any, tree: StoreTree) -> str:
    """Resolve a `from`/`to`/`input`/`output` reference to a canonical node path.

    `ref` is either a plain relative-path string (as used by `sp-ops:relationships`
    `from`/`to`), or an RFC-8 Reference object `{"id": ...}` and/or `{"path": {"path": ...}}`
    (as used by `scene` `input`/`output`). `base` is the path of the collection whose
    attributes the reference was read from, so relative paths resolve against it.
    """
    if isinstance(ref, str):
        return posixpath.normpath(posixpath.join(base, ref))
    if isinstance(ref, dict):
        path_obj = ref.get("path")
        if isinstance(path_obj, dict) and "path" in path_obj:
            return posixpath.normpath(posixpath.join(base, path_obj["path"]))
        ref_id = ref.get("id")
        if ref_id is not None:
            if ref_id in tree.ids:
                return tree.ids[ref_id]
            # An RFC-5 coordinate system id with no node of its own (e.g. "well"): keep
            # it as a coordinate-system node distinct from any element path.
            return f"cs:{ref_id}"
    raise ValueError(f"cannot resolve reference {ref!r} against {base!r}")


def _ensure_node(g: nx.DiGraph, tree: StoreTree, path: str) -> str:
    """Add `path` to `g` if a resolved reference names something outside the walked tree.

    A reference that does not resolve to a real node is a finding, not a tool bug (see
    docs/open-questions.md Q16/Q35: a reference can dangle in a real delivery). Surface it
    as a distinctly styled node rather than silently dropping or crashing on the edge.
    """
    if path not in g:
        node = tree.nodes.get(path)
        if node is not None:
            g.add_node(path, kind=node.type, label=node.name)
        else:
            g.add_node(path, kind=DANGLING, label=f"{path or '(root)'} (unresolved)")
    return path


def build_relationships_graph(tree: StoreTree) -> nx.DiGraph:
    """One node per store element, one edge per `sp-ops:relationships` entry."""
    g = nx.DiGraph()
    for path, node in tree.nodes.items():
        g.add_node(path, kind=node.type, label=node.name)

    for path, node in tree.nodes.items():
        if node.type != COLLECTION:
            continue
        relationships = node.attributes.get("sp-ops:relationships")
        if not relationships:
            continue
        for edge in relationships.get("edges", []):
            src = _ensure_node(g, tree, resolve_ref(path, edge["from"], tree))
            dst = _ensure_node(g, tree, resolve_ref(path, edge["to"], tree))
            g.add_edge(
                src,
                dst,
                declared_on=path,
                method=edge.get("method"),
                on=edge.get("on"),
                status=edge.get("status", "computed"),
                cardinality=edge.get("cardinality"),
                note=edge.get("note"),
            )
    return g


def _transform_summary(transformations: list[dict[str, Any]]) -> str:
    return " ∘ ".join(t.get("type", "?") for t in transformations)


def build_transformations_graph(tree: StoreTree) -> nx.DiGraph:
    """One node per element plus one per named coordinate system, one edge per transform.

    Two sources, both real per docs/layout.md#registration:
    - group-level `scene.coordinateTransformations` (the general RFC-5 mechanism; no
      example store here writes it yet, since none place tiles into a shared `well` frame
      through it).
    - per-multiscale `coordinateSystems` + the base pyramid level's own
      `coordinateTransformations`, which is what every image/labels node in the example
      stores actually carries today: e.g. a merged image's `(t, c, z, y, x)` array maps into
      its declared "well" coordinate system by a `scale` then `translation`.
    """
    g = nx.DiGraph()
    for path, node in tree.nodes.items():
        g.add_node(path, kind=node.type, label=node.name)

    def ensure_cs_node(cs_id: str) -> str:
        cs_path = f"cs:{cs_id}"
        if cs_path not in g:
            g.add_node(cs_path, kind=COORDINATE_SYSTEM, label=cs_id)
        return cs_path

    for path, node in tree.nodes.items():
        if node.type == COLLECTION:
            scene = node.attributes.get("scene")
            if not scene:
                continue
            for ct in scene.get("coordinateTransformations", []):
                src = _ensure_node(g, tree, resolve_ref(path, ct["input"], tree))
                dst_id = ct["output"]["id"]
                dst = ensure_cs_node(dst_id)
                g.add_edge(src, dst, declared_on=path, source="scene", type=ct.get("type"), params=ct)

        elif node.type == MULTISCALE:
            coordinate_systems = node.attributes.get("coordinateSystems") or []
            datasets = (node.multiscales[0].get("datasets") if node.multiscales else None) or []
            if not coordinate_systems or not datasets:
                continue
            cs_id = coordinate_systems[0]["id"]
            dst = ensure_cs_node(cs_id)
            base_transforms = datasets[0].get("coordinateTransformations", [])
            g.add_edge(
                path,
                dst,
                declared_on=path,
                source="multiscale-base-level",
                type=_transform_summary(base_transforms),
                params=base_transforms,
            )
    return g
