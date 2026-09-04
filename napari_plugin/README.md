# napari-sp-ops

> **Disclaimer:** This plugin was heavily vibecoded during the [scverse x Cell Painting hackathon](https://github.com/scverse/2026_08_hackathon_cellpainting) in Berlin Buch, 2026. It is a starting point for discussion and needs refinement before anyone relies on it.

Status: phase 3 of [PLAN.md](PLAN.md). The package installs, registers a napari reader for `.zarr` paths and URLs, opens any node of an sp-ops store from a single channel image up to the screen root, and adds a navigator dock widget for picking wells and tiles. Layers carry channel names, colormaps, contrast limits, a `round` slider, tile placement from the `layout` polygons, and cell-table columns as label features. Groups outside an sp-ops store go to napari-ome-zarr unchanged.

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

A path is treated as sp-ops when the group, or any ancestor up to twelve levels above it, is an RFC-8 collection or carries an `sp-ops:*` key. Any other group is passed to napari-ome-zarr unchanged, so a plain OME-Zarr image still opens through this plugin.

What opens for a leaf node:

- An image splits into one layer per channel, named and coloured from `sp-ops:channels`. Singleton axes other than `y` and `x` are squeezed, so a stored `(1, 6, 1, Y, X)` image shows six 2D layers and no length-one sliders. The dataset `translation` is applied, which napari-ome-zarr drops.
- An RFC-8 label raster opens as a hidden labels layer at its own scale.
- A raster with a trailing three- or four-long `uint8` channel axis opens as one RGB layer.
- A `round` axis becomes a slider labelled `round`.

What opens for a collection. The reader follows the `nodes` list of the dropped collection and recurses, following the rules of the mapping table in [PLAN.md](PLAN.md):

- A raw `round` gives one layer per channel, named `round0 (cycle 1) DAPI`.
- A raw `tile` stacks its rounds lazily, one layer per channel with a `round` slider and `(unaligned)` in the name. Nothing is resampled.
- `tiles` places every tile at the minimum corner of its `layout` polygon and adds the layout as a shapes layer with the tile index as text.
- `merged` opens the image, every label raster hidden, RGBA rasters as RGB, and points such as `reads`. Tables open nothing.
- A `modality` opens `merged` when present, else `tiles`. A `well` opens every modality with the modality name as a layer prefix.
- A `plate` opens its first well by row then column and warns with the names of the others. A `screen` opens the `processed` plate when it has one, else the first plate.

Four settings are read from environment variables, with these defaults:

```bash
NAPARI_SP_OPS_LAYER_BUDGET=64   # stop recursing after this many napari layers and warn with the skipped node names
NAPARI_SP_OPS_STAGE=processed   # which plate stage a screen root opens
NAPARI_SP_OPS_PREFER=merged     # or tiles, for a modality that has both
NAPARI_SP_OPS_POINTS_CAP=2000000
```

Dropping a table directly warns and yields napari's "returned no data" error, because a table has no layer type. A table reaches napari through a labels layer instead. When the collection carries a computed edge in `sp-ops:relationships` between a labels element and a table on `value` or `label`, the table's `obs` columns become that labels layer's `features`, indexed by label value, so hovering a cell shows its barcode and measurements.

Contrast limits are estimated from the lowest pyramid level when that level has at most about a million elements. Larger images leave contrast to napari.

## Navigator

The `sp-ops navigator` dock widget (Plugins menu) shows a store as a tree: stage, plate, well, modality, tiles or merged, tile, round, down to the leaves. It expands one collection at a time, so a plate with hundreds of wells costs one metadata read per expanded node. Tick any nodes and press "Add selected" to open them through the reader, which is how you open one well of a plate without dropping its folder. The path field is prefilled from the first sp-ops layer already in the viewer. The widget needs a Qt binding, so install with the `qt` extra.

## Remote stores

Paths may be `http(s)://` or `s3://` URLs. Store detection walks up the URL to the first `.zarr` component, children open through the same store object, and layout and points parquet files are read through fsspec, so credentials given to the store carry over. The test suite serves the synthetic store over HTTP to cover this.

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
