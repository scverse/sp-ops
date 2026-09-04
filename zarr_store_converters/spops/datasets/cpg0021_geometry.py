"""Where cpg0021_sample's fields of view actually are.

This delivery ships a position list -- every ND2 records its own stage
coordinates -- and the positions are wrong. They disagree with the images by up
to 68 px, consistently, because the pixel size the instrument reports is 1.0
percent too large in ISS and 0.4 percent in phenotyping. So the tile footprints
this module produces are measured from the pixels and the stage readout is kept
beside them, which is Q2 and Q49: nothing in the specification distinguishes a
declared footprint from a measured one, so the store records both.

Three things are solved here, and only the first is a solve in the usual sense:

* `orientation` reads the frame off one image. The instrument's
  `pixelToStageTransformationMatrix` has a negative determinant -- it mirrors x
  -- so taking the well x axis against stage x absorbs the mirror and leaves the
  camera mounting angle, 0.053 degrees, which every tile-to-well transform
  carries. A writer that read the recorded matrix and wrote a translation would
  place every tile mirrored.
* `solve_grid` cross correlates the nuclear channel over every overlapping pair
  of a modality's tiles and least squares the pairwise offsets into absolute
  positions, anchored on tile 0.
* `solve_modality` measures the phenotyping-to-ISS scale the same way. It is
  registration step 3 of layout.md done at `raw`, because a raw store places both
  modalities in one `well` frame and has no merged image to do it between. The
  scale is not the ratio of the recorded pixel sizes, which is exactly 2 (Q37).

Nothing here is cached. The numbers are re-measured on every build and written
beside the store as a report; see `report`.
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field

import numpy as np
from skimage.filters import difference_of_gaussians
from skimage.registration import phase_cross_correlation

log = logging.getLogger("spops")

# Accept a pair whose overlap correlates at least this well. The rejects are
# genuinely empty strips -- a corner overlap of a few hundred pixels over
# background -- not near misses.
NCC_FLOOR = 0.30
# Ignore an overlap thinner than this; below it the strip carries no nuclei.
MIN_OVERLAP_PX = 16
# Band pass, in pixels of the grid being solved, applied once per image before
# any correlation. An overlap strip is a tenth of a tile wide, so without this
# the correlation is dominated by the vignetting profile, which is identical in
# both tiles and peaks at zero shift whatever the truth is. On this dataset it
# takes the phenotyping residual from 4.6 px rms to 2.7 and the ISS residual
# from 2.8 to 2.3.
BAND_PASS_PX = (1.0, 20.0)
# Swaps the two axes of a 2x2, which is how an instrument matrix in (x, y)
# becomes one in the (y, x) order the store writes.
_YX = np.array([[0.0, 1.0], [1.0, 0.0]])


@dataclass
class Frame:
    """The pixel-to-well orientation, read from one image of a modality."""

    px: float                      # micrometres per pixel
    rotation: np.ndarray           # 2x2, (y, x); a rotation, determinant +1
    stage_sign: np.ndarray         # 2, (y, x); which stage axes the well frame flips

    def stage_to_well(self, stage_xy: np.ndarray) -> np.ndarray:
        """Stage coordinates as the ND2 reports them, (x, y), to well (y, x)."""
        return np.asarray(stage_xy, float)[..., ::-1] * self.stage_sign


@dataclass
class Grid:
    """One modality's tiles in one well, measured."""

    px: float
    tiles: list[int]
    nominal: np.ndarray            # (n, 2) (y, x) centres from the stage readout
    solved: np.ndarray             # (n, 2) (y, x) centres from the pixels
    n_px: int = 1480
    ncc: list[float] = field(default_factory=list)
    n_pairs_used: int = 0
    n_pairs_skipped: int = 0
    resid_rms_px: float = 0.0
    max_drift_px: float = 0.0

    @property
    def side_um(self) -> float:
        return self.n_px * self.px

    def report(self) -> dict:
        return {"px": self.px, "tiles": self.tiles,
                "nominal": self.nominal.tolist(), "solved": self.solved.tolist(),
                "n_pairs_used": self.n_pairs_used,
                "n_pairs_skipped": self.n_pairs_skipped,
                "ncc": [round(v, 4) for v in self.ncc],
                "resid_rms_px": self.resid_rms_px,
                "max_drift_px": self.max_drift_px}


def orientation(volume, stage_calibration: float | None = None) -> Frame:
    """The frame of one modality, from an ND2's own `volume` metadata.

    `volume.pixelToStageTransformationMatrix` is `pixel (x, y) -> stage (x, y)`
    in micrometres. Dividing by the pixel size leaves a mirrored rotation;
    flipping the stage axis whose diagonal entry is negative turns it into a
    rotation and defines the well frame at the same time.
    """
    px = float(stage_calibration or volume.axesCalibration[0])
    linear = np.asarray(volume.pixelToStageTransformationMatrix,
                        dtype=float).reshape(2, 3)[:, :2] / px
    sign = np.sign(np.diag(linear))
    rotation_xy = np.diag(sign) @ linear
    if not np.isclose(np.linalg.det(rotation_xy), 1.0, atol=1e-6):
        raise ValueError(
            f"pixelToStageTransformationMatrix is not a mirrored rotation: "
            f"determinant {np.linalg.det(rotation_xy)}")
    return Frame(px=px, rotation=_YX @ rotation_xy @ _YX, stage_sign=sign[::-1])


def _bandpass(image: np.ndarray) -> np.ndarray:
    """Nuclei without the illumination profile they sit on."""
    return difference_of_gaussians(np.asarray(image, np.float32), *BAND_PASS_PX)


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float64) - a.mean()
    b = b.astype(np.float64) - b.mean()
    den = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / den) if den > 0 else 0.0


def _overlap(a: np.ndarray, b: np.ndarray,
             shift: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """The strip of `a` and of `b` that image the same ground at `shift`.

    `shift` is where b's origin sits in a's pixel frame, (y, x), rounded.
    """
    dy, dx = (int(round(v)) for v in shift)
    ay0, by0 = max(dy, 0), max(-dy, 0)
    ax0, bx0 = max(dx, 0), max(-dx, 0)
    h = min(a.shape[0] - ay0, b.shape[0] - by0)
    w = min(a.shape[1] - ax0, b.shape[1] - bx0)
    if h < MIN_OVERLAP_PX or w < MIN_OVERLAP_PX:
        return None
    return (a[ay0:ay0 + h, ax0:ax0 + w], b[by0:by0 + h, bx0:bx0 + w])


def _measure(a: np.ndarray, b: np.ndarray,
             nominal_shift: np.ndarray) -> tuple[np.ndarray, float] | None:
    """Refine `nominal_shift` between two overlapping images, with a score.

    Returns the measured shift in pixels, (y, x), and the correlation of the
    overlap at that shift.
    """
    patches = _overlap(a, b, nominal_shift)
    if patches is None:
        return None
    # float64: the band pass leaves float32, and squaring a correlation peak of
    # a 1480 px strip overflows it inside the library's own error term.
    residual, _, _ = phase_cross_correlation(
        patches[0].astype(np.float64), patches[1].astype(np.float64),
        upsample_factor=10, normalization=None)
    measured = np.asarray(nominal_shift, float) + np.asarray(residual, float)
    refined = _overlap(a, b, measured)
    if refined is None:
        return None
    return measured, _ncc(*refined)


def solve_grid(frame: Frame, tiles: list[int], stage_xy: np.ndarray,
               read: callable, *, n_px: int = 1480, label: str = "") -> Grid:
    """Absolute tile positions from every overlapping pair of nuclear images.

    `read(tile_index)` returns that tile's nuclear channel. `stage_xy` is the
    instrument's own `(x, y)` readout per tile, in the order of `tiles`.
    """
    nominal = frame.stage_to_well(np.asarray(stage_xy, float))
    n, side = len(tiles), n_px * frame.px

    planes = {i: _bandpass(read(t)) for i, t in enumerate(tiles)}
    rows, rhs, used_ncc, skipped = [], [], [], 0
    for i, j in itertools.combinations(range(n), 2):
        delta = nominal[j] - nominal[i]
        if np.abs(delta).max() >= side:          # footprints do not overlap
            continue
        got = _measure(planes[i], planes[j], delta / frame.px)
        if got is None:
            continue
        shift, score = got
        if score < NCC_FLOOR:
            skipped += 1
            continue
        row = np.zeros(n)
        row[i], row[j] = -1.0, 1.0
        rows.append(row)
        rhs.append(shift * frame.px)
        used_ncc.append(score)

    # Anchored on tile 0, so the well frame has a definite origin before the
    # store shifts it to put the plate's own corner at zero.
    anchor = np.zeros(n)
    anchor[0] = 1.0
    A = np.vstack([np.asarray(rows), anchor]) if rows else anchor[None]
    b = np.vstack([np.asarray(rhs), nominal[0]]) if rhs else nominal[0][None]
    solved, *_ = np.linalg.lstsq(A, b, rcond=None)

    resid = (A[:-1] @ solved - b[:-1]) / frame.px if rows else np.zeros((0, 2))
    grid = Grid(px=frame.px, tiles=list(tiles), nominal=nominal, solved=solved,
                ncc=used_ncc, n_pairs_used=len(rows), n_pairs_skipped=skipped,
                resid_rms_px=float(np.sqrt((resid ** 2).sum(1).mean())) if len(resid) else 0.0,
                max_drift_px=float(np.abs(solved - nominal).max() / frame.px),
                n_px=n_px)
    log.info("  %s grid: %d tiles, %d pairs used, %d skipped, "
             "residual %.2f px rms, drift up to %.1f px", label, n,
             grid.n_pairs_used, grid.n_pairs_skipped, grid.resid_rms_px,
             grid.max_drift_px)
    return grid


def solve_modality(iss: Grid, pheno: Grid, read_iss: callable,
                   read_pheno: callable, *, label: str = "") -> dict:
    """The phenotyping-to-ISS similarity, measured on the nuclear channel.

    Each phenotyping tile that falls wholly inside an ISS tile is correlated
    against it at ISS sampling, which gives its centre in the ISS frame. A
    uniform scale and an offset are then fitted over those correspondences.
    Only tiles contained outright are paired: a partial overlap would need its
    own crop on both sides and add nothing, since the 24 contained pairs each
    well has already pin the scale to five significant figures.
    """
    step = int(round(iss.px / pheno.px))          # 2; both are powers of two apart
    iss_half, pheno_half = iss.side_um / 2, pheno.side_um / 2
    iss_planes = {i: _bandpass(read_iss(t)) for i, t in enumerate(iss.tiles)}

    src, dst, scores = [], [], []
    for j, _ in enumerate(pheno.tiles):
        centre = pheno.solved[j]
        inside = [i for i in range(len(iss.tiles))
                  if np.all(np.abs(centre - iss.solved[i]) + pheno_half <= iss_half)]
        if not inside:
            continue
        i = min(inside, key=lambda k: np.abs(centre - iss.solved[k]).max())
        # Sample the phenotyping tile down to ISS pixels, then band pass, so
        # both sides of the correlation are filtered at the same physical
        # scale. The residual scale is what we are after and it is far below one
        # pixel of this grid.
        small = _bandpass(read_pheno(pheno.tiles[j])[::step, ::step])
        origin = (centre - pheno_half) - (iss.solved[i] - iss_half)
        got = _measure(iss_planes[i], small, origin / iss.px)
        if got is None or got[1] < NCC_FLOOR:
            continue
        shift, score = got
        measured = (iss.solved[i] - iss_half) + shift * iss.px + pheno_half
        src.append(centre)
        dst.append(measured)
        scores.append(score)

    if len(src) < 3:
        raise ValueError(f"{label}: only {len(src)} modality correspondences")
    src_a, dst_a = np.asarray(src), np.asarray(dst)

    # dst = scale * src + offset, one isotropic scale over both axes.
    rows = np.zeros((2 * len(src_a), 3))
    rows[0::2, 0], rows[0::2, 1] = src_a[:, 0], 1.0
    rows[1::2, 0], rows[1::2, 2] = src_a[:, 1], 1.0
    fit, *_ = np.linalg.lstsq(rows, dst_a.reshape(-1), rcond=None)
    scale, offset = float(fit[0]), fit[1:]

    resid = np.abs(scale * src_a + offset - dst_a).max()
    resid_translation = np.abs(src_a + (dst_a - src_a).mean(0) - dst_a).max()
    out = {"n": len(src_a), "n_tiles": len(set(map(tuple, src_a.tolist()))),
           "scale": scale, "offset_um": offset.tolist(),
           "resid_max_um": float(resid),
           "resid_translation_only_max_um": float(resid_translation),
           "ncc_min": round(min(scores), 3), "ncc_max": round(max(scores), 3)}
    log.info("  %s modality: scale %.7f over %d tile pairs, residual %.2f um "
             "against %.2f um for a translation alone", label, scale, len(src_a),
             resid, resid_translation)
    return out
