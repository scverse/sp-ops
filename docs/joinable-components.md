# Joinable components

An optical pooled screen links pixels to perturbations through several elements. This page names the ones every screen has and defines how they join. The list is not exhaustive, and the column names are those of the running example. A dataset will have further elements and columns; the edges in its `sp-ops:relationships` attributes are the record of what exists and how it joins.

| Element | Type | Level | Rows |
| --- | --- | --- | --- |
| `library` | table | screen | one per guide: `barcode`, `perturbation_id`, `role`, `control_type` |
| `iss/tiles/tile<i>/peaks` | points | tile | one per candidate spot: `x`, `y`, `read` |
| `iss/merged/reads` | points | merged | one per decoded read: `x`, `y`, `read`, `barcode`, `cell_label` |
| `pheno/merged/cells` | labels | merged | pixel value is the cell label |
| `pheno/merged/cells_features` | table | merged | one per cell: features, `barcode` once assigned |
| `pheno/merged/nuclei_features` | table | merged | one per nucleus: features, `cell_label` |

Reads are decoded per read id across rounds; `read` is the join key between a peak and its decoded read, following the scallops convention. `cell_label`, `barcode`, and `read` are example column names; the edge, not this page, fixes the names a store uses.

## Joins

Two kinds of join connect elements. A key join matches column values, or a column against label pixel values. A spatial join matches geometry, for example a read point inside a cell label. Once a spatial join is computed its result is stored as a column, here `cell_label` on `reads`, and it becomes a key join.

```{mermaid}
flowchart LR
  lib["library [Table]"] ---|"barcode"| reads["iss/merged/reads [Points]"]
  reads ---|"cell_label = pixel value"| cells["pheno/merged/cells [Labels]"]
  cells ---|"pixel value = label"| feat["pheno/merged/cells_features [Table]"]
  reads -.->|"sjoin, suggested"| cells
  nuc["pheno/merged/nuclei_features [Table]"] ---|"cell_label = pixel value"| cells
  peaks["iss/tiles/tile0/peaks [Points]"] ---|"read"| reads
```

## Storage

Edges are stored in `sp-ops:relationships` on the lowest collection that contains both endpoints. Element names are relative to that collection.

```json
"sp-ops:relationships": {
  "version": "0.2.0-draft",
  "edges": [
    {"from": "iss/merged/reads", "to": "../../../library", "method": "join",
     "on": {"left": "barcode", "right": "barcode"}, "status": "computed", "cardinality": "n:1"},
    {"from": "iss/merged/reads", "to": "pheno/merged/cells", "method": "join",
     "on": {"left": "cell_label", "right": "value"}, "status": "computed", "cardinality": "n:1"},
    {"from": "pheno/merged/cells", "to": "pheno/merged/cells_features", "method": "join",
     "on": {"left": "value", "right": "label"}, "status": "computed", "cardinality": "1:1"},
    {"from": "pheno/merged/nuclei_features", "to": "pheno/merged/cells", "method": "join",
     "on": {"left": "cell_label", "right": "value"}, "status": "computed", "cardinality": "n:1"},
    {"from": "iss/merged/reads", "to": "pheno/merged/cells", "method": "sjoin",
     "on": {"predicate": "within"}, "status": "suggested"}
  ]
}
```

`value` on a labels element means the pixel value. `status` is `computed` when the join columns exist and `suggested` when a reader would have to compute the join. The `sjoin` edge above is what the second edge looked like before `cell_label` was written. The `nuclei_features` edge is how a compartment with several instances per cell records its parent without nesting.

## Query sketch

The API below follows the Venice prototype. It is a sketch, not a released interface.

```python
well = sdata["plate1_processed/A/1"]

# rows of the feature table for cells in one tile footprint
tile0 = well["iss/tiles/layout"].query("tile == 0")
cells_in_tile0 = sd.polygon_query(well["pheno/merged/cells_features"], tile0.geometry[0], "well")

# one hop from reads along computed edges
query(well, "iss/merged/reads", depth=1)
# {"iss/merged/reads": ..., "library": ..., "pheno/merged/cells": ...}

# everything reachable from two cells
query(well, "pheno/merged/cells_features", ids=[6327, 6328], depth="all")

# check cardinality, coverage, and dangling keys on every edge
check_relationships(well)
```

With released SpatialData only, the same joins are `join_spatialelement_table` for labels to table and a pandas merge on `barcode` or `cell_label` for the rest.
