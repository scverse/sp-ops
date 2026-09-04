"""
Manual smoke test for reading sp-ops-conformant stores: round/t axes, relationships, the
RFC-8 collection reader, and the nested/truncated SpatialData repr.

These aren't implemented in a release of `spatialdata` -- they're a stack of experimental
branches on https://github.com/LucaMarconato/spatialdata:
https://github.com/LucaMarconato/spatialdata/pull/1 (through #9), topped by
`vibecoded-experiment/sp-ops-version-fallback`. `pyproject.toml` pins that branch's tip as
this repo's `spatialdata` dependency, so from a checkout of this repo:

    uv run python examples/try_sp_ops_rfc8.py

Its captured output lives alongside it in try_sp_ops_rfc8_output.txt.

Requires the two example sp-ops-conformant stores built for the spec's compliance review, at
OPS_DIR below -- not shipped with this repo.

Note: neither real store actually carries `round` as an *array axis* -- P001 is `raw`
(round is a folder level, not a dim) and Biohub is single-round `processed` data. So this
script also builds a tiny synthetic (round, c, y, x) image directly, to exercise that part
of the axis support for real.
"""

from pathlib import Path

import numpy as np

import spatialdata as sd
from spatialdata.models import Image2DModel

OPS_DIR = Path("/Users/rushin.gindra/Documents/Research/OPS-sandbox/stores/biohub_example")


def main() -> None:
    # --- RFC-8 reader: two real conformant stores ---
    # --- repr: nested, truncated tree instead of a flat dump of all elements ---
    # p001 = sd.read_zarr(OPS_DIR / "P001_spops.zarr")
    # print(f"P001_spops.zarr (raw):        {len(p001._elements)} elements")
    # print(p001)

    biohub = sd.read_zarr(OPS_DIR / "biohub_example.zarr")
    print(f"biohub_example.zarr:    {len(biohub._elements)} elements")
    print(biohub)

    # --- relationships: sp-ops:relationships resolved from the Biohub store ---
    print("\nsp-ops:relationships edges (Biohub):")
    for edge in biohub.relationships:
        print(f"  {edge.from_}  --{edge.method}({edge.status})-->  {edge.to}")
    print("check():", biohub.relationships.check(biohub) or "(no problems)")

    # --- round/t axes: a synthetic (round, c, y, x) image, since neither ---
    # --- real store above has `round` as an array axis (see module docstring) ---
    data = np.zeros((3, 2, 8, 8), dtype="uint16")
    img = Image2DModel.parse(data, dims=("round", "c", "y", "x"))
    print(f"\nsynthetic round-axis image dims: {img.dims}, shape: {img.shape}")
    print("img.sel(round=1, c=0) shape:", img.sel(round=1, c=0).shape)


if __name__ == "__main__":
    main()
