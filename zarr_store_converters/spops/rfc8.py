"""RFC-8 node and RFC-5 coordinate metadata, as plain dicts.

Nothing here touches a store, so every function is cheap to test against the
JSON the builders used to emit inline. The store is written as RFC-8 nodes:
one `ome` attribute per group holding `version`, `type`, `name`, `attributes` and
`nodes`. No OME-NGFF `omero`, `plate` or `well` metadata is written anywhere --
see assumption A2 in docs/design-decisions.md.

The one exception is a multiscale's `multiscales` block, which is written from
the same numbers as the `singlescale` nodes; `multiscales_block` says why.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

SPEC_VERSION = "0.2.0-draft"
OME_VERSION = "0.x"

# docs/design-decisions.md D6. check_sp_ops_zarr.py enforces that an image's axes
# are a subset of this, in this order.
AXIS_ORDER = ("round", "t", "c", "z", "y", "x")

# docs/extension.md: the four values sp-ops:channels[].role may take.
ROLES = ("nuclear", "base", "stain", "other")

# `spatialdata_attrs.version` per element type, frozen at what the builders
# already wrote. These are NOT what released spatialdata reports -- 0.3.0 gives
# raster 0.1, shapes 0.2, points 0.1, tables 0.1 -- and `element_type` is not a
# spatialdata key at all in that release; it comes from assumption A4. So the
# numbers below are an sp-ops choice. Left as they are rather than "corrected",
# because which format they track is an open spec question.
SD_VERSION = {
    "image": "0.2",
    "labels": "0.2",
    "table": "0.2",
    "shapes": "0.2",
    "points": "0.1",
}


def set_ome(group, node_type: str, name: str,
            attributes: dict | None = None,
            nodes: list[dict] | None = None,
            multiscales: list[dict] | None = None) -> None:
    """Write a group's `ome` attribute, replacing whatever was there.

    Called after any library that writes its own `ome` block, so the RFC-8 node
    is what survives. `multiscales` is the one pre-RFC-8 key this store keeps;
    see `multiscales_block`.
    """
    ome: dict[str, Any] = {"version": OME_VERSION, "type": node_type, "name": name}
    if attributes:
        ome["attributes"] = attributes
    if multiscales:
        ome["multiscales"] = multiscales
    if nodes:
        ome["nodes"] = nodes
    group.attrs["ome"] = ome


def node(node_type: str, name: str, path: str, attributes: dict | None = None,
         element_id: str | None = None) -> dict:
    """One entry for a parent collection's `nodes` list."""
    entry: dict[str, Any] = {"type": node_type, "name": name}
    if element_id is not None:
        entry["id"] = element_id
    entry["path"] = {"type": "zarr", "path": path}
    if attributes:
        entry["attributes"] = attributes
    return entry


def zarr_ref(path: str, cs_id: str | None = None) -> dict:
    """An RFC-8 Path object, optionally carrying a coordinate system id."""
    ref: dict[str, Any] = {"path": {"type": "zarr", "path": path}}
    if cs_id is not None:
        ref = {"id": cs_id, **ref}
    return ref


def rel_ref(holder_rel: str, target_rel: str, cs_id: str | None = None) -> dict:
    """A reference from the group at `holder_rel` to the one at `target_rel`.

    Both paths are store relative. The `../` depth is computed rather than
    counted by hand, which is the durable fix for references that climb out of
    one plate collection into another: the convention is the one
    check_relationships uses, `rel_join(holder_rel, ref)`, i.e. the reference is
    relative to the group whose attributes hold it.
    """
    return zarr_ref("/".join([".."] * len(holder_rel.split("/")) + [target_rel]), cs_id)


def image_axes(names: Sequence[str]) -> list[dict]:
    """The multiscale's own axes: `round` is an array axis, `c` a channel axis."""
    special = {"round": {"name": "round", "type": "array"},
               "c": {"name": "c", "type": "channel"}}
    return [special.get(n, {"name": n, "type": "space", "unit": "micrometer"})
            for n in names]


def array_axes(names: Sequence[str]) -> list[dict]:
    """A pyramid level's own axes, which are array indices throughout."""
    return [{"name": n, "type": "array", "discrete": True} for n in names]


def level_body(level: int, *, pixel_size_um: float, n_axes: int,
               origin_um: tuple[float, float] = (0.0, 0.0)) -> dict:
    """The transform from pyramid level `level` into the multiscale's frame, without ends.

    `origin_um` is where the array's first pixel sits in that frame, which is how
    a stitcher's fuse crop is recorded. A bare `scale` is emitted when the
    translation would be all zeros, which is the case for level 0 of an image
    whose origin is the frame origin.
    """
    n_lead = n_axes - 2
    scale = pixel_size_um * (2 ** level)
    scale_vec = [1.0] * n_lead + [scale, scale]
    # A downsampled level's first pixel centre moves by half the size it gained.
    half = (scale - pixel_size_um) / 2
    offset = [0.0] * n_lead + [origin_um[0] + half, origin_um[1] + half]

    inner: list[dict] = [{"type": "scale", "scale": scale_vec}]
    if any(o != 0.0 for o in offset):
        inner.append({"type": "translation", "translation": offset})
    if len(inner) == 1:
        return inner[0]
    return {"type": "sequence", "transformations": inner}


def level_transform(level: int, *, pixel_size_um: float, n_axes: int,
                    out_cs: str, origin_um: tuple[float, float] = (0.0, 0.0)) -> dict:
    """`level_body` with the RFC-5 `input` and `output` coordinate system references."""
    body = level_body(level, pixel_size_um=pixel_size_um, n_axes=n_axes,
                      origin_um=origin_um)
    return {**body, "input": {"id": f"array{level}"}, "output": {"id": out_cs}}


def level_nodes(n_levels: int, axis_names: Sequence[str], *, pixel_size_um: float,
                out_cs: str, origin_um: tuple[float, float] = (0.0, 0.0),
                level_name=str) -> list[dict]:
    """The inlined `singlescale` nodes of a multiscale, one per level.

    RFC-8 requires a singlescale to carry its own `coordinateTransformations`,
    which a Zarr array cannot hold a `nodes` list for, so they are inlined in the
    multiscale group's zarr.json as RFC-8's own example does. See Q18.
    """
    axes = array_axes(axis_names)
    return [
        node("singlescale", level_name(i), f"./{level_name(i)}", attributes={
            "coordinateSystems": [{"id": f"array{i}", "axes": axes}],
            "coordinateTransformations": [level_transform(
                i, pixel_size_um=pixel_size_um, n_axes=len(axis_names),
                out_cs=out_cs, origin_um=origin_um)],
        })
        for i in range(n_levels)
    ]


def multiscales_block(name: str, n_levels: int, axis_names: Sequence[str], *,
                      pixel_size_um: float, origin_um: tuple[float, float] = (0.0, 0.0),
                      level_name=str) -> list[dict]:
    """The pre-RFC-8 `multiscales` block for a multiscale group.

    RFC-8 says its `Multiscale` node "replaces the multiscale metadata defined
    in the previous versions" of OME-Zarr, and this store writes those nodes.
    Every reader in circulation still finds a pyramid only here, though:
    napari-ome-zarr dispatches on `multiscales` and nothing else, and
    napari-sp-ops reads its levels from `multiscales[0].datasets`. Without this
    block a conformant store opens as no layers at all, in napari and in
    anything else built on ome-zarr-py.

    It is derived from the same `level_body` numbers as `level_nodes`, so the
    two cannot drift: same level order, same paths, same transforms. What the
    RFC-8 node adds is the per-level `coordinateSystems` and the `input` and
    `output` references, which have no place in the older block.

    Written alongside the nodes rather than instead of them, so a reader that
    knows RFC-8 keeps the coordinate systems and one that does not still sees a
    pyramid. See docs/open-questions.md Q18.
    """
    axes = image_axes(axis_names)
    datasets = [
        {"path": level_name(i),
         "coordinateTransformations": [level_body(
             i, pixel_size_um=pixel_size_um, n_axes=len(axis_names),
             origin_um=origin_um)]}
        for i in range(n_levels)
    ]
    return [{"version": OME_VERSION, "name": name, "axes": axes, "datasets": datasets}]


def labels_source(*element_ids: str) -> dict:
    """The RFC-8 `labels` attribute naming the image a labels element came from."""
    return {"labels": {"source": [{"id": i} for i in element_ids]}}


def edge(frm: str, to: str, *, on: dict, method: str = "join",
         status: str = "computed", cardinality: str | None = None) -> dict:
    """One `sp-ops:relationships` edge. Endpoints are relative to the holder."""
    e: dict[str, Any] = {"from": frm, "to": to, "method": method, "on": on,
                         "status": status}
    if cardinality is not None:
        e["cardinality"] = cardinality
    return e


def relationships(edges: list[dict]) -> dict:
    """The `sp-ops:relationships` value. An empty edge list is a valid answer."""
    return {"version": SPEC_VERSION, "edges": edges}


def acquisitions(iss_cycles: Sequence[int], *, pheno_first: bool = False) -> list[dict]:
    """The plate's acquisitions: one per ISS round, plus one for phenotyping."""
    iss = [{"id": f"iss-c{c}", "name": f"ISS cycle {c}"} for c in iss_cycles]
    pheno = [{"id": "pheno", "name": "phenotyping"}]
    return pheno + iss if pheno_first else iss + pheno


def well_attribute(row: str, column: str) -> dict:
    """The RFC-8 `well` attribute."""
    return {"well": {"row": {"id": row}, "column": {"id": column}}}
