# napari plugin for sp-ops stores

Status: phase 2 implemented (PR #4 for phase 0, stacked PRs for phases 1 and 2). Written 2026-09-04 against napari-ome-zarr 0.10.0, napari 0.9.0 and the sp-ops specification at commit 362486d. The failure table was first measured on zarr 3.1.6 under Python 3.11 and is re-checked by the phase 0 baseline test on zarr 3.3.0 under Python 3.12.

## Summary

Build `napari-sp-ops`, a small napari reader plugin that depends on napari-ome-zarr and adds the five things an sp-ops store needs and napari-ome-zarr lacks. Those are traversal of OME-NGFF RFC-8 collections, detection of RFC-8 labels, layer names and colormaps from `sp-ops:channels`, a `round` slider for raw multi-round tiles, and tile placement from the `layout` shapes. Everything generic about RFC-8 is written in one module so it can be offered upstream to napari-ome-zarr and deleted here once released.

The plugin is a superset reader. When the dropped path is not inside an sp-ops store, it hands the group to napari-ome-zarr unchanged. A user can therefore make `napari-sp-ops` the default reader for `.zarr` without losing anything.

## What breaks today

The released napari-ome-zarr reader was run headless on every node kind of the two conformant example stores (the processed example converted from the Biohub portal subset, and the raw example converted from a two-well nd2 subset). The reader was called directly, so this is what drag-and-drop would produce before any viewer error handling.

| Node dropped | Result |
| --- | --- |
| screen, plate, well, modality, tiles, tile, round, merged collections | the reader claims the path and returns zero layers; napari shows nothing |
| table (`library`) and shapes (`layout`) | zero layers |
| processed `merged/image`, axes T,C,Z,Y,X | six image layers with no names and no colormaps; the singleton T and Z axes become sliders of length one; channel split and 0.325 µm scale are correct |
| the twelve label rasters such as `cell_seg` | opened as image layers, one per channel, not as labels |
| the RGBA overlays (`grid_overlay`, `iss_gene_image`), axes y,x,c | opened as four grayscale image layers instead of one RGB image |
| raw channel multiscale, axes y,x or z,y,x | opens with the right scale as one unnamed layer; there is no way to see a round's five channels or a tile's eleven rounds together |

Two causes explain the whole table. First, `read_ome_zarr` dispatches on six specs (Labels, Label, Bioformats2raw, Multiscales, Plate, Scene), and none of them is an RFC-8 `collection`. Second, RFC-8 puts `plate`, `well`, `labels`, `scene` and every `sp-ops:*` key under `ome.attributes`, but napari-ome-zarr looks for them directly under `ome`. Only `multiscales`, which RFC-8 keeps at the top of `ome`, is found. Labels are missed for the same reason plus one more. napari-ome-zarr requires the pre-RFC-8 `image-label` key, and sp-ops labels carry the RFC-8 `labels.source` reference instead.

Two more mismatches matter for later phases. RFC-8 coordinate systems are identified by `id` and transformations reference them with a `Reference` object (`id` plus a `path` object). napari-ome-zarr's `Scene` code expects RFC-5's `name` and a string path. Neither example store writes a `scene` yet, so this only affects tile placement once writers add stitching transforms.

## Scope

The user-facing unit is any node of an sp-ops store, dropped as a directory or opened by path or URL. An "sp-ops image object" here means a multiscale group carrying `sp-ops:*` attributes, together with the collections that contain it. The plugin opens the dropped node and everything image-like beneath it, as napari image, labels, points and shapes layers, with the names, colormaps, scale and placement the metadata dictates.

Out of scope for this plan. Tables have no napari layer type and are only used, in phase 3, to feed a labels layer's `features`. Nothing is written back. No registration is computed. Reading through a `SpatialData` object is deferred, because the released `spatialdata` reader cannot open these stores (assumptions A4 and A5 in the specification are not in a release), and napari-spatialdata's reader is a one-line call to that reader followed by its `Interactive` widget. When the hierarchical branch lands, napari-spatialdata becomes the natural home for table and query interaction, and this plugin stays the pixel reader.

## What is reused and what is new

Reused from napari-ome-zarr 0.10, imported from `napari_ome_zarr.ome_zarr_reader`. The `Multiscales` spec supplies the dask pyramid, the axes, units, scale and affine logic, including the `output.name` handling for 0.6 datasets. `transforms_to_affine` composes scale, translation, rotation, affine and sequence transforms into a napari `Affine`. `Multiscales` reads only the first transformation of a dataset, so a dataset `translation` such as the processed example's 15600 µm offset is dropped, and the plugin has to compose it itself. The `Label` spec supplies colors and properties parsing. `Scene` supplies the transformation graph, usable once RFC-8 references are adapted to RFC-5 form. The `napari_get_reader` entry point already opens local paths and URLs through zarr's fsspec stores.

New in this plugin. An attributes lookup that reads `ome.attributes` for RFC-8 nodes and falls back to `ome` for older data. A `Collection` spec that follows each entry in `nodes` by its `path` and recurses. Labels detection on RFC-8 `labels`. sp-ops semantics, meaning channel names and roles, round stacking, stage and modality selection, and layout-based placement. Squeezing of singleton non-spatial axes. RGBA detection. Parquet readers for points and shapes.

Upstream candidates, generic and not sp-ops specific, in the order they should be proposed. One, the `ome.attributes` lookup together with RFC-8 `labels` detection. Two, the `Collection` spec. Three, RFC-8 `Reference` support in `Scene`. Each is prototyped here behind one module, then proposed as its own pull request to napari-ome-zarr. When a pull request is released, the local copy is deleted and the version pin is raised.

## Layer mapping per node kind

The rule for every collection is the same. Open the node that was dropped, recurse to its leaves, and stop when a layer budget is reached. The budget is a setting with a default of 64 layers, and the reader logs what it skipped.

| Node kind | What opens | Layer details |
| --- | --- | --- |
| channel multiscale in `raw`, axes y,x or z,y,x | one image layer | name from `sp-ops:channels[0].name`, colormap from its role, scale from the dataset transform |
| round collection in `raw` | one image layer per channel | names carry the round index and cycle value, for example `round0 (cycle 1) DAPI_SBS`; channels overlay at the origin because raw channels are unaligned and no transform exists |
| tile collection in `raw`, several rounds | one image layer per channel index with a `round` slider | rounds are stacked lazily with dask when every round of a channel index has the same shape and dtype; the cycle values and acquisition ids go into layer metadata; the layer name says `unaligned`; if shapes differ, fall back to one layer per round and channel |
| tile collection in `processed` | image plus its points | `image` splits on `c`, keeps `round` as a slider labelled `round`; `peaks` becomes a points layer |
| merged collection | image, every label raster hidden, points | `image` as above; RFC-8 labels become labels layers, hidden by default as napari-ome-zarr does; RGBA rasters (the processed example has three) become one RGB image layer each; `reads` becomes a points layer |
| tiles collection | every tile placed in the well frame, plus the layout | tiles are translated by the `scene` transform when present, else by the minimum corner of their `layout` polygon; `layout` becomes a shapes layer of polygons with the `tile` index as a feature |
| modality collection | `merged` if present, else `tiles` | a setting flips the preference |
| well collection | every modality | ISS and phenotyping overlay in physical units; without a modality registration transform they share only the origin |
| plate collection | the first well by row then column, with a warning naming the other wells | the phase 3 navigator is the way to pick a well; a stitched plate grid like napari-ome-zarr's HCS view is not planned, because sp-ops wells have no fixed field grid |
| screen collection | the `processed` plate of the first physical plate, else `raw`, then as plate | the stage preference is a setting |
| table or shapes or points leaf dropped directly | points or shapes layer; a table opens nothing and warns | |

Axis handling for every image. Singleton axes whose type is not `space` y or x are squeezed, and scale, translation, axis labels and units are trimmed to match. The specification's decision D6 says writers omit such axes; the processed example keeps a singleton T and Z, so the reader tolerates them. Axis names are lower-cased for the labels shown in napari. The `round` axis has RFC-5 type `array`; napari-ome-zarr passes unknown axis types through as sliders, which is the wanted behaviour, and phase 1 confirms it on a synthetic store because neither example store has a processed multi-round image.

Colormaps by role. `nuclear` is blue. `base` takes a fixed four-entry palette by array position. `stain` alternates green and magenta. `other`, and any channel whose `channel_type` says `labelfree` or `predicted`, is gray. The palette lives in one table in the code. Contrast limits are left to napari in phase 1 and estimated from the lowest pyramid level in phase 3.

## Decisions

D1. A separate package that depends on napari-ome-zarr, not a fork and not a pull-request-only effort. The released 0.10.0 already has the zarr v3 architecture and the dependency set (`napari>=0.6`, `zarr>=3.1.5`) this plan builds on. sp-ops semantics would never be accepted upstream, and RFC-8 is still a draft, so the generic parts also need a home while they wait. Rejected: forking, because two readers for the same metadata drift apart.

D2. Superset reader with delegation. Both plugins accept `.zarr` directories, so napari asks the user to choose a reader when a store is dropped. For directories napari remembers that choice per folder, not per extension, so every node dropped from the same store asks again. The way out is the `plugins.extension2reader` preference with the pattern `*.zarr*` assigned to `napari-sp-ops`, or the `--plugin` flag. Delegating non-sp-ops groups to `read_ome_zarr` makes that preference safe. The README documents both.

D3. Detection walks up. A path is inside an sp-ops store when the group itself, or any ancestor up to the store root, carries an `sp-ops:*` key under `ome.attributes` or has `ome.type` equal to `collection`. The walk is bounded at twelve levels, which exceeds the deepest layout in the specification. For URLs the walk shortens the URL path. Phase 0 confirmed, on zarr 3.1.6 and 3.3.0, that zarr-python 3 opens `plate/A/1` when `plate/A` has no `zarr.json`, because the example stores nest the well name `A/1` as two directories with metadata only on the second.

D4. Traversal follows `nodes[].path.path`, never directory listing. Names are opaque by specification decision D3, and node types (`collection`, `multiscale`, `sp-ops:table`, `sp-ops:shapes`, `sp-ops:points`) come from the descriptor. A child referenced by path outside the store is opened by that path, which is how RFC-8 lets plates live in other stores.

D5. Rounds are stacked for viewing only. The stacked layer is a viewer convenience over unaligned data, and its name says so. Nothing is resampled.

D6. Placement uses `scene` first and `layout` second. When a modality or well collection has a `scene`, its transformations are converted from RFC-8 references to the RFC-5 form napari-ome-zarr's `Scene` expects, and that code places the tiles. Otherwise each tile is translated to the minimum corner of its `layout` polygon, in micrometres, after swapping the polygon's x,y order to napari's y,x. The raw example's layout was built from stage positions on the assumption that the position is the field centre, which the conformance notes flag as unverified, so the placement is only as good as that assumption.

D7. Vector data through pyarrow and shapely, not geopandas. Shapes are GeoParquet polygons in WKB and points are plain Parquet with x and y columns. Shapely decodes WKB and pyarrow reads both files, so geopandas and its GEOS stack stay out of the dependency list. Points layers are capped at two million rows with a warning; the processed example's full-well cell table has about 267 thousand rows, and read tables in the specification's running example have about 600 thousand.

D8. Python 3.12 for development, `requires-python >= 3.11` in the package. zarr 3.2 and later, spatialdata 0.8 and ome-zarr 0.19 all require 3.12, and the spatialdata path is the likely next step. On 3.11 the resolver falls back to zarr 3.1.6, which napari-ome-zarr accepts. The plugin is its own uv project under `napari_plugin/` with its own lock, not a member of the docs project, because the napari dependency tree should not enter the documentation build.

D9. Tests do not depend on ome-zarr-py. napari-ome-zarr's own tests write fixtures with ome-zarr-py, which now requires 3.12 and pulls ome-zarr-models. The synthetic fixture here is written with zarr directly, using RFC-8 group and multiscale writers adapted from the conformance conversion into the test package. The two real example stores are optional fixtures selected by an environment variable and skipped when absent.

D10. The public surface of napari-ome-zarr that this plugin imports is not declared public. The pin is `napari-ome-zarr>=0.10,<0.11`, every import from it goes through one adapter module, and the baseline test in phase 0 detects behaviour changes on upgrade.

D11. The plugin reads on-disk paths and URLs only. It does not accept a `SpatialData` object, and it will not until the hierarchical SpatialData reader is released. At that point the question of whether this plugin or napari-spatialdata should take a `SpatialData` object is reopened as its own decision. Until then napari-spatialdata is untouched and this plugin stays the pixel reader.

D12. RGBA detection wins over the RFC-8 `labels` key. A multiscale whose last axis is a channel axis of length three or four with `uint8` data opens as one RGB image layer, whatever else its attributes say. The example store's overlays carry `labels.source` because they were derived from the image, and `sp-ops:label_kind` is only a hint, so the array shape is the reliable signal.

D13. The reader composes every `coordinateTransformations` entry of the full-resolution dataset, in order, and squeezes singleton non-`y`,`x` axes out of the data and the transforms before composing. napari receives `scale` and `translate`; rotation or shear in a dataset transform is dropped with a warning until the `scene` work in phase 2 needs it.

D14. Detection opens the dropped group, then up to twelve ancestors by shortening the path string, and claims the path when any of them is an RFC-8 collection or carries an `sp-ops:*` key under `ome.attributes`. Ancestors that fail to open are skipped, not treated as the top, because `plate/A` has no metadata.

D15. Colormap palette. `nuclear` is `blue`; `base` cycles `green`, `red`, `magenta`, `cyan` in array order; `stain` alternates `green` and `magenta`; everything else, and any channel whose `channel_type` is `labelfree` or `predicted`, is `gray`. The table is the four constants at the top of `channels.py`.

D16. Settings are a frozen dataclass with defaults in `settings.py`, overridden by `NAPARI_SP_OPS_LAYER_BUDGET`, `NAPARI_SP_OPS_STAGE`, `NAPARI_SP_OPS_PREFER` and `NAPARI_SP_OPS_POINTS_CAP`. napari has no settings surface for reader plugins, and a widget-side settings panel is not worth its weight until the navigator in phase 3 exists.

D17. Placement in phase 2 uses the `layout` polygons only. A `scene` on a collection is reported with a warning and not applied. The RFC-8 `Reference` adapter for napari-ome-zarr's `Scene` code waits for a store that writes a `scene`, which neither example does, and lands with the upstream work in phase 4. This narrows D6 for now.

D18. The traversal never opens a table group. A zarr v3 collection cannot list a zarr v2 AnnData child, and a table has no layer type. Phase 3 reads a table only through a computed edge to a labels element, by path.

## Package layout

```text
napari_plugin/
├── PLAN.md
├── README.md                  # install, the reader-choice dialog, --plugin flag
├── pyproject.toml             # napari-sp-ops, hatchling, requires-python >=3.11
├── src/napari_sp_ops/
│   ├── napari.yaml            # one reader contribution, *.zarr, accepts_directories
│   ├── _reader.py             # napari_get_reader: detect sp-ops, else delegate
│   ├── upstream.py            # the only module importing napari_ome_zarr internals
│   ├── rfc8.py                # attributes lookup, Collection traversal, Reference adapter
│   ├── nodes.py               # Node wrapper and kind classification from attributes
│   ├── traverse.py            # per-kind collection rules and the layer budget
│   ├── settings.py            # defaults and environment overrides
│   ├── channels.py            # sp-ops:channels to names and colormaps
│   ├── images.py              # multiscale group to image, labels or rgb LayerData
│   ├── rounds.py              # raw round stacking
│   ├── placement.py           # layout and scene to per-tile translations
│   ├── vector.py              # parquet points and shapes to LayerData
│   └── _widget.py             # phase 3 navigator
└── tests/
    ├── conftest.py            # synthetic store fixture, optional real-store fixtures
    ├── test_baseline_upstream.py
    ├── test_images.py
    ├── test_collections.py
    └── test_vector.py
```

Each module stays under about 300 lines. Settings (layer budget, stage preference, merged versus tiles, points cap) are a small pydantic model read from napari's plugin settings, with defaults in one place.

## Phases

Each phase lands as its own pull request, and the requests form a stack. The branch for a phase is cut from the branch of the phase before it, and its pull request targets that branch until the parent merges, after which it is retargeted to `main`. Phase 0 is the base of the stack and targets `main` directly.

Phase 0, scaffold and baseline. Create the package, the uv environment on Python 3.12 with `pyqt6` as an optional extra, and a reader that only delegates to napari-ome-zarr. Turn the probe behind the table above into `test_baseline_upstream.py`, so the failure modes are recorded in the repository and any change in upstream behaviour fails a test. Confirm the implicit-group question in D3. Acceptance: the plugin installs, napari lists it, and every baseline assertion passes.

Phase 1, leaf images. Implement the `ome.attributes` lookup, RFC-8 labels detection, `sp-ops:channels` names and colormaps, the singleton squeeze, and RGBA detection. Acceptance on the processed example: `merged/image` opens as six named layers with colormaps, no length-one sliders, and the store's 15600 µm translation applied; `cell_seg` opens as a hidden labels layer at 0.65 µm; `grid_overlay` opens as one RGB layer. On the raw example: a channel multiscale opens with its channel name. On the synthetic store: an image with axes round,c,y,x opens with a slider labelled `round`.

Phase 2, collections. Implement `Collection` traversal, the per-kind rules in the mapping table, round stacking, layout placement, the layout shapes layer, and points. Acceptance on the raw example: dropping a tile gives five layers with an eleven-step `round` slider; dropping `tiles` gives both tiles side by side at 1.3 µm with the layout polygons over them; dropping the well adds the phenotyping tiles inside the ISS footprint at 0.325 µm. On the processed example: dropping `merged` gives the image, twelve hidden labels layers, and the three RGBA overlays; dropping the screen root gives the same via the stage rule. In both, the layer budget stops recursion with a logged list.

Phase 3, navigation and features. A dock widget shows the store as a tree (stage, plate, well, modality, tiles or merged, tile, round) with checkboxes and an add button, so a user opens one well of a plate without re-dropping. When a merged collection has a computed edge from a labels element to a table on `value` and `label`, the table's `obs` columns become the labels layer's `features`. Contrast limits come from the lowest pyramid level. Opening by HTTP or S3 URL is exercised against one example store served locally.

Phase 4, upstream, ongoing. Open the three pull requests listed above against napari-ome-zarr, each with the corresponding synthetic-store test. Track them in the README. Delete local code as releases land.

## Risks and open questions

- napari-ome-zarr internals may change again. The module was rewritten off ome-zarr-py in 2026, and the pin in D10 plus the baseline test are the mitigation. If the import surface breaks, `upstream.py` is the only file to fix.
- The reader-choice dialog returns for every node of a store until the user sets the `*.zarr*` pattern preference. A manifest cannot claim precedence, so documentation is the only fix.
- The `round` axis type `array` and the axis name `round` have not been seen by napari-ome-zarr's tests. Phase 1 checks them on the synthetic store first.
- Tile placement from `layout` depends on the field-centre assumption noted in the raw conformance report and on there being no rotation. A `scene` written by the processing pipeline supersedes it.
- Well names such as `A/1` are hierarchical paths, two zarr groups with metadata on the second. The reader follows `path` and never parses names, so it needs no special case beyond the implicit-group check in D3.
- `sp-ops:channels` in the processed example carries extra keys (`channel_type`, `description`) and the labels carry `sp-ops:label_kind`, neither in the registry. The reader tolerates unknown keys and uses `label_kind` only as a hint.
- Layers in one well overlay in physical units only when the modality registration transform exists. Without it, phenotyping and ISS share an origin and nothing else, which the layer names should say.

## Sources

- napari-ome-zarr, ome/napari-ome-zarr on GitHub, version 0.10.0 released 2026-08-12. https://github.com/ome/napari-ome-zarr
- ome-zarr-py, ome/ome-zarr-py on GitHub, version 0.19.1 released 2026-09-02. https://github.com/ome/ome-zarr-py
- napari-spatialdata, scverse/napari-spatialdata on GitHub, version 0.7.2 released 2026-07-02. https://github.com/scverse/napari-spatialdata
- napari reader plugin contribution reference. https://napari.org/stable/plugins/building_a_plugin/guides.html#readers
- OME-NGFF RFC-8, collections. https://ngff.openmicroscopy.org/rfc/8/index.html
- OME-NGFF RFC-5, coordinate systems and transformations. https://ngff.openmicroscopy.org/rfc/5/index.html
- Hierarchical SpatialData, experimental branch by Luca Marconato (EMBL). https://github.com/scverse/spatialdata/tree/vibecoded-experiment/hierarchical-spatialdata
- sp-ops specification pages `layout.md`, `extension.md`, `design-decisions.md`, `open-questions.md` in this repository.
- Conformance conversion notes and the two example stores, produced 2026-09-03 and 2026-09-04 in the hackathon workspace; referenced by the tests through an environment variable.
