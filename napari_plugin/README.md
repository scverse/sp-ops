# napari-sp-ops

Status: phase 0 of [PLAN.md](PLAN.md). The package installs, registers a napari reader for `.zarr` paths, and hands every group to napari-ome-zarr unchanged. sp-ops behaviour arrives in the later phases.

`napari-sp-ops` is a napari reader plugin for sp-ops stores, the SpatialData layout for optical pooled screening described in this repository's `docs/`. It depends on [napari-ome-zarr](https://github.com/ome/napari-ome-zarr) and adds what an sp-ops store needs on top of it: traversal of OME-NGFF RFC-8 collections, RFC-8 labels, channel names and colormaps from `sp-ops:channels`, a `round` slider for raw tiles, and tile placement from the `layout` shapes.

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

napari-ome-zarr and napari-sp-ops both accept `.zarr` directories, so napari asks which reader to use the first time you drop a store. Choose `napari-sp-ops` and tick the option to remember it for `.zarr`. Stores that are not sp-ops still open, because the plugin passes them to napari-ome-zarr. To skip the dialog from the command line:

```bash
napari --plugin napari-sp-ops path/to/screen.zarr
```

## Tests

```bash
UV_NO_SYNC=1 .venv/bin/python -m pytest tests -q
```

The suite builds a small synthetic screen on the fly. Two optional fixtures run the same checks on the conformant example stores when these variables point at the store roots:

```bash
export SP_OPS_PROCESSED_EXAMPLE=/path/to/processed_example.zarr
export SP_OPS_RAW_EXAMPLE=/path/to/raw_example.zarr
```

`tests/test_baseline_upstream.py` records how the pinned napari-ome-zarr behaves on sp-ops stores. A failure there means the upstream changed, and the matching code in `src/napari_sp_ops` needs a second look before the pin moves.
