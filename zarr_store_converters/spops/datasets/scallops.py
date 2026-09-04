"""experimentC_scallops: the same screen as experimentC, run through scallops.

`scallops <https://github.com/Genentech/scallops>`_ carries no raw tiles. What it
holds is the stitch stage (illumination fields, per cycle stitched well images,
stitch reports) and the ops stage (round registered ISS stack, spot detection,
base calling, segmentation, feature tables). So the store gets two plate
collections, `intermediate` and `processed`, plus the screen level `library`.
The raw plate lives in the sibling experimentC store, and the two share a plate id.

This dataset is the evidence for D4: `iss-registered-t0.zarr` declares axes
`t, c, y, x` with `t: [1, 2, 3, 4, 5, 7, 8, 9, 10]`, the cycle labels, and its
transform folders are `iss-transforms-t0/A1/t=2` to `t=10`. The store writes that
axis as `round`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import tifffile
import zarr
from shapely.geometry import box

from ..converter import ScreenConverter
from ..rfc8 import (acquisitions, edge, labels_source, node, rel_ref,
                    relationships, zarr_ref)

log = logging.getLogger("spops")

WELL_ROW, WELL_COLUMN = "A", "1"

# Cycle labels as acquired. Cycle 6 was not acquired, so round5 carries value 7.
ISS_CYCLES = [1, 2, 3, 4, 5, 7, 8, 9, 10]
# Acquisition site ids, and the grid indices scallops renumbered them to.
SITES = [102, 103]
GRID_INDEX = {102: 0, 103: 1}

PIXEL_SIZE_UM = 1.32        # image_spacing in every scallops group
TILE_PX = 1024
FUSE_CROP_PX = 11           # fuse_crop_width: the stitcher drops this many px per edge
CROP_UM = FUSE_CROP_PX * PIXEL_SIZE_UM
MERGED_SHAPE = (1002, 1972)
# Stage spacing between the two sites is 1280 um, which the stitcher converted to
# 1280 / 1.32 px. Its cross correlation scored zncc 0.0197 against a z_threshold
# of 3.09, so it kept this nominal offset rather than a measured one.
NOMINAL_DX_PX = 1280.0 / PIXEL_SIZE_UM

# Channel identity as the stitch step assigned it (--channel-name), which is
# where the dye names of the raw store (Cy3, A594, Cy5, Cy7) became base
# identities. See Q1.
ISS_CHANNELS = [("DAPI", "nuclear"), ("G", "base"), ("T", "base"),
                ("A", "base"), ("C", "base")]
PHENO_CHANNELS = [("DAPI", "nuclear"), ("NFkB", "stain")]
BASES = ["G", "T", "A", "C"]

INTERMEDIATE, PROCESSED = "plate1_intermediate", "plate1_processed"
WELL = f"{WELL_ROW}/{WELL_COLUMN}"


def _tile_offset_um(site: int) -> tuple[float, float]:
    """Offset of a field of view in the well frame, (y, x) in micrometres."""
    return (0.0, GRID_INDEX[site] * NOMINAL_DX_PX * PIXEL_SIZE_UM)


def _layout_frame() -> gpd.GeoDataFrame:
    """One polygon per field of view, declared from the stage position list."""
    side = TILE_PX * PIXEL_SIZE_UM
    rows = []
    for site in SITES:
        y0, x0 = _tile_offset_um(site)
        rows.append({"tile": GRID_INDEX[site], "site": site,
                     "geometry": box(x0, y0, x0 + side, y0 + side)})
    return gpd.GeoDataFrame(rows, geometry="geometry")


class ScallopsConverter(ScreenConverter):
    name = "experimentC_scallops"
    # From the acquisition directory embedded in the raw TIFF tags.
    plate_id = "6W-277A"
    pixel_size_um = PIXEL_SIZE_UM
    cs_id = "px"
    max_chunk = 512
    pyramid_levels = 3

    def load(self) -> None:
        self.D = self.sources["scallops"]
        self.raw = self.sources["raw"]

    # --------------------------------------------------------------- screen

    def write_screen_elements(self, root: zarr.Group) -> Iterable[dict]:
        src = pd.read_csv(self.raw / "barcodes.csv", dtype=str)
        obs = pd.DataFrame({
            "barcode": src["barcode"].astype(object),
            "sgRNA": src["sgRNA"].astype(object),
            "gene_symbol": src["gene_symbol"].astype("category"),
            # Derived: barcodes.csv has no perturbation id and no control flag.
            "perturbation_id": src["gene_symbol"].astype("category"),
            "role": np.where(src["gene_symbol"].eq("non-targeting"),
                             "control", "targeting"),
            "control_type": np.where(src["gene_symbol"].eq("non-targeting"),
                                     "non-targeting", ""),
            # Nine cycles were acquired, so a read is nine bases and can only
            # ever match this prefix. All 5738 prefixes are unique. See Q11.
            "barcode_prefix_9": src["barcode"].str.slice(0, 9).astype(object),
        })
        obs["role"] = obs["role"].astype("category")
        obs["control_type"] = obs["control_type"].astype("category")
        obs.index = pd.Index(src["barcode"].to_numpy())
        yield self.table(root, "library", obs, element_id="library")
        log.info("library written")

    def screen_attributes(self) -> dict:
        # The only edge whose endpoints span the whole screen. It is declared
        # because the specification requires it; it matches 2.4 percent of
        # reads, which is chance. See Q34.
        return {"sp-ops:relationships": relationships([
            edge(f"{PROCESSED}/{WELL}/iss/merged/reads", "library",
                 on={"left": "barcode", "right": "barcode_prefix_9"},
                 cardinality="n:1"),
        ])}

    def write_plates(self) -> Iterable[dict]:
        yield self._plate(INTERMEDIATE, "intermediate", self._intermediate_well)
        log.info("%s written", INTERMEDIATE)
        yield self._plate(PROCESSED, "processed", self._processed_well)
        log.info("%s written", PROCESSED)

    def _plate(self, name: str, stage: str, well_children) -> dict:
        return self.plate(
            name, stage=stage, rows=[WELL_ROW], columns=[WELL_COLUMN],
            acquisitions=acquisitions(ISS_CYCLES), with_names=False,
            children=lambda plate: [
                self.well(plate, WELL_ROW, WELL_COLUMN,
                          children=well_children,
                          scene=self._well_scene() if stage == "processed" else None,
                          edges=self._well_edges() if stage == "processed" else None)])

    # -------------------------------------------------- the intermediate plate

    def _intermediate_well(self, well: zarr.Group) -> list[dict]:
        out = []
        for modality, channels, rounds in [
            ("iss", ISS_CHANNELS, ISS_CYCLES),
            ("pheno", PHENO_CHANNELS, [0]),
        ]:
            out.append(self.modality(
                well, modality,
                acquisition="pheno" if modality == "pheno" else None,
                children=lambda m, mod=modality, ch=channels, rd=rounds: [
                    self._int_tiles(m, mod),
                    self._int_merged(m, mod, ch, rd),
                    self._int_illumination(m, mod, ch, rd),
                ]))
        return out

    def _stitch_dir(self, modality: str) -> Path:
        return self.D / f"stitch/{modality}"

    @staticmethod
    def _tag(modality: str, r: int) -> str:
        return f"A1-{r}" if modality == "iss" else "A1"

    def _int_tiles(self, modality: zarr.Group, mod: str) -> dict:
        rounds = ISS_CYCLES if mod == "iss" else [0]

        def children(tiles: zarr.Group) -> list[dict]:
            nodes = [self.shapes(tiles, "layout", _layout_frame(),
                                 element_id=f"{mod}-layout")]

            pos_rows = []
            for r in rounds:
                pos = pd.read_parquet(
                    self._stitch_dir(mod) / f"stitch/report/{self._tag(mod, r)}-positions.parquet")
                pos = pos.assign(round=rounds.index(r),
                                 acquisition=f"iss-c{r}" if mod == "iss" else "pheno")
                pos["source"] = pos["source"].map(lambda v: str(np.asarray(v).tolist()))
                pos_rows.append(pos)
            pos_all = pd.concat(pos_rows, ignore_index=True)
            pos_all["site"] = [SITES[int(t)] for t in pos_all["tile"]]
            pos_all.index = pd.Index(
                [f"{int(t)}_{int(r)}" for t, r in zip(pos_all["tile"], pos_all["round"])])
            nodes.append(self.table(tiles, "tile_features", pos_all,
                                    element_id=f"{mod}-tile-features"))

            # No per tile image exists at this stage: scallops stitches straight
            # from the raw TIFFs, so the tile collection has nothing under it.
            # This is Q33, and the four collections it produces are the four
            # expected failures of check_sp_ops_zarr.py.
            for site in SITES:
                nodes.append(self.tile(
                    tiles, f"tile{site}", index=GRID_INDEX[site],
                    extra_attributes={"sp-ops:site": site},
                    element_id=f"{mod}-tile{site}"))
            return nodes

        return self.tiles(
            modality, layout_id=f"{mod}-layout", children=children,
            edges=[edge("layout", "tile_features",
                        on={"left": "tile", "right": "tile"}, cardinality="1:n")])

    def _int_merged(self, modality: zarr.Group, mod: str, channels, rounds) -> dict:
        def children(merged: zarr.Group) -> list[dict]:
            # The stitcher writes one well image per round, each stitched on its
            # own. They share one grid, so they stack, which is what D6
            # requires. They are not registered to each other: that is what the
            # ops stage does. No key says so, and sp-ops:registration is only a
            # SHOULD, so it is omitted. See Q37.
            planes = [np.asarray(zarr.open(
                f"{self._stitch_dir(mod)}/stitch/stitch.zarr/images/{self._tag(mod, r)}/s0",
                mode="r")[:]) for r in rounds]
            stack = np.stack(planes) if len(planes) > 1 else planes[0]

            attrs: dict = {"sp-ops:channels": [{"name": n, "role": r}
                                               for n, r in channels]}
            axis_names = ["c", "y", "x"]
            if len(planes) > 1:
                axis_names = ["round", *axis_names]
                attrs["sp-ops:rounds"] = [
                    {"index": i, "acquisition": {"id": f"iss-c{c}"}}
                    for i, c in enumerate(rounds)]

            nodes = [self.image(merged, "image", data=stack,
                                axis_names=axis_names, attributes=attrs,
                                origin_um=(CROP_UM, CROP_UM),
                                element_id=f"{mod}-int-image")]

            # Which field of view each pixel came from. Identical in every
            # round, so it is written once. The source numbers the tiles from
            # zero, which collides with the labels background, so the grid index
            # plus one is written instead.
            base = f"{self._stitch_dir(mod)}/stitch/stitch.zarr/labels/{self._tag(mod, rounds[0])}"
            prov = np.asarray(zarr.open(f"{base}-tile/s0", mode="r")[:])
            cover = np.asarray(zarr.open(f"{base}-mask/s0", mode="r")[:])
            prov = np.where(cover > 0, prov.astype(np.int32) + 1, 0).astype(np.int32)
            nodes.append(self.labels(
                merged, "tile_provenance", data=prov, axis_names=["y", "x"],
                attributes=labels_source(f"{mod}-int-image"),
                origin_um=(CROP_UM, CROP_UM)))

            ev_rows = []
            for i, r in enumerate(rounds):
                ev = pd.read_parquet(
                    self._stitch_dir(mod) / f"stitch/report/{self._tag(mod, r)}-eval.parquet")
                ev = ev.assign(round=i,
                               acquisition=f"iss-c{r}" if mod == "iss" else "pheno")
                for col in ("pair", "shift"):
                    ev[col] = ev[col].map(lambda v: str(np.asarray(v).tolist()))
                ev_rows.append(ev)
            ev_all = pd.concat(ev_rows, ignore_index=True)
            ev_all.index = pd.Index([str(i) for i in ev_all["round"]])
            nodes.append(self.table(merged, "stitch_features", ev_all))
            return nodes

        return self.merged(modality,
                           source=[{"id": f"{mod}-tile{s}"} for s in SITES],
                           children=children)

    def _int_illumination(self, modality: zarr.Group, mod: str, channels,
                          rounds) -> dict:
        """Per round flat field profiles, in the tile frame.

        A third child of a modality, which docs/layout.md does not name and the
        checker never visits.
        """
        def children(illum: zarr.Group) -> list[dict]:
            nodes = []
            for i, r in enumerate(rounds):
                prof = tifffile.imread(
                    self._stitch_dir(mod)
                    / f"illumination_correction/{self._tag(mod, r)}.ome.tiff"
                ).astype(np.float32)
                nodes.append(self.image(
                    illum, f"round{i}", data=prof, axis_names=["c", "y", "x"],
                    attributes={
                        "sp-ops:channels": [{"name": n, "role": ro}
                                            for n, ro in channels],
                        "sp-ops:axis": {"name": "round", "index": i,
                                        "value": r if mod == "iss" else 0}},
                    levels=2))
            return nodes

        return self.collection(modality, "illumination", children=children)

    # ----------------------------------------------------- the processed plate

    def _processed_well(self, well: zarr.Group) -> list[dict]:
        return [
            self.modality(well, "iss", children=lambda m: [
                self.merged(m, source=self._int_tile_refs("iss"),
                            children=self._iss_merged)]),
            self.modality(well, "pheno", acquisition="pheno", children=lambda m: [
                self.merged(m, source=self._int_tile_refs("pheno"),
                            children=self._pheno_merged)]),
        ]

    @staticmethod
    def _int_tile_refs(mod: str) -> list[dict]:
        """The intermediate tiles this merged image was stitched from.

        The `../` depth is computed from the holder's own path rather than
        counted by hand: the attribute sits on `plate1_processed/A/1/<mod>/merged`,
        five segments deep, and the previous hand-written four resolved into
        `plate1_processed/A/1/plate1_intermediate/...`.
        """
        holder = f"{PROCESSED}/{WELL}/{mod}/merged"
        return [rel_ref(holder, f"{INTERMEDIATE}/{WELL}/{mod}/tiles/tile{s}")
                for s in SITES]

    def _iss_merged(self, merged: zarr.Group) -> list[dict]:
        D = self.D
        stack = np.asarray(zarr.open(
            f"{D}/ops/iss-registered-t0.zarr/images/A1/s0", mode="r")[:])
        assert stack.shape == (len(ISS_CYCLES), 5, *MERGED_SHAPE), stack.shape
        out = [self.image(
            merged, "image", data=stack, axis_names=["round", "c", "y", "x"],
            attributes={
                "sp-ops:rounds": [{"index": i, "acquisition": {"id": f"iss-c{c}"}}
                                  for i, c in enumerate(ISS_CYCLES)],
                "sp-ops:channels": [{"name": n, "role": r} for n, r in ISS_CHANNELS],
                # Recorded from the elastix run. The transform it actually
                # applied is an affine composed with a cubic B-spline, which
                # cannot be written. See Q32.
                "sp-ops:registration": {
                    "anchor": "DAPI",
                    "reference": rel_ref(f"{PROCESSED}/{WELL}/iss/merged",
                                         f"{INTERMEDIATE}/{WELL}/iss/merged/image")},
            },
            origin_um=(CROP_UM, CROP_UM), element_id="iss-merged-image")]

        peaks = pd.read_parquet(f"{D}/ops/spot-detect.zarr/points/A1-peaks.parquet")
        out.append(self.points(merged, "peaks", peaks.reset_index(drop=True),
                               element_id="iss-peaks"))

        reads = pd.read_parquet(f"{D}/ops/reads/reads/A1.parquet")
        out.append(self.points(merged, "reads", reads, element_id="iss-reads"))

        bases = pd.read_parquet(f"{D}/ops/reads/bases/A1.parquet")
        bases = bases.rename(columns={"t": "cycle"})
        bases["round"] = bases["cycle"].map({c: i for i, c in enumerate(ISS_CYCLES)})
        X = bases[["intensity", "corrected_intensity"]].to_numpy(np.float64)
        obs = bases.drop(columns=["intensity", "corrected_intensity"])
        obs.index = pd.Index([f"{r}_{c}_{t}" for r, c, t
                              in zip(obs["read"], obs["c"], obs["cycle"])])
        out.append(self.table(
            merged, "bases", obs, X=X,
            var=pd.DataFrame(index=["intensity", "corrected_intensity"]),
            element_id="iss-bases"))

        # A 4 by 4 base bleed matrix. Run level calibration with no granularity
        # in the feature ladder, so it lands here. See Q36.
        ct = np.asarray(zarr.open(f"{D}/ops/reads/crosstalk/A1-w.zarr/s0", mode="r")[:])
        out.append(self.table(
            merged, "crosstalk", pd.DataFrame(index=pd.Index(BASES, name=None)),
            X=ct.astype(np.float64), var=pd.DataFrame(index=pd.Index(BASES))))

        for src, name in [("A1-peak-labels", "peak_thresholds_labels"),
                          ("A1-peak-crosstalk", "peak_thresholds_crosstalk")]:
            qc = pd.read_parquet(f"{D}/ops/reads/spots/{src}.parquet")
            qc.index = pd.Index([f"{i}" for i in range(len(qc))])
            out.append(self.table(merged, name, qc))
        return out

    def _pheno_merged(self, merged: zarr.Group) -> list[dict]:
        D = self.D
        # Written into both plate collections, because nothing between the
        # stitch and the segmentation touched it and there is no way for one
        # stage to say that a single element of it is another stage's unchanged.
        img = np.asarray(zarr.open(
            f"{D}/stitch/pheno/stitch/stitch.zarr/images/A1/s0", mode="r")[:])
        out = [self.image(
            merged, "image", data=img, axis_names=["c", "y", "x"],
            attributes={
                "sp-ops:channels": [{"name": n, "role": r} for n, r in PHENO_CHANNELS],
                # No modality registration was performed: the two merged images
                # were stitched onto the same nominal grid and are used
                # interchangeably.
                "sp-ops:registration": {"anchor": "DAPI",
                                        "reference": {"id": "iss-merged-image"}}},
            origin_um=(CROP_UM, CROP_UM), element_id="pheno-merged-image")]

        label_arrays = {}
        for src, name in [("A1-nuclei", "nuclei"), ("A1-cell", "cells"),
                          ("A1-cytosol", "cytosol"),
                          # The pre-filter pass of two of them. Two
                          # segmentations of one compartment have no expression
                          # in the spec, so they are named apart. See Q42.
                          ("A1-nuclei.all", "nuclei_unfiltered"),
                          ("A1-cell.all", "cells_unfiltered")]:
            a = np.asarray(zarr.open(f"{D}/ops/segment.zarr/labels/{src}/s0", mode="r")[:])
            label_arrays[name] = a
            out.append(self.labels(
                merged, name, data=a, axis_names=["y", "x"],
                attributes=labels_source("pheno-merged-image"),
                origin_um=(CROP_UM, CROP_UM), element_id=f"pheno-{name}"))

        cell_labels = set(np.unique(label_arrays["cells"]).tolist()) - {0}
        for comp, folder, name in [("nuclei", "nuclei", "nuclei_features"),
                                   ("cells", "cell", "cells_features"),
                                   ("cytosol", "cytosol", "cytosol_features")]:
            X, obs, var = self._feature_table(comp, folder, cell_labels)
            out.append(self.table(merged, name, obs, X=X, var=var,
                                  element_id=f"pheno-{name}"))

        calls = pd.read_parquet(f"{D}/ops/reads/labels/A1.parquet")
        calls.index = pd.Index(calls["label"].astype(str))
        out.append(self.table(merged, "cell_barcodes", calls,
                              element_id="pheno-cell-barcodes"))

        # The pipeline also writes one wide table fusing all three compartments
        # and the barcode calls. It duplicates the split tables above; it is
        # kept because it is what the pipeline hands an analyst. See Q41.
        mg = pd.read_parquet(f"{D}/ops/merge/A1.parquet")
        mg.insert(0, "label", mg.index.to_numpy())
        mg.index = pd.Index(mg["label"].astype(str))
        num = [c for c in mg.columns if mg[c].dtype.kind in "fiu" and c != "label"]
        out.append(self.table(
            merged, "merged_features", mg.drop(columns=num),
            X=mg[num].to_numpy(np.float64), var=pd.DataFrame(index=pd.Index(num))))
        return out

    def _feature_table(self, comp: str, folder: str,
                       cell_labels: set[int]) -> tuple[np.ndarray, pd.DataFrame, pd.DataFrame]:
        """One compartment's split feature table: X the features, obs the geometry."""
        feats = pd.read_parquet(f"{self.D}/ops/features/{folder}/A1.parquet")
        objs = pd.read_parquet(f"{self.D}/ops/features/{folder}/A1-objects.parquet")
        # The objects table covers every label in the array; the feature table
        # may not.
        joined = objs.join(feats, how="left")
        X = joined[feats.columns].to_numpy(np.float64)
        obs = joined[objs.columns].copy()
        obs.insert(0, "label", joined.index.to_numpy())
        # Compartment membership. Nuclei, cells and cytosol share one label
        # numbering, so a nucleus belongs to the cell of the same value when
        # that cell exists. See Q43.
        obs["cell_label"] = [v if v in cell_labels else 0 for v in obs["label"]]
        obs["has_features"] = joined[feats.columns[0]].notna().to_numpy()
        obs.index = pd.Index(joined.index.astype(str))
        var = pd.DataFrame(index=pd.Index(list(feats.columns)))
        var["compartment"] = comp
        var["channel"] = [
            "NFkB" if c.endswith("NFkB") else ("DAPI" if c.endswith("DAPI") else "")
            for c in var.index]
        return X, obs, var

    # ------------------------------------------------------------- well frame

    def _well_scene(self) -> dict:
        """Both merged images sit on the same grid, offset from the well origin
        by the stitcher's fuse crop. The crop is not in the source metadata; it
        is derived from fuse_crop_width and confirmed by the array shapes.

        Only the two merged images appear here. Adding per tile transforms would
        start check_layout_against_scene firing, which skips any input path that
        is not `<modality>/tiles/tile<n>/...`.
        """
        return {
            "coordinateSystems": [{"id": "well", "axes": [
                {"name": "y", "type": "space", "unit": "micrometer"},
                {"name": "x", "type": "space", "unit": "micrometer"}]}],
            "coordinateTransformations": [
                {"type": "translation", "translation": [0.0, 0.0],
                 "input": zarr_ref(f"./{m}/merged/image", "px"),
                 "output": {"id": "well"}}
                for m in ("iss", "pheno")
            ],
        }

    @staticmethod
    def _well_edges() -> list[dict]:
        j = dict(on={"left": "value", "right": "label"}, cardinality="1:1")
        return [
            # The decoded read joins the cell it fell in. reads.label is the
            # pixel value of the cells labels at the read position, so the join
            # is computed.
            edge("iss/merged/reads", "pheno/merged/cells",
                 on={"left": "label", "right": "value"}, cardinality="n:1"),
            edge("iss/merged/bases", "iss/merged/reads",
                 on={"left": "read", "right": "read"}, cardinality="n:1"),
            # A peak becomes a read at the same position and scale. There is no
            # single column pair that expresses this: the key is (y, x, sigma).
            # See Q40.
            edge("iss/merged/peaks", "iss/merged/reads",
                 on={"left": "y", "right": "y"}, status="suggested",
                 cardinality="1:1"),
            edge("pheno/merged/cells", "pheno/merged/cells_features", **j),
            edge("pheno/merged/nuclei", "pheno/merged/nuclei_features", **j),
            edge("pheno/merged/cytosol", "pheno/merged/cytosol_features", **j),
            edge("pheno/merged/nuclei_features", "pheno/merged/cells",
                 on={"left": "cell_label", "right": "value"}, cardinality="n:1"),
            edge("pheno/merged/cytosol_features", "pheno/merged/cells",
                 on={"left": "cell_label", "right": "value"}, cardinality="n:1"),
            edge("pheno/merged/cells", "pheno/merged/cell_barcodes", **j),
            edge("pheno/merged/nuclei", "pheno/merged/merged_features", **j),
        ]
