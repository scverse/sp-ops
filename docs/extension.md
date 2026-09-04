# Extension registry

Everything this specification adds to RFC-8 uses the prefix `sp-ops`, following RFC-8's naming scheme for extension identifiers. The surface is twelve attribute keys and three node types. A reader that does not know the prefix treats the values as opaque, as RFC-8 requires.

## Attribute keys

| Key | On | Value | Required |
| --- | --- | --- | --- |
| `sp-ops:spec` | screen collection | `{"version": string}` | MUST |
| `sp-ops:plate` | plate collection | `{"id": string}`; the physical plate, shared by its stages | MUST |
| `sp-ops:stage` | plate collection | `"raw"`, `"intermediate"`, `"processed"`, or another string | MUST |
| `sp-ops:modality` | modality collection | `"iss"`, `"pheno"`, or another string | MUST |
| `sp-ops:tiles` | tiles collection | `{"layout": Reference}`; the shapes element with one polygon per tile | MUST |
| `sp-ops:tile` | tile collection | `{"index": integer}`; matches the `tile` column of `layout` | MUST on tiles |
| `sp-ops:merged` | merged collection | `{"source": [Reference or ID, ...]}`; the tiles it was stitched from, by reference where the tiles are present in the store and by bare id where they are not; `[]` when no tile ids are known | MUST on merged |
| `sp-ops:axis` | round or channel node | `{"name": "round" or "c" or "t", "index": integer, "value": number or string, "unit": string}`; `value` and `unit` optional | MUST in `raw` |
| `sp-ops:rounds` | processed multiscale with a `round` axis | array of `{"index": integer, "acquisition": Reference}`, one per slice along `round` | MUST when `round` is present |
| `sp-ops:channels` | multiscale | array of `{"name": string or null, "role": "nuclear" or "base" or "stain" or "other"}`, one per channel in array order; or one such array per round when channels differ between rounds | MUST on images |
| `sp-ops:registration` | processed multiscale | `{"anchor": channel name, "reference": Reference}`, or one such object per round when the anchor differs between rounds | SHOULD |
| `sp-ops:relationships` | any collection | `{"version": string, "edges": [...]}`, see [](joinable-components.md#storage) | MUST for every table that describes an element; SHOULD otherwise |

A table that describes no element in the store, for example a screen-level `library` in a raw-only store with nothing to join it to, MUST still carry `sp-ops:relationships`, with `edges: []`. An empty list is the correct value for "no joinable pairs exist," not evidence of an omission.

At most one channel per round has role `nuclear`; phase or brightfield rounds have none. `sp-ops:channels` is authoritative over array position, and a writer MAY use fewer than four `base` channels.

## Node types

RFC-8 defines `collection`, `multiscale`, and `singlescale`. Tables, shapes, and points have no core node type, so this specification adds three leaf types. Each has `name` and `path` and no `nodes`; the element's own metadata lives in its Zarr group under `spatialdata_attrs`, and its link to other elements is an edge in `sp-ops:relationships`.

| Type | Element |
| --- | --- |
| `sp-ops:table` | SpatialData table, `AnnData` on disk |
| `sp-ops:shapes` | SpatialData shapes, GeoParquet on disk |
| `sp-ops:points` | SpatialData points, Parquet on disk |

No path type, coordinate transformation type, or axis type is added. RFC-5 `affine`, `translation`, `scale`, and `byDimension` cover alignment and stitching, and `round` is an axis of type `array`.

## Complete example

The processed well `A/1`, with the ISS modality expanded and the phenotyping modality abbreviated. The relationship edges are the ones from [](joinable-components.md#storage), abbreviated. Coordinate transformations are illustrative.

```json
{
  "type": "collection",
  "name": "A/1",
  "attributes": {
    "well": {"row": {"id": "A"}, "column": {"id": "1"}},
    "sp-ops:relationships": {
      "version": "0.2.0-draft",
      "edges": [
        {"from": "iss/merged/reads", "to": "../../../library", "method": "join",
         "on": {"left": "barcode", "right": "barcode"}, "status": "computed", "cardinality": "n:1"},
        {"from": "iss/merged/reads", "to": "pheno/merged/cells", "method": "join",
         "on": {"left": "cell_label", "right": "value"}, "status": "computed", "cardinality": "n:1"},
        {"from": "pheno/merged/cells", "to": "pheno/merged/cells_features", "method": "join",
         "on": {"left": "value", "right": "label"}, "status": "computed", "cardinality": "1:1"}
      ]
    },
    "scene": {
      "coordinateSystems": [{"id": "well", "axes": [
        {"name": "y", "type": "space", "unit": "micrometer"},
        {"name": "x", "type": "space", "unit": "micrometer"}]}],
      "coordinateTransformations": [
        {"type": "affine", "affine": [[1, 0, 0], [0, 1, 0]],
         "input": {"id": "tile", "path": {"type": "zarr", "path": "./iss/tiles/tile0/image"}}, "output": {"id": "well"}},
        {"type": "affine", "affine": [[1, 0, 0], [0, 1, 2048]],
         "input": {"id": "tile", "path": {"type": "zarr", "path": "./iss/tiles/tile1/image"}}, "output": {"id": "well"}},
        {"type": "affine", "affine": [[0.5, 0, 3.2], [0, 0.5, -1.7]],
         "input": {"id": "px", "path": {"type": "zarr", "path": "./pheno/merged/image"}}, "output": {"id": "well"}}
      ]
    }
  },
  "nodes": [
    {
      "type": "collection", "name": "iss",
      "attributes": {"sp-ops:modality": "iss"},
      "nodes": [
        {
          "type": "collection", "name": "tiles",
          "attributes": {"sp-ops:tiles": {"layout": {"id": "iss-layout"}}},
          "nodes": [
        {"type": "sp-ops:shapes", "name": "layout", "id": "iss-layout", "path": {"type": "zarr", "path": "./iss/tiles/layout"}},
        {"type": "sp-ops:table", "name": "tile_features", "path": {"type": "zarr", "path": "./iss/tiles/tile_features"}},
        {
          "type": "collection", "name": "tile0", "id": "iss-tile0",
          "attributes": {"sp-ops:tile": {"index": 0}},
          "nodes": [
            {"type": "multiscale", "name": "image", "path": {"type": "zarr", "path": "./iss/tiles/tile0/image"},
             "attributes": {
               "sp-ops:rounds": [{"index": 0, "acquisition": {"id": "iss-c1"}}, {"index": 1, "acquisition": {"id": "iss-c2"}}],
               "sp-ops:channels": [
                 {"name": "DAPI", "role": "nuclear"}, {"name": "A", "role": "base"},
                 {"name": "G", "role": "base"}, {"name": "C", "role": "base"}, {"name": "T", "role": "base"}],
               "sp-ops:registration": {"anchor": "DAPI", "reference": {"id": "round0", "path": {"type": "zarr", "path": "../../../../plate1_raw/A/1/iss/tiles/tile0/round0"}}},
               "coordinateSystems": [{"id": "tile", "axes": [
                 {"name": "round", "type": "array"}, {"name": "c", "type": "channel"},
                 {"name": "y", "type": "space", "unit": "micrometer"}, {"name": "x", "type": "space", "unit": "micrometer"}]}]}},
            {"type": "sp-ops:points", "name": "peaks", "path": {"type": "zarr", "path": "./iss/tiles/tile0/peaks"}}
          ]
        },
        {"type": "collection", "name": "tile1", "id": "iss-tile1", "path": {"type": "zarr", "path": "./iss/tiles/tile1"},
         "attributes": {"sp-ops:tile": {"index": 1}}}
          ]
        },
        {
          "type": "collection", "name": "merged",
          "attributes": {"sp-ops:merged": {"source": [{"id": "iss-tile0"}, {"id": "iss-tile1"}]}},
          "nodes": [
            {"type": "multiscale", "name": "image", "path": {"type": "zarr", "path": "./iss/merged/image"},
             "attributes": {"sp-ops:channels": ["... as tile0 ..."], "coordinateSystems": ["..."]}},
            {"type": "sp-ops:points", "name": "reads", "path": {"type": "zarr", "path": "./iss/merged/reads"}}
          ]
        }
      ]
    },
    {
      "type": "collection", "name": "pheno",
      "attributes": {"sp-ops:modality": "pheno", "acquisition": {"id": "pheno"}},
      "nodes": [
        {"type": "collection", "name": "tiles", "path": {"type": "zarr", "path": "./pheno/tiles"},
         "attributes": {"sp-ops:tiles": {"layout": {"id": "pheno-layout"}}}},
        {
          "type": "collection", "name": "merged",
          "attributes": {"sp-ops:merged": {"source": ["..."]}},
          "nodes": [
            {"type": "multiscale", "name": "image", "id": "pheno-merged-image",
             "path": {"type": "zarr", "path": "./pheno/merged/image"},
             "attributes": {"sp-ops:channels": [{"name": "DAPI", "role": "nuclear"}, {"name": "GFP", "role": "stain"}],
                            "coordinateSystems": ["..."]}},
            {"type": "multiscale", "name": "cells", "path": {"type": "zarr", "path": "./pheno/merged/cells"},
             "attributes": {"labels": {"source": [{"id": "pheno-merged-image"}]}, "coordinateSystems": ["..."]}},
            {"type": "multiscale", "name": "nuclei", "path": {"type": "zarr", "path": "./pheno/merged/nuclei"},
             "attributes": {"labels": {"source": [{"id": "pheno-merged-image"}]}, "coordinateSystems": ["..."]}},
            {"type": "sp-ops:table", "name": "nuclei_features", "path": {"type": "zarr", "path": "./pheno/merged/nuclei_features"}},
            {"type": "sp-ops:table", "name": "cells_features", "path": {"type": "zarr", "path": "./pheno/merged/cells_features"}}
          ]
        }
      ]
    }
  ]
}
```

Nodes with a `path` and no `nodes` are stored in their own `zarr.json`; the example inlines some of them for readability. RFC-8 allows either.
