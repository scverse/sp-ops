# Features

A feature is a measurement of an instance. Instances exist at several granularities, and every granularity uses the same structure: a table whose rows describe one element at the same level of the hierarchy, linked to it by an edge in `sp-ops:relationships` (see [](joinable-components.md)).

| Granularity | Instance | Linked element | Typical content |
| --- | --- | --- | --- |
| cell | one label of a compartment | labels (`nuclei`, `cells`, `cytosol`, ...) | morphology, intensity, texture; the unit of biological interpretation |
| tile | one field of view | `layout` shapes of a modality | vignetting, focus, signal to noise; quality control |
| well | one well | `wells` shapes on the plate collection | stitching residuals, seeding gradients; quality control |
| plate | one plate | none | batch metadata |

Compartments are not fixed. A writer MAY segment any set of compartments and MAY store features for each. A compartment other than the cell may have several instances per cell, for example the nuclei of a multinucleated cell or mitochondria, so compartments are not nested under cells in the hierarchy. Each compartment has its own labels and its own feature table, and membership is a column on that table (`cell_label` in the examples) joined to the `cells` labels by an edge.

## Cell features

A cell feature table is a child of the tile or merged collection whose labels it describes. The link to the labels is an edge on that collection: the table's label column against the pixel value of the labels element.

```text
plate1_processed/A/1/pheno/merged/
├── image
├── nuclei               # labels (y, x), int32
├── cells                # labels (y, x), int32
├── nuclei_features      # table; one row per nucleus; obs has label, cell_label
└── cells_features       # table; one row per cell; obs has label
```

```json
"sp-ops:relationships": {
  "version": "0.2.0-draft",
  "edges": [
    {"from": "cells", "to": "cells_features", "method": "join",
     "on": {"left": "value", "right": "label"}, "status": "computed", "cardinality": "1:1"},
    {"from": "nuclei", "to": "nuclei_features", "method": "join",
     "on": {"left": "value", "right": "label"}, "status": "computed", "cardinality": "1:1"},
    {"from": "nuclei_features", "to": "cells", "method": "join",
     "on": {"left": "cell_label", "right": "value"}, "status": "computed", "cardinality": "n:1"}
  ]
}
```

`obs` holds the label column and categorical annotations such as the assigned `barcode`. `var` holds one row per feature with its name and, optionally, the channel and compartment it was measured on. Cell to cell relations such as a k-nearest-neighbour graph go in `obsp`, following the scanpy convention.

```text
SpatialData object
├── image: [Image] DataArray[cyx] (5, 8192, 8192)
├── nuclei: [Labels2D] DataArray[yx] (8192, 8192)
├── cells: [Labels2D] DataArray[yx] (8192, 8192)
├── nuclei_features: [Table] AnnData (28102, 1400)   # obs: label, cell_label
└── cells_features: [Table] AnnData (27488, 1400)    # obs: label, barcode; obsp: spatial_connectivities
with element relationships:
    ▸ cells ══(value / label)══ cells_features
    ▸ nuclei ══(value / label)══ nuclei_features
    ▸ nuclei_features ══(cell_label / value)══ cells
```

:::{admonition} The SpatialData annotation triple is legacy
:class: note

Released SpatialData links a table to an element with `region`, `region_key`, and `instance_key` in the table's `spatialdata_attrs`. That mechanism is being replaced by relationship edges, which SpatialData intends to adopt beyond OPS data. This specification uses edges only. A writer MAY also fill the triple for readers that still need it, but nothing here depends on it.
:::

## Tile and well features

Tiles of different modalities are imaged at different magnifications and are not directly comparable, so by default each modality's `tiles/` collection holds its own `tile_features` table, one row per tile, linked to that modality's `layout` by an edge on the `tiles/` collection.

```text
plate1_processed/A/1/iss/tiles/
├── layout               # shapes: one polygon per tile, column tile
├── tile_features        # table: one row per tile
└── tile0/ ...
```

```json
{"from": "layout", "to": "tile_features", "method": "join",
 "on": {"left": "tile", "right": "tile"}, "status": "computed", "cardinality": "1:1"}
```

`well_features` links to a `wells` shapes element on the plate collection in the same way. Nothing else changes with granularity, and nothing restricts these tables to quality control.

## Merged and split tables

Every table above is processed data, and there is more than one valid way to store it. A table can be written once per tile, merged collection, or modality (split) or once for a well, plate, or the whole screen (merged). A writer MAY split or merge tables at will and store them at any level, as long as an edge on the lowest collection containing both ends links each table to the element it describes. A reader MUST handle both. Three encodings of a merged table are in use:

1. `region_key` and `instance_key` columns. This is the legacy SpatialData encoding described above. Selecting one source means filtering on `region_key` before indexing on `instance_key`, and with several nested levels the filter has several terms. It is documented for existing stores and will not be carried forward.
2. One index column per source table, `NaN` elsewhere. Selecting one source means picking its column and dropping `NaN` rows. The column count grows with the number of sources.
3. A hierarchical unique id column, for example `A-1_pheno_merged_4213`, next to plain `well`, `modality`, `site` (a tile index or `merged`), `label` columns. The id indexes the whole merged table and the plain columns filter it. The column count is fixed.

This specification will adopt one of the last two as the default for merged tables; the choice is open. Split tables need none of this; each is indexed by its label column alone.
