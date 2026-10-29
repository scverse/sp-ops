"""cpg0021_sample: a two-well subset of cpg0021-periscope, written as `raw`.

Nikon ND2 files straight off the microscope with one guide table beside them,
and no derived data of any kind -- no segmentation, no features, no reads -- so
the store is one `raw` plate and nothing else. It is the complement of
`biohub_example`, which is `processed` and nothing else.

What makes it worth converting is that the acquisition metadata arrives intact.
Every image carries its objective, numerical aperture, camera, binning,
exposure, filter block, autofocus offset, stage coordinates, timestamp and a
pixel-to-stage matrix, so this is the dataset that says what a `raw` store is
being asked to carry, and the one that can be checked against itself. Four
things follow, and each is a finding rather than a build choice:

* The tile positions are measured, not declared. The recorded stage
  coordinates disagree with the images by up to 68 px because the recorded
  pixel size is about one percent too large. `layout` holds the measured
  footprint and keeps the stage readout in four columns beside it, because
  nothing in the specification distinguishes the two (Q2, Q49).
* The tile-to-well transform is an affine with a rotation, not a translation.
  See `cpg0021_geometry.orientation`.
* The phenotyping transforms carry a scale. That is registration step 3, the
  modality registration, done at `raw` because a raw store places both
  modalities in one `well` frame and has no merged image to do it between.
  `sp-ops:registration` is bound to a processed multiscale, so the store cannot
  say so (Q50).
* `image_metadata` is the provenance table Q6 proposed, written here to see
  whether it works: one row per acquired image plane. Q6 puts it at the plate
  level; this splits it per modality under each `tiles` collection, which
  features.md permits and which lets the well and the modality come from
  position in the hierarchy rather than from columns. Its key is
  `(tile, round, channel)` and an edge's `on` takes one column pair, so the edge
  joins on `tile` alone (Q33).

Hygiene, and not specification problems: the cycle 2 directory is `10x_c2-SBS-2`
and the other eleven are `10X_c<n>-SBS-<n>`; `Well1_Point1` encodes the well
twice and the row and column not at all (Q18); three phenotyping channels are
named by dye or filter and one, `750`, by an excitation line (Q9, Q51); 96 of
the 272 images report a timestamp in the year 3189, so the recorded value is
written with a `timestamp_valid` column beside it; and `gene_symbol` and
`gene_id` do not agree on identity.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import zarr
from shapely.geometry import Polygon

from ..converter import ScreenConverter
from ..rfc8 import acquisitions, edge, relationships, zarr_ref
from . import cpg0021_geometry as geometry

log = logging.getLogger("spops")

BATCH = "20200805_A549_WG_Screen"
PLATE = "CP186A"
STAGE = "raw"

# The delivery names a well twice and its row and column not at all, so the
# mapping to a plate address is asserted here. See Q18.
WELLS = {1: ("A", "1"), 2: ("A", "2")}
# A 6-well plate. Only two wells carry pixels; a plate collection declares what
# the plate has, not what the delivery shipped. See Q4.
PLATE_ROWS, PLATE_COLUMNS = ["A", "B"], ["1", "2", "3"]

ISS_CYCLES = list(range(1, 13))       # twelve, no gap
TILE_PX = 1480

# `Well<n>_Point<n>_<site>_Channel<names>_Seq<n>.nd2`. The site is the index
# within the well; the sequence number is the position in the original
# whole-plate run and is not contiguous in this subset, so it is never used.
FILENAME = re.compile(r"^Well(?P<well>\d+)_Point(?P<point>\d+)_(?P<site>\d{4})_"
                      r"Channel(?P<channels>.+)_Seq(?P<seq>\d{4})\.nd2$")
# Cycle 2's directory is lowercase, so the match is case insensitive and the
# cycle is read from the directory rather than from any metadata prefix.
ISS_DIR = re.compile(r"^10x_c(?P<cycle>\d+)-SBS-(?P=cycle)$", re.IGNORECASE)
PHENO_DIR = re.compile(r"^20x_CP_", re.IGNORECASE)

# Roles for the four values sp-ops:channels[].role may take. ISS carries four
# base channels; phenotyping carries four stains, one of which the delivery
# names by an excitation line rather than by what it images.
ROLES = {"iss": "base", "pheno": "stain"}

# Julian day number of the Unix epoch, and the window outside which a recorded
# timestamp is not believable. The arithmetic is `datetime` rather than
# `pd.Timestamp` because 96 of the 272 images stamp the year 3189, which is
# past the nanosecond range a pandas timestamp can hold at all.
_JULIAN_UNIX_EPOCH = 2440587.5
_VALID_FROM = datetime(2000, 1, 1, tzinfo=timezone.utc)
_VALID_TO = datetime(2100, 1, 1, tzinfo=timezone.utc)


def _footprint(centre_yx: np.ndarray, rotation: np.ndarray, side_um: float) -> Polygon:
    """The tile's outline in the well frame, as the transform places it."""
    half = side_um / 2
    corners = np.array([[-half, -half], [-half, half], [half, half], [half, -half]])
    placed = corners @ rotation.T + centre_yx
    return Polygon(placed[:, ::-1])            # shapely is (x, y)


class Cpg0021Converter(ScreenConverter):
    name = "cpg0021_sample"
    plate_id = PLATE
    # The ISS value. Phenotyping is half of it and passes its own per call; a
    # converter has one class-level default and this store has two modalities
    # at different magnifications.
    pixel_size_um = 1.2142857142857144
    cs_id = "px"
    max_chunk = 512
    pyramid_levels = 3

    # ------------------------------------------------------------------- load

    def load(self) -> None:
        import nd2                              # only this dataset needs it

        self._nd2 = nd2
        root = self.sources["dataset"] / "cpg0021-periscope" / "broad"
        self.images = root / "images" / BATCH / "images" / PLATE
        self.barcodes = root / "workspace" / "metadata" / BATCH / "Barcodes.csv"
        if not self.images.is_dir():
            raise FileNotFoundError(f"no acquisition directories under {self.images}")

        # acquisition -> {(well, site): path}, and the channel names it declares
        self.by_acquisition: dict[str, dict[tuple[int, int], Path]] = {}
        self.channels: dict[str, list[str]] = {}
        self.rounds: list[tuple[str, int]] = []          # (directory, cycle label)
        pheno_dir = None
        for d in sorted(p for p in self.images.iterdir() if p.is_dir()):
            iss = ISS_DIR.match(d.name)
            if iss is None and PHENO_DIR.match(d.name) is None:
                log.info("skipping unrecognised acquisition %s", d.name)
                continue
            found = {}
            for f in d.glob("*.nd2"):
                m = FILENAME.match(f.name)
                if m is None:
                    continue
                found[(int(m["well"]), int(m["site"]))] = f
                self.channels.setdefault(d.name, m["channels"].split(","))
            if not found:
                continue
            self.by_acquisition[d.name] = dict(sorted(found.items()))
            if iss is not None:
                self.rounds.append((d.name, int(iss["cycle"])))
            else:
                pheno_dir = d.name
        self.rounds.sort(key=lambda rc: rc[1])
        self.pheno_dir = pheno_dir

        cycles = [c for _, c in self.rounds]
        if not cycles or self.pheno_dir is None:
            raise ValueError(f"expected ISS cycles and one phenotyping acquisition "
                             f"under {self.images}, found {cycles} and "
                             f"{self.pheno_dir!r}")
        # A gap is expressible -- the round index is its position and
        # `sp-ops:axis.value` its label (D3) -- so a missing cycle is worth
        # saying out loud and not worth refusing to convert.
        if cycles != ISS_CYCLES:
            log.info("ISS cycles %s, not the %s this delivery is documented with",
                     cycles, ISS_CYCLES)
        # Every cycle images the same fields of view, and `_path` assumes it.
        grids = {tuple(sorted(self.by_acquisition[d])) for d, _ in self.rounds}
        if len(grids) != 1:
            raise ValueError(f"ISS acquisitions do not share one tile grid: "
                             f"{[len(g) for g in grids]} images")

        self.sites = {
            (well, mod): sorted(s for (w, s) in self.by_acquisition[acq] if w == well)
            for well in WELLS
            for mod, acq in (("iss", self.rounds[0][0]), ("pheno", self.pheno_dir))}
        log.info("%d acquisitions, %d ISS cycles, wells %s; %s",
                 len(self.by_acquisition), len(cycles), sorted(WELLS),
                 ", ".join(f"{m} {len(self.sites[(w, m)])} tiles in {WELLS[w][0]}/{WELLS[w][1]}"
                           for w in WELLS for m in ("iss", "pheno")))

        self._solve()

    # ------------------------------------------------------------------ pixels

    def _acq(self, modality: str, round_index: int | None) -> str:
        return self.pheno_dir if modality == "pheno" else self.rounds[round_index][0]

    def _path(self, well: int, modality: str, site: int,
              round_index: int | None) -> Path:
        return self.by_acquisition[self._acq(modality, round_index)][(well, site)]

    def _stack(self, path: Path) -> np.ndarray:
        """The `(c, y, x)` planes of one acquisition, as the instrument wrote them."""
        with self._nd2.ND2File(path) as f:
            return np.asarray(f.asarray())

    def _nuclear(self, path: Path) -> np.ndarray:
        return self._stack(path)[0]

    def _image_metadata(self, path: Path) -> tuple[dict, list[dict]]:
        """Everything one ND2 records about how it was acquired. See Q6.

        Returns what the whole acquisition shares and what each plane of it
        carries separately, because the exposure and the filter block differ per
        channel while the stage position and the timestamp do not.
        """
        with self._nd2.ND2File(path) as f:
            meta, frame = f.metadata, f.frame_metadata(0)
            volume, scope = meta.channels[0].volume, meta.channels[0].microscope
            position = frame.channels[0].position.stagePositionUm
            julian = frame.channels[0].time.absoluteJulianDayNumber
            camera, planes = _describe(f.text_info)
        stamp = (datetime(1970, 1, 1, tzinfo=timezone.utc)
                 + timedelta(seconds=(julian - _JULIAN_UNIX_EPOCH) * 86400))
        shared = {
            "source_file": path.name,
            "objective": scope.objectiveName or "",
            "numerical_aperture": scope.objectiveNumericalAperture,
            "magnification": scope.objectiveMagnification,
            "camera": camera,
            "pixel_size_um": float(volume.axesCalibration[0]),
            "stage_x_um": position.x, "stage_y_um": position.y, "stage_z_um": position.z,
            "timestamp": stamp.isoformat(),
            # 96 of the 272 images stamp the year 3189 and four acquisitions
            # stamp every image identically. The recorded value is written and
            # flagged rather than repaired.
            "timestamp_valid": bool(_VALID_FROM < stamp < _VALID_TO),
        }
        return shared, planes

    # --------------------------------------------------------------- geometry

    def _solve(self) -> None:
        """Measure every tile footprint, and the phenotyping-to-ISS scale."""
        self.frames: dict[tuple[int, str], geometry.Frame] = {}
        self.grids: dict[tuple[int, str], geometry.Grid] = {}
        self.registration: dict[int, dict] = {}
        self.origin: dict[int, np.ndarray] = {}

        for well in WELLS:
            row, column = WELLS[well]
            for mod in ("iss", "pheno"):
                sites = self.sites[(well, mod)]
                paths = [self._path(well, mod, s, 0) for s in sites]
                with self._nd2.ND2File(paths[0]) as f:
                    frame = geometry.orientation(f.metadata.channels[0].volume)
                stage = np.array([[m["stage_x_um"], m["stage_y_um"]]
                                  for m, _ in map(self._image_metadata, paths)])
                self.frames[(well, mod)] = frame
                self.grids[(well, mod)] = geometry.solve_grid(
                    frame, sites, stage, lambda s, w=well, m=mod: self._nuclear(
                        self._path(w, m, s, 0)),
                    n_px=TILE_PX, label=f"{row}/{column} {mod}")

            iss, pheno = self.grids[(well, "iss")], self.grids[(well, "pheno")]
            self.registration[well] = geometry.solve_modality(
                iss, pheno,
                lambda s, w=well: self._nuclear(self._path(w, "iss", s, 0)),
                lambda s, w=well: self._nuclear(self._path(w, "pheno", s, 0)),
                label=f"{row}/{column}")
            # The well frame is anchored on ISS tile 0 by the solve. Shift it so
            # the corner of everything the well holds sits at the origin, which
            # is what makes two wells comparable to read.
            corners = np.concatenate([self._corners(well, m) for m in ("iss", "pheno")])
            self.origin[well] = corners.min(axis=0)

    def _similarity(self, well: int, modality: str) -> tuple[np.ndarray, float, np.ndarray]:
        """The linear part of a tile-to-well transform, and the fit it folds in.

        Phenotyping carries the measured modality scale and offset. ISS is the
        frame those were measured against, so it carries neither and its linear
        part is the camera rotation alone.
        """
        scale, offset = 1.0, np.zeros(2)
        if modality == "pheno":
            scale = self.registration[well]["scale"]
            offset = np.asarray(self.registration[well]["offset_um"])
        return self.frames[(well, modality)].rotation * scale, scale, offset

    def _place(self, well: int, modality: str, *,
               positions: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        """`(translation, centre)` per tile, before the well frame is shifted.

        The translation puts the array's first pixel where the centre and the
        camera angle say it goes, which is what an RFC-5 affine needs.
        """
        grid = self.grids[(well, modality)]
        linear, scale, offset = self._similarity(well, modality)
        centres = (grid.solved if positions is None else positions) * scale + offset
        return centres - (linear @ np.full(2, grid.side_um / 2)), centres

    def _corners(self, well: int, modality: str) -> np.ndarray:
        """Every placed tile corner, which is what fixes the well frame origin."""
        linear, _, _ = self._similarity(well, modality)
        side = self.grids[(well, modality)].side_um
        box = np.array([[0.0, 0.0], [0.0, side], [side, side], [side, 0.0]])
        return np.concatenate([box @ linear.T + t
                               for t in self._place(well, modality)[0]])

    def _geometry(self, well: int, modality: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """`(linear, translation, centre)` per tile, in the shifted well frame."""
        linear, _, _ = self._similarity(well, modality)
        translation, centres = self._place(well, modality)
        return linear, translation - self.origin[well], centres - self.origin[well]

    def _nominal(self, well: int, modality: str) -> np.ndarray:
        """Where the instrument's own stage readout puts each tile centre."""
        nominal = self.grids[(well, modality)].nominal
        return self._place(well, modality, positions=nominal)[1] - self.origin[well]

    def geometry_report(self) -> dict:
        """The solve, as a JSON sidecar written beside the store."""
        return {f"{WELLS[w][0]}/{WELLS[w][1]}": {
            "iss": self.grids[(w, "iss")].report(),
            "pheno": self.grids[(w, "pheno")].report(),
            "modality": self.registration[w],
            "origin_um": self.origin[w].tolist()} for w in WELLS}

    def build(self) -> None:
        """The store, and the solve that placed its tiles, beside it.

        The geometry is re-measured on every build and never read back, so the
        sidecar is a report rather than an input: it is the only place the
        correlation scores and residuals behind the transforms are recorded.
        """
        super().build()
        report = self.out.parent / f"{self.out.name}.geometry.json"
        report.write_text(json.dumps(self.geometry_report(), indent=1))
        log.info("wrote %s", report)

    # ---------------------------------------------------------------- screen

    def write_screen_elements(self, root: zarr.Group) -> Iterable[dict]:
        src = pd.read_csv(self.barcodes)
        control = src["design"].str.endswith("_nt")
        obs = src.copy()
        # Derived: the delivery has no barcode column, no perturbation id and no
        # control flag. The read is a prefix of the guide, one base per cycle.
        obs["barcode"] = src["sgRNA"]
        obs[f"barcode_prefix_{len(ISS_CYCLES)}"] = src["sgRNA"].str.slice(0, len(ISS_CYCLES))
        obs["perturbation_id"] = src["gene_symbol"]
        obs["role"] = np.where(control, "control", "targeting")
        obs["control_type"] = np.where(control, "non-targeting", "")
        for c in ("design", "source", "gene_symbol", "perturbation_id", "role",
                  "control_type"):
            obs[c] = obs[c].astype("category")
        # The delivery has no unique row key: 82678 rows carry 80862 distinct
        # guides, so `sgRNA` cannot be the index. A synthetic one is minted
        # rather than deduplicating, because which duplicate to keep is not
        # this converter's call to make. See Q19.
        obs.index = pd.Index([f"guide{i}" for i in range(len(src))])
        yield self.table(root, "library", obs, element_id="library")
        log.info("library: %d rows, %d distinct guides, %d gene symbols, %d controls",
                 len(obs), src["sgRNA"].nunique(), obs["gene_symbol"].nunique(),
                 int(control.sum()))

    def screen_attributes(self) -> dict:
        # A raw store holds nothing to join the library to: no reads, no cells.
        # extension.md makes the empty list the correct value for that, not
        # evidence of an omission. See Q7.
        return {"sp-ops:relationships": relationships([])}

    # ----------------------------------------------------------------- plate

    def write_plates(self) -> Iterable[dict]:
        yield self.plate(
            f"plate1_{STAGE}", stage=STAGE, rows=PLATE_ROWS, columns=PLATE_COLUMNS,
            acquisitions=acquisitions(ISS_CYCLES),
            children=lambda plate: [self._write_well(plate, w) for w in WELLS])
        log.info("plate1_%s written", STAGE)

    def _write_well(self, plate: zarr.Group, well: int) -> dict:
        row, column = WELLS[well]
        return self.well(plate, row, column, scene=self.scene(self._transforms(well)),
                         children=lambda group: [
                             self._write_modality(group, well, "iss"),
                             self._write_modality(group, well, "pheno")])

    def _transforms(self, well: int) -> list[dict]:
        """One tile-to-well transform per raw channel array.

        Placing a raw tile costs one transform per channel, because a channel is
        its own element with its own frame (D5) and RFC-5 transforms apply to a
        whole array. That is 680 per well here. See Q40.
        """
        out = []
        for mod in ("iss", "pheno"):
            linear, translation, _ = self._geometry(well, mod)
            rounds = range(len(self.rounds)) if mod == "iss" else [None]
            for t, site in enumerate(self.sites[(well, mod)]):
                affine = [[*linear[0], translation[t][0]],
                          [*linear[1], translation[t][1]]]
                for r in rounds:
                    prefix = f"./{mod}/tiles/tile{site}"
                    if r is not None:
                        prefix += f"/round{r}"
                    for c in range(len(self._channels(mod))):
                        out.append({"type": "affine", "affine": affine,
                                    "input": zarr_ref(f"{prefix}/channel{c}", self.cs_id),
                                    "output": {"id": "well"}})
        return out

    # -------------------------------------------------------------- modality

    def _channels(self, modality: str) -> list[tuple[str, str]]:
        names = self.channels[self._acq(modality, 0)]
        return [(n, "nuclear" if i == 0 else ROLES[modality])
                for i, n in enumerate(names)]

    def _write_modality(self, well_group: zarr.Group, well: int,
                        modality: str) -> dict:
        sites = self.sites[(well, modality)]
        pixel_size = self.grids[(well, modality)].px
        rounds = None
        if modality == "iss":
            rounds = [(f"round{i}", i, cycle, f"iss-c{cycle}")
                      for i, (_, cycle) in enumerate(self.rounds)]

        return self.modality(
            well_group, modality,
            acquisition="pheno" if modality == "pheno" else None,
            children=lambda m: [self.raw_tiles(
                m, layout_id=f"{modality}-layout",
                layout=self._layout(well, modality),
                tiles=[(f"tile{s}", s, s) for s in sites],
                channels=self._channels(modality),
                rounds=rounds,
                read=lambda site, r, w=well, mo=modality: self._stack(
                    self._path(w, mo, site, r)),
                tables=[("image_metadata", self._metadata_table(well, modality))],
                edges=[edge("layout", "image_metadata",
                            on={"left": "tile", "right": "tile"}, cardinality="1:n")],
                pixel_size_um=pixel_size)])

    def _layout(self, well: int, modality: str) -> gpd.GeoDataFrame:
        """One polygon per field of view, measured, with the stage readout beside it.

        Nothing in the specification says whether a `layout` polygon is declared
        or measured, so the store carries both and the polygon is the measured
        one -- the transforms place the tiles there, and the two agreeing is
        what `check_layout_against_scene` looks for. See Q2 and Q49.
        """
        linear, _, centres = self._geometry(well, modality)
        nominal = self._nominal(well, modality)
        side = self.grids[(well, modality)].side_um
        rows = [{"tile": site, "site": site,
                 "measured_y_um": centres[i][0], "measured_x_um": centres[i][1],
                 "nominal_y_um": nominal[i][0], "nominal_x_um": nominal[i][1],
                 "geometry": _footprint(centres[i], linear, side)}
                for i, site in enumerate(self.sites[(well, modality)])]
        return gpd.GeoDataFrame(rows, geometry="geometry")

    def _metadata_table(self, well: int, modality: str) -> pd.DataFrame:
        """One row per acquired image plane, keyed by (tile, round, channel)."""
        channels = self._channels(modality)
        rounds = ([(i, cycle) for i, (_, cycle) in enumerate(self.rounds)]
                  if modality == "iss" else [(None, None)])
        rows = []
        for site in self.sites[(well, modality)]:
            for r, cycle in rounds:
                shared, planes = self._image_metadata(
                    self._path(well, modality, site, r))
                for c, (name, role) in enumerate(channels):
                    rows.append({
                        "tile": site, "site": site,
                        "round": -1 if r is None else r,
                        "cycle": -1 if cycle is None else cycle,
                        "acquisition": "pheno" if modality == "pheno" else f"iss-c{cycle}",
                        "channel": c, "channel_name": name, "role": role,
                        **planes[c], **shared})
        table = pd.DataFrame(rows)
        table.index = pd.Index([f"{t}_{r}_{c}" for t, r, c
                                in zip(table["tile"], table["round"], table["channel"])])
        # `source_file` too: 480 rows name 96 files, and the repetition is the
        # (tile, round) key the table is already indexed by.
        for c in ("acquisition", "channel_name", "role", "objective", "camera",
                  "binning", "filter_block", "source_file"):
            table[c] = table[c].astype("category")
        return table


def _field(block: str, key: str) -> str:
    """One `key: value` line out of an ND2 free-text block.

    The camera, the binning, the filter block and the autofocus offset are
    recorded only here, and the block is prose rather than a mapping. Some
    fields sit under a heading on the same line (`Camera Settings:   Binning:
    2x2`), hence the optional prefix; requiring it to end in a colon is what
    keeps `Name` from matching `Camera Name`.
    """
    match = re.search(rf"^[^\S\r\n]*(?:[\w ]+:[^\S\r\n]+)?{key}:[^\S\r\n]*(.+?)[^\S\r\n]*$",
                      block, re.MULTILINE)
    # The block uses CRLF and `$` stops after the CR, so strip it back off.
    return match.group(1).strip() if match else ""


def _describe(text: dict) -> tuple[str, list[dict]]:
    """The camera, and one record per picture plane, from `description`.

    `description` is the only block with per-plane settings: `capturing` numbers
    its samples but does not name them, and the structured metadata carries
    neither the filter block nor the autofocus offset.
    """
    head, *blocks = re.split(r"\r?\nPlane #\d+:\r?\n", text.get("description", "") or "")
    planes = [{
        "binning": _field(b, "Binning"),
        "exposure_ms": _number(_field(b, "Exposure")),
        # Recorded as `3 (Cy3)`, the turret position and the block mounted in
        # it. The position is a property of the microscope on the day, not of
        # the image, so only the block is kept.
        "filter_block": _parenthesised(
            _field(b, r"Nikon Ti2, FilterChanger\(Turret-Lo\)")),
        "pfs_offset": _number(_field(b, "PFS, offset")),
    } for b in blocks]
    return _field(head, "Camera Name"), planes


def _parenthesised(value: str) -> str:
    """`3 (Cy3)` -> `Cy3`; the whole string when it carries no parentheses."""
    match = re.search(r"\(([^)]*)\)", value)
    return match.group(1).strip() if match else value


def _number(value: str) -> float:
    """The leading number of a field such as `50 ms`, or NaN when there is none."""
    match = re.match(r"[-+]?\d*\.?\d+", value)
    return float(match.group()) if match else float("nan")
