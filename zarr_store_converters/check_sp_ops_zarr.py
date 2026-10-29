r"""Walk an sp-ops store from its root collection and check the specification's MUSTs.

Usage, from the repository root:
    python zarr_store_converters/check_sp_ops_zarr.py STORE.zarr \
        [--tiffs DIR] [--zarr DIR] [--scallops DIR] [--nd2 DIR]

Handles both stages: `raw`, where a tile holds rounds and one multiscale per
channel, and `processed`, where a tile or merged collection holds one image plus
labels, points, shapes and tables.

With --tiffs, --zarr, --scallops or --nd2 the pixels are compared against the
source the store was built from. Advisories are reported separately from
failures: they are checks this exercise suggests the specification should
require, not ones it does.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import zarr

LEAF_TYPES = {"sp-ops:table", "sp-ops:shapes", "sp-ops:points"}
ROLES = {"nuclear", "base", "stain", "other"}

FAILURES: list[str] = []
ADVISORIES: list[str] = []
CHECKS = [0]
STORE: Path
TIFFS: Path | None = None
SRC_ZARR: Path | None = None
SRC_SCALLOPS: Path | None = None
SRC_ND2: Path | None = None
ND2_COMPARED = [0]


def check(condition: bool, message: str) -> bool:
    CHECKS[0] += 1
    if not condition:
        FAILURES.append(message)
    return bool(condition)


def advise(condition: bool, message: str) -> None:
    CHECKS[0] += 1
    if not condition:
        ADVISORIES.append(message)


def load_ome(rel: str) -> dict:
    p = (STORE / rel / "zarr.json") if rel else (STORE / "zarr.json")
    return json.loads(p.read_text()).get("attributes", {}).get("ome", {})


def resolve(rel: str, path_obj: dict) -> str:
    p = path_obj["path"]
    assert p.startswith("./"), p
    return f"{rel}/{p[2:]}" if rel else p[2:]


def rel_join(base: str, ref: str) -> str:
    parts = base.split("/") if base else []
    for seg in ref.split("/"):
        if seg == "..":
            parts = parts[:-1]
        elif seg not in ("", "."):
            parts.append(seg)
    return "/".join(parts)


def check_relationships(rel: str, attrs: dict, required: bool) -> None:
    rl = attrs.get("sp-ops:relationships")
    if rl is None:
        check(not required, f"MUST: sp-ops:relationships missing on {rel}")
        return
    check("version" in rl, f"{rel}: sp-ops:relationships has no version")
    for e in rl.get("edges", []):
        for end in ("from", "to"):
            target = rel_join(rel, e[end])
            check((STORE / target).exists(),
                  f"{rel}: edge {end} {e[end]!r} does not resolve to {target}")
        check(e.get("method") in {"join", "sjoin"},
              f"{rel}: edge method {e.get('method')!r} is neither join nor sjoin")
        check(e.get("status") in {"computed", "suggested"},
              f"{rel}: edge status {e.get('status')!r} is neither computed nor suggested")
        check("on" in e, f"{rel}: edge {e.get('from')} -> {e.get('to')} has no `on`")


def extent_um(rel: str) -> tuple[float, float] | None:
    """Physical y, x extent of a multiscale's level 0, from its own metadata."""
    ome = load_ome(rel)
    lvl0 = next((n for n in ome.get("nodes", []) if n["name"] == "0"), None)
    if lvl0 is None:
        return None
    t = lvl0["attributes"]["coordinateTransformations"][0]
    inner = t["transformations"][0] if t["type"] == "sequence" else t
    scale = inner.get("scale")
    if scale is None:
        return None
    shape = json.loads((STORE / rel / "0" / "zarr.json").read_text())["shape"]
    return (scale[-2] * shape[-2], scale[-1] * shape[-1])


def check_image(rel: str, stage: str, in_raw_channel: bool, is_label: bool) -> None:
    ome = load_ome(rel)
    check(ome.get("type") in {"multiscale", "singlescale"}, f"{rel}: not an image node")
    attrs = ome.get("attributes", {})

    if in_raw_channel:
        check("sp-ops:axis" in attrs, f"MUST: sp-ops:axis missing on {rel} in raw")
        check(attrs.get("sp-ops:axis", {}).get("name") == "c",
              f"{rel}: sp-ops:axis.name is not 'c'")

    if not is_label:
        chans = attrs.get("sp-ops:channels")
        check(isinstance(chans, list) and len(chans) >= 1,
              f"MUST: sp-ops:channels missing or empty on {rel}")
        for c in chans or []:
            check(c.get("role") in ROLES,
                  f"{rel}: channel role {c.get('role')!r} is not one of {sorted(ROLES)}")

    cs = attrs.get("coordinateSystems", [])
    check(len(cs) == 1, f"{rel}: expected exactly one coordinate system")
    axes = [a["name"] for a in cs[0]["axes"]] if cs else []
    order = ["round", "t", "c", "z", "y", "x"]
    check(axes == [a for a in order if a in axes],
          f"{rel}: axes {axes} are not a subset of {order} in order")
    if "round" in axes:
        check("sp-ops:rounds" in attrs,
              f"MUST: sp-ops:rounds missing on {rel} which has a round axis")

    levels = [n for n in ome.get("nodes", []) if n["type"] == "singlescale"]
    check(len(levels) >= 1, f"{rel}: no singlescale level")
    for lnode in levels:
        check("coordinateTransformations" in lnode.get("attributes", {}),
              f"{rel}/{lnode['name']}: MUST have coordinateTransformations")
        check((STORE / resolve(rel, lnode["path"]) / "zarr.json").exists(),
              f"{rel}/{lnode['name']}: array does not resolve")
        arr = json.loads((STORE / resolve(rel, lnode["path"]) / "zarr.json").read_text())
        check(len(arr["shape"]) == len(axes),
              f"{rel}/{lnode['name']}: shape {arr['shape']} does not match axes {axes}")


def walk_merged_or_tile(rel: str, stage: str, kind: str, acq_ids: set) -> None:
    """A tile or merged collection in a non-raw stage: image plus derived data."""
    ome = load_ome(rel)
    attrs = ome.get("attributes", {})
    if kind == "merged":
        check("sp-ops:merged" in attrs, f"MUST: sp-ops:merged missing on {rel}")
        check("source" in attrs.get("sp-ops:merged", {}),
              f"MUST: sp-ops:merged on {rel} has no source")
        advise(bool(attrs.get("sp-ops:merged", {}).get("source")),
               f"{rel}: sp-ops:merged.source is empty; the tiles it was stitched "
               f"from are not in this store")
    else:
        check("sp-ops:tile" in attrs, f"MUST: sp-ops:tile missing on {rel}")

    check_relationships(rel, attrs, required=False)

    images, labels = [], []
    ids = {n.get("id") for n in ome.get("nodes", []) if n.get("id")}
    for node in ome.get("nodes", []):
        nrel = resolve(rel, node["path"])
        if node["type"] in LEAF_TYPES:
            check((STORE / nrel).exists(), f"{rel}: {node['name']} does not resolve")
            continue
        child = load_ome(nrel)
        is_label = "labels" in child.get("attributes", {})
        check_image(nrel, stage, in_raw_channel=False, is_label=is_label)
        (labels if is_label else images).append((node["name"], nrel, child))

    check(len(images) >= 1, f"MUST: {rel} holds no image")
    for name, nrel, child in labels:
        src = child["attributes"]["labels"].get("source", [])
        check(bool(src), f"{nrel}: labels.source is empty")
        for s in src:
            check(s.get("id") in ids,
                  f"{nrel}: labels.source id {s.get('id')!r} matches no node in {rel}")
        # Not a requirement today. It is what would have caught the source's
        # labels declaring twice the image's pixel size on an identical grid.
        for s in src:
            snode = next((n for n in ome.get("nodes", []) if n.get("id") == s.get("id")), None)
            if snode is None:
                continue
            a, b = extent_um(nrel), extent_um(resolve(rel, snode["path"]))
            if a and b:
                advise(max(abs(a[0] - b[0]), abs(a[1] - b[1])) < 1.0,
                       f"{nrel}: extent {a} um disagrees with its source image {b} um")


def walk_modality(mrel: str, stage: str, acq_ids: set) -> None:
    mod = load_ome(mrel)
    mattrs = mod.get("attributes", {})
    check("sp-ops:modality" in mattrs, f"MUST: sp-ops:modality missing on {mrel}")
    if "acquisition" in mattrs:
        check(mattrs["acquisition"]["id"] in acq_ids,
              f"{mrel}: acquisition {mattrs['acquisition']['id']} not declared on the plate")

    children = {n["name"]: n for n in mod.get("nodes", [])}
    if stage == "raw":
        check("tiles" in children, f"MUST: {mrel} has no tiles collection in stage raw")
    check("tiles" in children or "merged" in children,
          f"MUST: {mrel} has neither tiles nor merged")

    if "merged" in children:
        walk_merged_or_tile(resolve(mrel, children["merged"]["path"]), stage, "merged", acq_ids)
    if "tiles" not in children:
        return

    trel = resolve(mrel, children["tiles"]["path"])
    tiles = load_ome(trel)
    tattrs = tiles.get("attributes", {})
    check("sp-ops:tiles" in tattrs, f"MUST: sp-ops:tiles missing on {trel}")
    layout_ref = tattrs.get("sp-ops:tiles", {}).get("layout", {})
    check("id" in layout_ref, f"MUST: sp-ops:tiles on {trel} has no layout reference")
    ids = {n.get("id") for n in tiles.get("nodes", [])}
    check(layout_ref.get("id") in ids,
          f"{trel}: layout reference {layout_ref.get('id')} matches no node id")

    layout_tiles = None
    lnode = next((n for n in tiles.get("nodes", []) if n.get("id") == layout_ref.get("id")), None)
    if lnode is not None:
        pq = STORE / resolve(trel, lnode["path"]) / "shapes.parquet"
        if check(pq.exists(), f"{trel}: layout shapes.parquet missing"):
            gdf = pd.read_parquet(pq)
            check("tile" in gdf.columns, f"{trel}: layout has no tile column")
            layout_tiles = set(gdf["tile"].tolist())

    tile_nodes = [n for n in tiles.get("nodes", []) if n["type"] == "collection"]
    check(len(tile_nodes) >= 1, f"MUST: {trel} has no tile")
    seen = set()
    for tnode in tile_nodes:
        tirel = resolve(trel, tnode["path"])
        tile = load_ome(tirel)
        tiattrs = tile.get("attributes", {})
        check("sp-ops:tile" in tiattrs, f"MUST: sp-ops:tile missing on {tirel}")
        idx = tiattrs.get("sp-ops:tile", {}).get("index")
        check(isinstance(idx, int), f"MUST: sp-ops:tile.index on {tirel} is not an integer")
        seen.add(idx)

        rounds = [n for n in tile.get("nodes", []) if n["type"] == "collection"]
        channels = [n for n in tile.get("nodes", []) if n["type"] == "multiscale"]
        if stage != "raw":
            walk_merged_or_tile(tirel, stage, "tile", acq_ids)
        elif rounds:
            for rnode in rounds:
                rrel = resolve(tirel, rnode["path"])
                rd = load_ome(rrel)
                rattrs = rd.get("attributes", {})
                check("sp-ops:axis" in rattrs, f"MUST: sp-ops:axis missing on {rrel}")
                check(rattrs.get("sp-ops:axis", {}).get("name") == "round",
                      f"{rrel}: sp-ops:axis.name is not 'round'")
                check(rattrs.get("acquisition", {}).get("id") in acq_ids,
                      f"{rrel}: acquisition not declared on the plate")
                rch = [n for n in rd.get("nodes", []) if n["type"] == "multiscale"]
                check(len(rch) >= 1, f"MUST: {rrel} has no channel in raw")
                for cnode in rch:
                    crel = resolve(rrel, cnode["path"])
                    check_image(crel, stage, in_raw_channel=True, is_label=False)
                    check_pixels(crel, "iss", idx, rattrs["sp-ops:axis"].get("value"))
        else:
            check(len(channels) >= 1, f"MUST: {tirel} has no channel in raw")
            for cnode in channels:
                crel = resolve(tirel, cnode["path"])
                check_image(crel, stage, in_raw_channel=True, is_label=False)
                check_pixels(crel, "pheno", idx, None)

    if layout_tiles is not None:
        check(seen == layout_tiles,
              f"{trel}: tile indices {sorted(seen)} do not match layout {sorted(layout_tiles)}")


def check_pixels_nd2(crel: str, modality: str, tile_index, cycle) -> None:
    """One raw channel against the ND2 page it was written from.

    The source names a well `Well<n>` and a field of view by its index within
    that well, so both are recovered from the store path and the tile index.
    """
    if SRC_ND2 is None:
        return
    import nd2

    parts = crel.split("/")
    row, column = parts[1], parts[2]
    well_no = {("A", "1"): 1, ("A", "2"): 2}[(row, column)]
    if modality == "iss":
        acq = "10x_c2-SBS-2" if cycle == 2 else f"10X_c{cycle}-SBS-{cycle}"
    else:
        acq = next(p.name for p in SRC_ND2.iterdir() if p.name.startswith("20X_"))
    pattern = f"Well{well_no}_Point{well_no}_{int(tile_index):04d}_*.nd2"
    matches = sorted((SRC_ND2 / acq).glob(pattern))
    if not check(len(matches) == 1, f"{crel}: {acq}/{pattern} matched {len(matches)} files"):
        return

    c = load_ome(crel)["attributes"]["sp-ops:axis"]["index"]
    arr = zarr.open_array(store=str(STORE), path=f"{crel}/0", mode="r")
    with nd2.ND2File(matches[0]) as f:
        page = f.asarray()[c]
    check(np.array_equal(arr[:], page), f"{crel}: level 0 pixels differ from {matches[0].name}")
    ND2_COMPARED[0] += 1


def check_pixels(crel: str, modality: str, tile_index, cycle) -> None:
    check_pixels_nd2(crel, modality, tile_index, cycle)
    if TIFFS is None:
        return
    import tifffile
    ome = load_ome(crel)
    c = ome["attributes"]["sp-ops:axis"]["index"]
    if modality == "iss":
        src = TIFFS / "input" / f"10X_c{cycle}-SBS-{cycle}" / f"10X_c{cycle}-SBS-{cycle}_A1_Tile-{tile_index}.sbs.tif"
    else:
        src = TIFFS / "10X_c0-DAPI-p65ab" / f"10X_c0-DAPI-p65ab_A1_Tile-{tile_index}.phenotype.tif"
    arr = zarr.open_array(store=str(STORE), path=f"{crel}/0", mode="r")
    check(np.array_equal(arr[:], tifffile.imread(src)[c]),
          f"{crel}: level 0 pixels differ from {src.name}")


def check_source_zarr() -> None:
    """Compare the processed store's level 0 against the source OME-NGFF plate."""
    if SRC_ZARR is None:
        return
    src = zarr.open_group(store=str(SRC_ZARR / "Biohub_OPS0001.zarr"), mode="r")
    base = "plate1_processed/A/1"
    img = np.asarray(src["A/1/0/0"])[0, :, 0]
    got = np.asarray(zarr.open_array(store=str(STORE), path=f"{base}/pheno/merged/image/0", mode="r"))
    check(np.array_equal(img, got), "pheno/merged/image level 0 differs from the source plate")
    n = 0
    for name in sorted(src["A/1/0/labels"].group_keys()):
        if "ome" not in dict(src[f"A/1/0/labels/{name}"].attrs):
            continue
        want = np.asarray(src[f"A/1/0/labels/{name}/0"])[0, 0, 0]
        got = np.asarray(zarr.open_array(store=str(STORE), path=f"{base}/pheno/merged/{name}/0", mode="r"))
        check(np.array_equal(want, got), f"{name} level 0 differs from the source plate")
        n += 1
    print(f"  compared 1 image and {n} label images against the source plate")


def check_source_scallops() -> None:
    """Compare the store against the scallops output it was built from."""
    if SRC_SCALLOPS is None:
        return
    D = SRC_SCALLOPS
    cycles = [1, 2, 3, 4, 5, 7, 8, 9, 10]

    def got(rel: str) -> np.ndarray:
        return np.asarray(zarr.open_array(store=str(STORE), path=rel, mode="r"))

    # the stitch stage: nine per round well images, stacked
    stack = got("plate1_intermediate/A/1/iss/merged/image/0")
    check(stack.shape[0] == len(cycles),
          f"intermediate iss image: {stack.shape[0]} rounds")
    for i, c in enumerate(cycles):
        src = np.asarray(zarr.open(
            f"{D}/stitch/iss/stitch/stitch.zarr/images/A1-{c}/s0", mode="r"))
        check(np.array_equal(stack[i], src),
              f"intermediate iss round {i} differs from stitched cycle {c}")
    ph = got("plate1_intermediate/A/1/pheno/merged/image/0")
    check(np.array_equal(ph, np.asarray(zarr.open(
        f"{D}/stitch/pheno/stitch/stitch.zarr/images/A1/s0", mode="r"))),
        "intermediate pheno image differs from the stitched source")

    # the ops stage: the registered stack, and its reference round passed through
    reg = got("plate1_processed/A/1/iss/merged/image/0")
    src = np.asarray(zarr.open(
        f"{D}/ops/iss-registered-t0.zarr/images/A1/s0", mode="r"))
    check(np.array_equal(reg, src), "processed iss image differs from the source")
    check(np.array_equal(reg[0], stack[0]),
          "the reference round is not the stitched cycle 1 unchanged")

    # labels
    names = {"nuclei": "A1-nuclei", "cells": "A1-cell", "cytosol": "A1-cytosol",
             "nuclei_unfiltered": "A1-nuclei.all",
             "cells_unfiltered": "A1-cell.all"}
    for name, src_name in names.items():
        check(np.array_equal(
            got(f"plate1_processed/A/1/pheno/merged/{name}/0"),
            np.asarray(zarr.open(
                f"{D}/ops/segment.zarr/labels/{src_name}/s0", mode="r"))),
            f"labels {name} differ from the source")

    # reads land on the cells they were assigned to, on one shared grid
    reads = pd.read_parquet(
        STORE / "plate1_processed/A/1/iss/merged/reads/points.parquet")
    cells = got("plate1_processed/A/1/pheno/merged/cells/0")
    check(np.array_equal(cells[reads["y"].to_numpy(), reads["x"].to_numpy()],
                         reads["label"].to_numpy()),
          "reads.label is not the cells pixel value at the read position")
    check(reads["barcode"].str.len().dropna().eq(9).all(),
          "not every read barcode is nine bases")

    # the library join the specification declares
    import anndata as ad
    lib = ad.read_zarr(STORE / "library")
    hit = reads["barcode"].isin(set(lib.obs["barcode_prefix_9"])).mean()
    advise(hit > 0.5,
           f"the declared reads-to-library edge matches {hit:.1%} of reads; "
           f"{len(lib)} / 4**9 = {len(lib) / 4 ** 9:.1%} is chance")

    print(f"  compared 10 well images, 5 label images and {len(reads)} reads "
          f"against the scallops output")


def footprint(rel: str, transform: dict) -> np.ndarray | None:
    """The four corners of an image, in the frame the transform outputs to."""
    ext = extent_um(rel)
    if ext is None:
        return None
    h, w = ext
    corners = np.array([[0.0, 0.0], [0.0, w], [h, w], [h, 0.0]])
    if transform["type"] == "affine":
        m = np.array(transform["affine"], dtype=float)
        if m.shape != (2, 3):
            return None
        return corners @ m[:, :2].T + m[:, 2]
    if transform["type"] == "translation":
        t = np.array(transform["translation"], dtype=float)
        if t.shape != (2,):
            return None
        return corners + t
    return None


def check_layout_against_scene(wrel: str) -> None:
    """Advisory: a tile's `layout` polygon agrees with its tile-to-well transform.

    Nothing in the specification ties the two together, so a store can declare
    a layout measured from the images and transforms taken from the stage
    readout, or the reverse, and stay conformant while placing the same tile in
    two places. This is what tells a reader the two agree.
    """
    well = load_ome(wrel)
    scene = well.get("attributes", {}).get("scene")
    if not scene:
        return
    placed: dict[tuple[str, str], list] = {}
    for t in scene.get("coordinateTransformations", []):
        path = t.get("input", {}).get("path", {}).get("path")
        if not path or t.get("output", {}).get("id") != "well":
            continue
        seg = path.lstrip("./").split("/")
        if len(seg) < 4 or seg[1] != "tiles" or not seg[2].startswith("tile"):
            continue
        box = footprint(rel_join(wrel, path.lstrip("./")), t)
        if box is not None:
            placed.setdefault((seg[0], seg[2][4:]), []).append(box)

    from shapely import wkb

    for modality in {m for m, _ in placed}:
        trel = f"{wrel}/{modality}/tiles"
        tiles = load_ome(trel)
        want_id = tiles.get("attributes", {}).get("sp-ops:tiles", {}).get("layout", {}).get("id")
        lnode = next((n for n in tiles.get("nodes", []) if n.get("id") == want_id), None)
        if lnode is None:
            continue
        pq = STORE / resolve(trel, lnode["path"]) / "shapes.parquet"
        if not pq.exists():
            continue
        gdf = pd.read_parquet(pq)
        for _, srow in gdf.iterrows():
            key = (modality, str(srow["tile"]))
            if key not in placed:
                continue
            geom = srow["geometry"]
            if isinstance(geom, (bytes, bytearray)):
                geom = wkb.loads(bytes(geom))
            want = np.asarray(geom.centroid.coords[0])[::-1]  # (y, x)
            got = np.stack(placed[key]).reshape(-1, 2).mean(axis=0)
            advise(float(np.abs(want - got).max()) < 1.0,
                   f"{wrel}/{modality}: layout polygon for tile {srow['tile']} is "
                   f"centred at {np.round(want, 1).tolist()} um but its tile-to-well "
                   f"transforms place it at {np.round(got, 1).tolist()} um")


def walk() -> None:
    root = load_ome("")
    check(root.get("type") == "collection", "root is not an RFC-8 collection")
    rattrs = root.get("attributes", {})
    check("sp-ops:spec" in rattrs, "MUST: sp-ops:spec missing on the screen collection")
    check("version" in rattrs.get("sp-ops:spec", {}), "MUST: sp-ops:spec has no version")
    check_relationships("", rattrs, required=False)

    plates = [n for n in root.get("nodes", []) if n["type"] == "collection"]
    check(len(plates) >= 1, "MUST: no plate collection under the screen")
    for n in root.get("nodes", []):
        if n["type"] in LEAF_TYPES:
            check((STORE / resolve("", n["path"])).exists(),
                  f"screen table {n['name']} does not resolve")

    for pnode in plates:
        prel = resolve("", pnode["path"])
        plate = load_ome(prel)
        pattrs = plate.get("attributes", {})
        check("sp-ops:plate" in pattrs, f"MUST: sp-ops:plate missing on {prel}")
        check("sp-ops:stage" in pattrs, f"MUST: sp-ops:stage missing on {prel}")
        check("plate" in pattrs, f"MUST: RFC-8 plate attribute missing on {prel}")
        check_relationships(prel, pattrs, required=False)
        stage = pattrs.get("sp-ops:stage")
        acq_ids = {a["id"] for a in pattrs.get("plate", {}).get("acquisitions", [])}
        check(len(acq_ids) >= 1, f"{prel}: plate declares no acquisitions")

        wells = [n for n in plate.get("nodes", []) if n["type"] == "collection"]
        check(len(wells) >= 1, f"MUST: {prel} has no well")
        for wnode in wells:
            wrel = resolve(prel, wnode["path"])
            well = load_ome(wrel)
            wattrs = well.get("attributes", {})
            check("well" in wattrs, f"MUST: well attribute missing on {wrel}")
            check_relationships(wrel, wattrs, required=False)
            mods = [n for n in well.get("nodes", []) if n["type"] == "collection"]
            check(len(mods) >= 1, f"MUST: {wrel} has no modality")
            for mnode in mods:
                walk_modality(resolve(wrel, mnode["path"]), stage, acq_ids)
            check_layout_against_scene(wrel)


if __name__ == "__main__":
    args = sys.argv[1:]
    STORE = Path(args[0]).expanduser()
    if "--tiffs" in args:
        TIFFS = Path(args[args.index("--tiffs") + 1]).expanduser()
    if "--zarr" in args:
        SRC_ZARR = Path(args[args.index("--zarr") + 1]).expanduser()
    if "--scallops" in args:
        SRC_SCALLOPS = Path(args[args.index("--scallops") + 1]).expanduser()
    if "--nd2" in args:
        SRC_ND2 = Path(args[args.index("--nd2") + 1]).expanduser()
    walk()
    check_source_zarr()
    check_source_scallops()
    if SRC_ND2 is not None:
        print(f"  compared {ND2_COMPARED[0]} raw channels against their ND2 pages")
    print(f"{CHECKS[0]} checks run, {len(FAILURES)} failed, {len(ADVISORIES)} advisories")
    for f in FAILURES:
        print("  FAIL", f)
    for a in ADVISORIES:
        print("  ADVISORY", a)
    sys.exit(1 if FAILURES else 0)
