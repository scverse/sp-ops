"""Write a small sp-ops screen with zarr v3 and RFC-8 group metadata.

The layout mirrors the two conformant example stores: a processed plate whose
merged collection holds an image with singleton T and Z axes, RFC-8 labels and
an RGBA overlay, and a raw plate whose tiles hold one multiscale per channel.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
import zarr

OME_VERSION = "0.6-rfc8-draft"
SPEC_VERSION = "0.2.0-draft"

TCZYX = [
    {"name": "T", "type": "time", "unit": "second"},
    {"name": "C", "type": "channel"},
    {"name": "Z", "type": "space", "unit": "micrometer"},
    {"name": "Y", "type": "space", "unit": "micrometer"},
    {"name": "X", "type": "space", "unit": "micrometer"},
]
YX = [
    {"name": "y", "type": "space", "unit": "micrometer"},
    {"name": "x", "type": "space", "unit": "micrometer"},
]
ZYX = [{"name": "z", "type": "space", "unit": "micrometer"}, *YX]
YXC = [*YX, {"name": "c", "type": "channel"}]
ISS_LAYOUT = {0: (100.0, 200.0, 120.8, 220.8), 1: (120.8, 200.0, 141.6, 220.8)}
ROUND_CYX = [{"name": "round", "type": "array"}, {"name": "c", "type": "channel"}, *YX]
TCZYX_LOWER = [{**axis, "name": axis["name"].lower()} for axis in TCZYX]


def _write_group(group_dir: Path, attributes: dict) -> None:
    group_dir.mkdir(parents=True, exist_ok=True)
    payload = {"zarr_format": 3, "node_type": "group", "attributes": attributes}
    (group_dir / "zarr.json").write_text(json.dumps(payload, indent=2))


def node(node_type: str, name: str, attributes: dict | None = None, node_id: str | None = None) -> dict:
    descriptor: dict = {"type": node_type, "name": name, "path": {"type": "zarr", "path": f"./{name}"}}
    if node_id:
        descriptor["id"] = node_id
    if attributes:
        descriptor["attributes"] = attributes
    return descriptor


def write_collection(group_dir: Path, name: str, nodes: list[dict], attributes: dict | None = None) -> None:
    ome: dict = {"version": OME_VERSION, "type": "collection", "name": name, "nodes": nodes}
    if attributes:
        ome["attributes"] = attributes
    _write_group(group_dir, {"ome": ome})


def write_multiscale(
    group_dir: Path,
    array: np.ndarray,
    axes: list[dict],
    scale: list[float],
    attributes: dict,
    coordinate_system: str,
    translation: list[float] | None = None,
    coordinate_axes: list[dict] | None = None,
) -> None:
    group_dir.mkdir(parents=True, exist_ok=True)
    zarr.create_array(store=str(group_dir / "0"), data=array, chunks=array.shape)
    transforms: list[dict] = [{"type": "scale", "scale": scale}]
    if translation is not None:
        transforms.append({"type": "translation", "translation": translation})
    multiscales = [{"version": OME_VERSION, "axes": axes, "datasets": [{"path": "0", "coordinateTransformations": transforms}]}]
    ome = {
        "version": OME_VERSION,
        "type": "multiscale",
        "multiscales": multiscales,
        "attributes": {**attributes, "coordinateSystems": [{"id": coordinate_system, "axes": coordinate_axes or axes}]},
    }
    _write_group(group_dir, {"ome": ome})


@dataclass(frozen=True)
class SyntheticScreen:
    root: Path
    plate_processed: Path
    well: Path
    modality: Path
    merged: Path
    image: Path
    labels: Path
    overlay: Path
    iss_image: Path
    reads: Path
    layout: Path
    table: Path
    plate_raw: Path
    raw_tiles: Path
    raw_tile: Path
    raw_round: Path
    raw_channel_yx: Path
    raw_channel_zyx: Path


def _processed_plate(plate: Path) -> None:
    well_attrs = {"well": {"row": {"id": "A"}, "column": {"id": "1"}}}
    write_collection(
        plate,
        "plate1_processed",
        [node("collection", "A/1", well_attrs)],
        {
            "sp-ops:plate": {"id": "plate1"},
            "sp-ops:stage": "processed",
            "plate": {"rows": [{"id": "A"}], "columns": [{"id": "1"}], "acquisitions": [{"id": "pheno", "name": "phenotyping"}]},
        },
    )
    well = plate / "A" / "1"
    scene = {
        "coordinateSystems": [{"id": "well", "axes": YX}],
        "coordinateTransformations": [
            {"type": "translation", "translation": [100.0, 200.0], "input": {"id": "px", "path": {"type": "zarr", "path": "./iss/merged/image"}}, "output": {"id": "well"}}
        ],
    }
    write_collection(well, "A/1", [node("collection", "iss"), node("collection", "pheno")], {**well_attrs, "scene": scene})
    _processed_iss(well / "iss")
    modality = well / "pheno"
    write_collection(modality, "pheno", [node("collection", "merged")], {"sp-ops:modality": "pheno", "acquisition": {"id": "pheno"}})
    merged = modality / "merged"
    edge = {"from": "cells", "to": "cells_features", "method": "join", "on": {"left": "value", "right": "label"}, "status": "computed", "cardinality": "1:1"}
    write_collection(
        merged,
        "merged",
        [node("multiscale", "image", node_id="pheno-merged-image"), node("multiscale", "cells"), node("multiscale", "overlay"), node("sp-ops:table", "cells_features")],
        {"sp-ops:merged": {"source": []}, "sp-ops:relationships": {"version": SPEC_VERSION, "edges": [edge]}},
    )
    write_table(
        merged / "cells_features",
        {"label": np.array([1, 2, 3, 4]), "area": np.array([10.5, 20.0, 30.0, 40.0])},
        {"barcode": (np.array([0, 1, 0, -1], dtype=np.int8), np.array(["ACGT", "TTGA"], dtype=np.dtypes.StringDType()))},
        {"gene": (np.array(["A", "B", "", "D"], dtype=np.dtypes.StringDType()), np.array([False, False, True, False]))},
    )
    rng = np.random.default_rng(0)
    write_multiscale(
        merged / "image",
        rng.random((1, 2, 1, 16, 16), dtype=np.float32),
        TCZYX,
        [1.0, 1.0, 2.0, 0.325, 0.325],
        {"sp-ops:channels": [{"name": "GFP", "role": "stain"}, {"name": "nuclei_prediction", "role": "other"}]},
        "well",
        translation=[0.0, 0.0, 0.0, 15600.0, 15600.0],
        coordinate_axes=TCZYX_LOWER,
    )
    write_multiscale(
        merged / "cells",
        rng.integers(0, 5, (1, 1, 1, 16, 16), dtype=np.int32),
        TCZYX,
        [1.0, 1.0, 2.0, 0.65, 0.65],
        {
            "labels": {"source": [{"path": {"type": "zarr", "path": "../image"}, "id": "pheno-merged-image"}]},
            "sp-ops:label_kind": "biological",
        },
        "well",
        translation=[0.0, 0.0, 0.0, 15600.0, 15600.0],
        coordinate_axes=TCZYX_LOWER,
    )
    write_multiscale(
        merged / "overlay",
        rng.integers(0, 255, (16, 16, 4), dtype=np.uint8),
        YXC,
        [1.0, 1.0, 1.0],
        {"labels": {"source": [{"id": "pheno-merged-image"}]}, "sp-ops:label_kind": "overlay"},
        "well",
    )


def _processed_iss(modality: Path) -> None:
    """A registered multi-round ISS image with axes round, c, y, x."""
    write_collection(modality, "iss", [node("collection", "merged")], {"sp-ops:modality": "iss"})
    merged = modality / "merged"
    write_collection(
        merged, "merged", [node("multiscale", "image", node_id="iss-merged-image"), node("sp-ops:points", "reads")], {"sp-ops:merged": {"source": []}}
    )
    rng = np.random.default_rng(2)
    write_points(merged / "reads", np.array([[1.3, 2.6], [13.0, 6.5], [20.8, 19.5]]), {"read": ["ACGT", "TTGA", "ACGT"], "barcode": ["b1", "b2", "b1"]})
    full = rng.integers(0, 4000, (2, 2, 16, 16), dtype=np.uint16)
    write_rfc8_multiscale(
        merged / "image",
        [full, full[:, :, ::2, ::2]],
        ROUND_CYX,
        [[1.0, 1.0, 1.3, 1.3], [1.0, 1.0, 2.6, 2.6]],
        {
            "sp-ops:channels": [{"name": "DAPI", "role": "nuclear"}, {"name": "A", "role": "base"}],
            "sp-ops:rounds": [{"index": 0, "acquisition": {"id": "iss-c1"}}, {"index": 1, "acquisition": {"id": "iss-c2"}}],
        },
        "px",
    )


def write_element_group(group_dir: Path, element_type: str, extra: dict | None = None) -> None:
    """A leaf element group tagged with ``spatialdata_attrs.element_type`` and no ``ome`` key."""
    _write_group(group_dir, {"spatialdata_attrs": {"element_type": element_type}, **(extra or {})})


def write_layout(group_dir: Path, boxes: dict[int, tuple[float, float, float, float]]) -> None:
    """GeoParquet polygons, one per tile index, from x_min, y_min, x_max, y_max boxes in micrometres."""
    write_element_group(group_dir, "shapes", {"sp-ops:geometry": "polygon", "coordinateSystem": "well"})
    geometry = [shapely.box(*box).wkb for box in boxes.values()]
    table = pa.table({"tile": pa.array(list(boxes), pa.int64()), "geometry": pa.array(geometry, pa.binary())})
    geo = {"version": "1.0.0", "primary_column": "geometry", "columns": {"geometry": {"encoding": "WKB", "geometry_types": ["Polygon"]}}}
    table = table.replace_schema_metadata({b"geo": json.dumps(geo).encode()})
    pq.write_table(table, group_dir / "shapes.parquet")


def write_points(group_dir: Path, xy: np.ndarray, columns: dict[str, list] | None = None) -> None:
    """Parquet points with x and y columns plus any extra columns."""
    write_element_group(group_dir, "points", {"coordinateSystem": "well"})
    data = {"x": xy[:, 0], "y": xy[:, 1], **(columns or {})}
    pq.write_table(pa.table(data), group_dir / "points.parquet")


def write_rfc8_multiscale(group_dir: Path, levels: list[np.ndarray], axes: list[dict], scales: list[list[float]], attributes: dict, coordinate_system: str) -> None:
    """An RFC-8 multiscale written as ``singlescale`` nodes, each with its own array-to-image transform.

    This is the form ome-zarr-py writes: no ``multiscales`` list, axes only in
    the node's ``coordinateSystems``, and per-level ``coordinateTransformations``
    from a discrete array system to the image system.
    """
    nodes = []
    for index, (array, scale) in enumerate(zip(levels, scales, strict=True)):
        zarr.create_array(store=str(group_dir / str(index)), data=array, chunks=array.shape)
        transform: dict = {"type": "scale", "scale": scale, "input": {"id": f"array{index}"}, "output": {"id": coordinate_system}}
        if index:
            offset = [0.0 if axis["type"] != "space" else (scale[position] - scales[0][position]) / 2 for position, axis in enumerate(axes)]
            transform = {"type": "sequence", "transformations": [{"type": "scale", "scale": scale}, {"type": "translation", "translation": offset}], "input": {"id": f"array{index}"}, "output": {"id": coordinate_system}}
        level_axes = [{"name": axis["name"], "type": "array", "discrete": True} for axis in axes]
        nodes.append({"type": "singlescale", "name": str(index), "path": {"type": "zarr", "path": f"./{index}"}, "attributes": {"coordinateSystems": [{"id": f"array{index}", "axes": level_axes}], "coordinateTransformations": [transform]}})
    ome = {"version": "0.x", "type": "multiscale", "name": group_dir.name, "attributes": {**attributes, "coordinateSystems": [{"id": coordinate_system, "axes": axes}]}, "nodes": nodes}
    _write_group(group_dir, {"ome": ome})


def write_table(
    group_dir: Path,
    columns: dict[str, np.ndarray],
    categorical: dict[str, tuple[np.ndarray, np.ndarray]] | None = None,
    nullable: dict[str, tuple[np.ndarray, np.ndarray]] | None = None,
    zarr_format: int = 2,
) -> None:
    """An AnnData-in-zarr table with ``obs`` columns, optional categoricals and optional nullable arrays."""
    attributes = {"encoding-type": "anndata", "encoding-version": "0.1.0", "spatialdata_attrs": {"element_type": "table"}}
    table = zarr.create_group(str(group_dir), zarr_format=zarr_format, attributes=attributes)
    order = [*columns, *(categorical or {}), *(nullable or {})]
    obs = table.create_group("obs", attributes={"encoding-type": "dataframe", "encoding-version": "0.2.0", "_index": "_index", "column-order": order})
    length = len(next(iter(columns.values())))
    obs.create_array("_index", data=np.array([f"cell{index}" for index in range(length)], dtype=np.dtypes.StringDType()))
    for name, values in columns.items():
        obs.create_array(name, data=values)
    for name, (codes, categories) in (categorical or {}).items():
        group = obs.create_group(name, attributes={"encoding-type": "categorical", "encoding-version": "0.2.0", "ordered": False})
        group.create_array("codes", data=codes)
        group.create_array("categories", data=categories)
    for name, (values, mask) in (nullable or {}).items():
        group = obs.create_group(name, attributes={"encoding-type": "nullable-string-array", "encoding-version": "0.1.0"})
        group.create_array("values", data=values)
        group.create_array("mask", data=mask)


def write_plain_multiscale(group_dir: Path, array: np.ndarray, axes: list[dict], scale: list[float]) -> None:
    """An OME-NGFF 0.5 image with no RFC-8 type and no sp-ops keys."""
    group_dir.mkdir(parents=True, exist_ok=True)
    zarr.create_array(store=str(group_dir / "0"), data=array, chunks=array.shape)
    multiscales = [{"axes": axes, "datasets": [{"path": "0", "coordinateTransformations": [{"type": "scale", "scale": scale}]}]}]
    _write_group(group_dir, {"ome": {"version": "0.5", "multiscales": multiscales}})


def _raw_plate(plate: Path) -> None:
    well_attrs = {"well": {"row": {"id": "A"}, "column": {"id": "1"}}}
    acquisitions = [{"id": "iss-c1", "name": "ISS cycle 1"}, {"id": "iss-c2", "name": "ISS cycle 2"}, {"id": "pheno", "name": "phenotyping"}]
    write_collection(
        plate,
        "plate1_raw",
        [node("collection", "A/1", well_attrs)],
        {"sp-ops:plate": {"id": "plate1"}, "sp-ops:stage": "raw", "plate": {"rows": [{"id": "A"}], "columns": [{"id": "1"}], "acquisitions": acquisitions}},
    )
    well = plate / "A" / "1"
    write_collection(well, "A/1", [node("collection", "iss"), node("collection", "pheno")], well_attrs)
    rng = np.random.default_rng(1)

    iss = well / "iss"
    write_collection(iss, "iss", [node("collection", "tiles")], {"sp-ops:modality": "iss"})
    tile_nodes = [node("collection", f"tile{index}", {"sp-ops:tile": {"index": index}}) for index in range(2)]
    write_collection(
        iss / "tiles", "tiles", [node("sp-ops:shapes", "layout", node_id="iss-layout"), *tile_nodes], {"sp-ops:tiles": {"layout": {"id": "iss-layout"}}}
    )
    write_layout(iss / "tiles" / "layout", ISS_LAYOUT)
    channels = [("DAPI", "nuclear"), ("Cy3", "base")]
    for tile_node in tile_nodes:
        tile = iss / "tiles" / tile_node["name"]
        rounds = []
        for index, cycle in enumerate((1, 2)):
            rounds.append(node("collection", f"round{index}", {"acquisition": {"id": f"iss-c{cycle}"}, "sp-ops:axis": {"name": "round", "index": index, "value": cycle}}))
        write_collection(tile, tile_node["name"], rounds, tile_node["attributes"])
        for round_node in rounds:
            round_dir = tile / round_node["name"]
            channel_nodes = []
            for index, (name, role) in enumerate(channels):
                attrs = {"sp-ops:axis": {"name": "c", "index": index}, "sp-ops:channels": [{"name": name, "role": role}]}
                channel_nodes.append(node("multiscale", f"channel{index}", attrs))
                write_multiscale(round_dir / f"channel{index}", rng.integers(0, 4000, (16, 16), dtype=np.uint16), YX, [1.3, 1.3], attrs, f"iss-{round_node['name']}-c{index}")
            write_collection(round_dir, round_node["name"], channel_nodes, round_node["attributes"])

    pheno = well / "pheno"
    write_collection(pheno, "pheno", [node("collection", "tiles")], {"sp-ops:modality": "pheno", "acquisition": {"id": "pheno"}})
    write_collection(pheno / "tiles", "tiles", [node("collection", "tile0", {"sp-ops:tile": {"index": 0}})], {"sp-ops:tiles": {}})
    attrs = {"sp-ops:axis": {"name": "c", "index": 0}, "sp-ops:channels": [{"name": "AF750", "role": "stain"}]}
    write_collection(pheno / "tiles" / "tile0", "tile0", [node("multiscale", "channel0", attrs)], {"sp-ops:tile": {"index": 0}})
    write_multiscale(pheno / "tiles" / "tile0" / "channel0", rng.integers(0, 4000, (2, 16, 16), dtype=np.uint16), ZYX, [1.5, 0.325, 0.325], attrs, "pheno-c0")


def build_synthetic_screen(root: Path) -> SyntheticScreen:
    """Write the screen under ``root`` and return the paths a test needs."""
    plate_processed = root / "plate1_processed"
    plate_raw = root / "plate1_raw"
    write_collection(
        root,
        "screen",
        [
            node("collection", "plate1_processed", {"sp-ops:plate": {"id": "plate1"}, "sp-ops:stage": "processed"}),
            node("collection", "plate1_raw", {"sp-ops:plate": {"id": "plate1"}, "sp-ops:stage": "raw"}),
        ],
        {"sp-ops:spec": {"version": SPEC_VERSION}},
    )
    _processed_plate(plate_processed)
    _raw_plate(plate_raw)
    merged = plate_processed / "A" / "1" / "pheno" / "merged"
    raw_tile = plate_raw / "A" / "1" / "iss" / "tiles" / "tile0"
    return SyntheticScreen(
        root=root,
        plate_processed=plate_processed,
        well=plate_processed / "A" / "1",
        modality=plate_processed / "A" / "1" / "pheno",
        merged=merged,
        image=merged / "image",
        labels=merged / "cells",
        overlay=merged / "overlay",
        iss_image=plate_processed / "A" / "1" / "iss" / "merged" / "image",
        reads=plate_processed / "A" / "1" / "iss" / "merged" / "reads",
        layout=raw_tile.parent / "layout",
        table=merged / "cells_features",
        plate_raw=plate_raw,
        raw_tiles=raw_tile.parent,
        raw_tile=raw_tile,
        raw_round=raw_tile / "round0",
        raw_channel_yx=raw_tile / "round0" / "channel0",
        raw_channel_zyx=plate_raw / "A" / "1" / "pheno" / "tiles" / "tile0" / "channel0",
    )
