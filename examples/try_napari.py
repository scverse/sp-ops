"""
Open one of the sp-ops-conformant example stores in a real, interactive napari window,
via napari-spatialdata.

Same dependency as try_sp_ops_rfc8.py: an experimental `spatialdata` branch (the
`vibecoded-experiment/sp-ops-example` stack, https://github.com/LucaMarconato/spatialdata/pull/8
and below), plus `napari-spatialdata` and a Qt binding (PyQt5 or PyQt6) installed in the same
environment, e.g.:

    uv pip install -e ".[extra]"   # from the spatialdata checkout, pulls in napari-spatialdata

Then, from that checkout:

    .venv/bin/python /path/to/sp-ops/examples/try_napari.py

This opens a real window (do not set QT_QPA_PLATFORM=offscreen/minimal for this -- on macOS
that backend has no working OpenGL context and napari segfaults on `Viewer()` construction;
a normal, on-screen Qt platform works fine). Close the window, or Ctrl-C in the terminal, to
exit -- `Interactive(...)` blocks in napari's own event loop until then.

Once it's open, the "SpatialData" dock widget on the left lists every element by its
hierarchical name; double-click one to add it as a layer.
"""

from pathlib import Path

import spatialdata as sd
from napari_spatialdata import Interactive

OPS_DIR = Path("/Users/macbook/ssd/biodata/ops/spops_conformant")


def main() -> None:
    sdata = sd.read_zarr(OPS_DIR / "Biohub_OPS0001_spops.zarr")
    print(f"read {len(sdata._elements)} elements, opening napari...")
    Interactive(sdata)  # blocks until the window is closed


if __name__ == "__main__":
    main()
