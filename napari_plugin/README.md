# napari-sp-ops

> **Disclaimer:** This plugin was heavily vibecoded during the [scverse x Cell Painting hackathon](https://github.com/scverse/2026_08_hackathon_cellpainting) in Berlin Buch, 2026. It is a starting point for discussion and needs refinement before anyone relies on it.

Status: phase 0 of [PLAN.md](PLAN.md). The package installs, registers a napari reader for `.zarr` paths, and hands every group to napari-ome-zarr unchanged. sp-ops behaviour arrives in the later phases.

`napari-sp-ops` is a napari reader plugin for sp-ops stores, the SpatialData layout for optical pooled screening described in this repository's `docs/`. It depends on [napari-ome-zarr](https://github.com/ome/napari-ome-zarr) and is meant to add what an sp-ops store needs on top of it: traversal of OME-NGFF RFC-8 collections, RFC-8 labels, channel names and colormaps from `sp-ops:channels`, a `round` slider for raw tiles, and tile placement from the `layout` shapes.

## Install

The plugin is its own uv project. From this directory:

```bash
uv sync --group dev            # reader and tests, no Qt
uv sync --group dev --extra qt # adds PyQt6 so napari can open a window
```

Or into an existing napari environment:

```bash
pip install -e .
```

## Use

napari-ome-zarr and napari-sp-ops both accept `.zarr` directories, so napari asks which reader to use when you drop a store. It remembers the answer per folder, not per extension, so each node you drop from the same store asks again. To route every path inside a store to this plugin once, add the pattern `*.zarr*` for `napari-sp-ops` under the file extension readers in napari's plugin preferences (the `plugins.extension2reader` setting). From the command line:

```bash
napari --plugin napari-sp-ops path/to/screen.zarr
```

Anything napari-ome-zarr can open still opens through this plugin, because the group is passed to it unchanged. In phase 0 that means a multiscale image opens, and a collection such as a screen, plate, well or merged node fails with the "returned no data" error from napari's plugin loader, exactly as it does with napari-ome-zarr alone. Phase 2 adds the collections.

## Tests

```bash
UV_NO_SYNC=1 .venv/bin/python -m pytest tests -q
```

The suite builds a small synthetic screen on the fly and opens it through napari's Qt-free viewer model, so a run needs no display. Two optional fixtures run the same checks on the conformant example stores when these variables point at the store roots:

```bash
export SP_OPS_PROCESSED_EXAMPLE=/path/to/processed_example.zarr
export SP_OPS_RAW_EXAMPLE=/path/to/raw_example.zarr
```

`tests/test_baseline_upstream.py` records how the pinned napari-ome-zarr behaves on sp-ops stores. A failure there means the upstream changed, and the matching code in `src/napari_sp_ops` needs a second look before the pin moves.
