# Open questions

Every entry on this page came out of writing a real dataset as a conformant store and checking the
result against the specification. Each has a stable id, the observation from that exercise, and what
the specification should do about it. An entry that is resolved moves into the page it fixes.

Four datasets were written, and every entry names the ones it came from, so a question can be read
against the delivery that raised it.

| Dataset | Stage | Delivered as | What it holds |
| --- | --- | --- | --- |
| [`experimentC`](#experimentc) | `raw` | Micro-Manager TIFF, no derived data | one well, two fields of view, nine ISS rounds, one phenotyping round |
| [`experimentC_scallops`](#experimentc_scallops) | `intermediate`, `processed` | Zarr and Parquet from the scallops pipeline | the same well after stitching, decoding and segmentation |
| [`biohub_example`](#biohub_example) | `processed` | OME-NGFF 0.5 HCS, merged only | three wells, one stitched image and twelve segmentations each |
| [`cpg0021_sample`](#cpg0021_sample) | `raw` | Nikon ND2 with its acquisition metadata intact | two wells, 48 fields of view, twelve ISS rounds, one phenotyping round |

Between them they exercise the whole specification. Where two of them answer the same question
differently, the disagreement is itself the finding.

| | `experimentC` | `experimentC_scallops` | `biohub_example` | `cpg0021_sample` |
| --- | --- | --- | --- | --- |
| base identity (Q1) | dye names only | `G, T, A, C`, in a command string | `DAPI, G, T, A, C` recorded | dye names only |
| tile layout (Q2) | measured from image overlap | declared, from a position list | tile ids in a table, grid as a bitmap | a position list, wrong by 68 px |
| magnification (Q20) | both 10x, scale 1 | both 10x | 5x against 20x, ratio 4 | 10x against 20x, ratio 2 |
| pixel size against geometry (Q22) | 2.2 percent apart | stage offset kept over the images | — | 1.0 percent ISS, 0.4 percent pheno |
| barcode against rounds (Q23) | 20 bases, 9 rounds | 9-base reads that join nothing (Q15) | 10 bases, 10 rounds, every row joins | 20 bases, 12 rounds, prefix works |
| instrument provenance (Q6) | TIFF tags | — | a YAML sidecar | per image, in every ND2 |

## The datasets

### experimentC

An optical pooled screen delivered as flat TIFF exports and one barcode table, with no derived data
of any kind, so it exercises `raw` and nothing else. It is the dataset behind the running example in
[](layout.md).

| What | Value |
| --- | --- |
| wells | one, `A1` |
| fields of view | two, Micro-Manager sites 102 and 103, overlapping by about 33 px |
| ISS rounds | nine, cycle labels 1 to 5 and 7 to 10; cycle 6 was not acquired |
| ISS channels | five: `DAPI_10p`, `Cy3`, `A594`, `Cy5`, `Cy7` |
| phenotyping | one round, two channels: `DAPI_10p`, `GFP` |
| tile shape | `(c, 1024, 1024)` `uint16`, one z plane, one timepoint |
| pixel size | 1.32 µm, 10x objective, 2x2 binning, both modalities |
| library | 5738 guides over 950 gene symbols, 100 of them non-targeting |

```text
experimentC.zarr/
├── zarr.json                    # collection; sp-ops:spec
├── library                      # table: one row per guide
└── plate1_raw/                  # collection; plate; sp-ops:stage "raw"
    └── A/1/                     # collection; well {row A, column 1}; scene: the well frame
        ├── iss/                 # collection; sp-ops:modality "iss"
        │   └── tiles/           # collection; sp-ops:tiles
        │       ├── layout       # shapes: one polygon per tile, measured, not declared
        │       ├── tile102/     # collection; sp-ops:tile {"index": 102}
        │       │   ├── round0/  # collection; acquisition iss-c1; sp-ops:axis {round, 0, 1}
        │       │   │   ├── channel0   # multiscale (y, x); DAPI_10p, role nuclear
        │       │   │   └── channel1 ... channel4   # Cy3, A594, Cy5, Cy7; role base
        │       │   └── round1/ ... round8/   # iss-c2 to iss-c10; round5 is cycle 7
        │       └── tile103/     # collection; sp-ops:tile {"index": 103}
        └── pheno/               # collection; sp-ops:modality "pheno"; acquisition pheno
            └── tiles/           # one round only, so no round level
                ├── layout
                └── tile102/ tile103/
                    ├── channel0 # DAPI_10p, role nuclear
                    └── channel1 # GFP, role stain
```

123 RFC-8 nodes, 94 channel multiscales, 282 arrays over three pyramid levels, 169 MB.

The tile offsets in the well frame are measured, not declared. The delivery ships no per-well
position list, so `layout` and the tile-to-well transforms come from cross correlating the nuclear
overlap strip: tile 103 sits 991 px in `x` and 4 px in `y` from tile 102, the same value in all ten
acquisitions, at correlations of 0.945 to 0.954. See Q2 and Q22.

Hygiene, and not specification problems: the phenotyping folder sits outside the nine ISS cycle
folders and is labelled `c0`, as though phenotyping were ISS cycle 0; the phenotyping channel is
recorded as `GFP` and the antibody it images, p65, appears only in a folder name, which is the
practice D3 removes; and the acquisition prefix disagrees with the folder name for three of the nine
cycles, `10X-c5-SBS-5` against `10X_c5-SBS-5`.

### experimentC_scallops

The same screen as `experimentC`, the same well and the same two fields of view, run through the
[scallops](https://github.com/Genentech/scallops) pipeline. It carries no raw tiles: it holds a
stitch stage and an ops stage, so it is the processed counterpart Q25 asked for over pixels whose
`raw` form is already written, and the only dataset here that exercises `intermediate`.

| What | Value |
| --- | --- |
| fields of view | two, grid indices 0 and 1, renumbered from sites 102 and 103 |
| ISS rounds | nine, cycle labels 1 to 5 and 7 to 10; the pipeline calls the axis `t` |
| channels | named at stitch time: ISS `DAPI, G, T, A, C`, phenotyping `DAPI, NFkB` |
| merged shape | `(1002, 1972)`, 11 px cropped from every edge of a `(1024, 1993.7)` mosaic |
| stitch stage | 10 illumination fields, 10 stitched well images, per-tile position and eval reports |
| ops stage | registered ISS stack, 39987 peaks, 15590 reads, 561240 base intensities |
| segmentation | five label arrays: 4706 nuclei, 4589 cells, 4525 cytosol, and two unfiltered |
| features | 141 cell, 49 nuclei, 38 cytosol columns, plus one 275-column fusion of all three |
| library | the same 5738 guides; not the reference the reads were decoded against (Q15) |

This dataset is the evidence for [D4](design-decisions.md#d4-there-is-no-fixation-timepoint-level):
`iss-registered-t0.zarr` declares axes `t, c, y, x` with `t: [1, 2, 3, 4, 5, 7, 8, 9, 10]`, the
cycle labels, and its transform folders are `iss-transforms-t0/A1/t=2` to `t=10`. The store writes
that axis as `round`.

```text
experimentC_scallops.zarr/
├── zarr.json                     # collection; sp-ops:spec; edge reads → library (Q15)
├── library                       # table: 5738 guides
├── plate1_intermediate/          # collection; plate; sp-ops:stage "intermediate"
│   └── A/1/
│       ├── iss/
│       │   ├── tiles/            # collection; sp-ops:tiles
│       │   │   ├── layout        # shapes: 2 polygons, from the stage position list
│       │   │   ├── tile_features # table: 18 rows, one per tile and round
│       │   │   └── tile102/ tile103/   # empty: no per-tile product exists  ← Q14
│       │   ├── merged/
│       │   │   ├── image         # multiscale (round, c, y, x); stitched, unregistered ← Q30
│       │   │   ├── tile_provenance   # labels (y, x): which tile each pixel came from
│       │   │   └── stitch_features   # table: 9 rows, the zncc the stitcher scored
│       │   └── illumination/     # 9 multiscales (c, y, x) float32, in the tile frame
│       └── pheno/                # the same four children, one round
└── plate1_processed/             # collection; plate; sp-ops:stage "processed"
    └── A/1/                      # collection; well; scene; 10 relationship edges
        ├── iss/
        │   └── merged/           # collection; sp-ops:merged → the intermediate tiles
        │       ├── image         # multiscale (9, 5, 1002, 1972); sp-ops:rounds, registration
        │       ├── peaks         # points: 39987 candidate spots, with sigma
        │       ├── reads         # points: 15590 decoded reads, 9 bases each
        │       ├── bases         # table: 561240 rows, one per read, round and base ← Q17
        │       ├── crosstalk     # table: the 4 by 4 base bleed matrix ← Q17
        │       └── peak_thresholds_labels, peak_thresholds_crosstalk   # 98 rows each ← Q17
        └── pheno/
            └── merged/
                ├── image         # multiscale (2, 1002, 1972)
                ├── nuclei, cells, cytosol              # labels (y, x) int32
                ├── nuclei_unfiltered, cells_unfiltered # the pre-filter pass ← Q47
                ├── nuclei_features, cells_features, cytosol_features
                ├── cell_barcodes  # table: 2798 cells with a called barcode
                └── merged_features    # table: 4706 by 275, all three compartments ← Q34
```

42 RFC-8 nodes, 21 multiscales, 318 arrays, 14 tables, two shapes and two points elements, 359 MB.
There is no `raw` plate: those pixels are `experimentC`, and the two stores share the plate id.

Three things are derived rather than copied. The tile layout comes from `stage_positions.parquet`,
so these polygons are declared where `experimentC`'s were measured. Both merged images carry a
14.52 µm translation into the well frame for the stitcher's 11 px fuse crop, which no source
metadata records (Q32). And `tile_provenance` is the grid index plus one, because the source numbers
tiles from zero and zero is the labels background. The phenotyping merged image is written into both
plate collections, because nothing between the stitch and the segmentation touched it and there is
no way for one stage to say that a single element of it is another stage's element unchanged.

Hygiene: the stitcher scored a cross correlation of 0.003 to 0.022 on the one overlapping pair and
kept the nominal stage offset, 969.69697 px, in all ten acquisitions, where `experimentC` measured
991 px from the same images at 0.945 to 0.954 — and the two cannot be reconciled, since at 991 px
the overlap is 3.2 percent, below the pipeline's own `min_overlap_fraction` of 4 percent. The 4 by 4
crosstalk matrix ships as a multiscale with `y` and `x` space axes, so a viewer renders a
calibration matrix as a 4-pixel image. Every label in `segment.zarr` points at a group that does not
exist (Q16), two segmentations are named `.all` (Q47), and `spot-detect.zarr/images/A1-max` gives
its `sigma` axis a `type` of `null` (Q31).

### biohub_example

The public submission [](layout.md) cites for the merged-only case: one stitched image and a stack
of segmentations per well, no tiles and no raw data. It is the complement of `experimentC` — that
one exercises `raw` and nothing else, this one `processed` and nothing else. The delivery holds a
three-well manifest that declares a stitched image of 104650 by 105144 px per well and carries no
pixels, and beside it a 2048 by 2048 excerpt of well `A/1` that does, positioned by a translation of
15600 µm. The store is built from the excerpt.

| What | Value |
| --- | --- |
| wells | three declared, `A/1` to `A/3`; pixels for `A/1` only |
| image | `(1, 6, 1, 2048, 2048)` float32, five pyramid levels, 0.325 µm per px |
| channels | `Phase2D`, `Focus3D`, `GFP` (5xUPRE), `mCherry` (SEC61B), `nuclei_prediction`, `membrane_prediction` |
| labels | twelve compartments: cell, nuclei, and ten organelle classes, `int32` |
| other rasters | three RGBA overlays, `(2048, 2048, 4)` uint8: two ISS renderings and a tile grid |
| ISS | ten cycles declared in the metadata; no per-cycle image, no reads, no peaks |
| library | 4211 guides over 1052 perturbations, 211 non-targeting, 10-base barcodes |
| cells | 831587 barcode-assigned cells over the three wells, from 2249 source tiles |
| features | 2935 definitions and no values; a separate 1052 by 66 atlas over 77 screens |
| provenance | a YAML sidecar: cell line, library, ISS chemistry, objectives, microscope, filters |

```text
biohub_example.zarr/
├── zarr.json                    # collection; sp-ops:spec; edge cells → library
├── library                      # table: 4211 guides
├── feature_definitions          # table: 2935 features, no values anywhere (Q26)
└── plate1_processed/            # collection; plate; sp-ops:stage "processed"
    ├── cells                    # table: 831587 cells, all three wells, plate level
    └── A/1/                     # collection; well; scene: the well frame
        ├── pheno/
        │   └── merged/          # collection; sp-ops:merged {"source": []}  ← Q8
        │       ├── image        # multiscale (c, y, x) float32, 6 channels, 5 levels
        │       ├── cell_seg     # multiscale (y, x) int32; labels.source → image
        │       ├── nuclear_seg  # ... and ten more compartments
        │       └── grid_overlay # multiscale (c, y, x) uint8; a rendering, not data
        └── iss/
            └── merged/          # collection; sp-ops:merged {"source": []}
                ├── iss_gene_image   # multiscale (c, y, x) uint8 RGBA
                └── iss_guide_image  # multiscale (c, y, x) uint8 RGBA
```

23 RFC-8 nodes, 124 arrays, three tables, 149 MB. Wells `A/2` and `A/3` are declared in the plate's
columns and carry no node, which [](layout.md#screen-and-plates) permits because the delivery has no
pixels for them; their rows are in the plate-level `cells` table. Two corrections make this a
rewrite rather than a relabelling: the axes are squeezed and lowercased (Q44), and the labels are
written at the image's pixel size rather than the one they declare (Q46). The well collection
carries sixteen identical transforms, one per merged element, and eleven `sjoin` edges at
`status: "suggested"` for the compartment membership nothing records (Q12).

Hygiene: the `labels/` group declares its contents twice, in `ome.labels` and in a sibling `labels`
key, listing twelve and thirteen names against fifteen groups on disk, and the two ISS renderings
appear in neither, so the only ISS-derived rasters in the submission are the ones a reader following
the metadata never sees. `cell_seg` reports three cell counts that cannot all describe the same
thing, 590472, 267449 and 44734217. `nuclear_seg` is two rows shorter than the image in the
manifest, so the labels are not quite the same grid even before Q46. And the channel named `mCherry`
was imaged with mScarlet-I and the one named `GFP` with mEGFP, per the metadata block that names
them.

### cpg0021_sample

A two-well subset of the public
[cpg0021-periscope](https://github.com/broadinstitute/cellpainting-gallery) whole-genome screen,
delivered as Nikon ND2 files straight off the microscope with one guide table beside them. Like
`experimentC` it carries no derived data. Unlike `experimentC` its images arrive in a vendor format
with their acquisition metadata intact — stage coordinates, objective, exposure, filter block,
autofocus offset and a pixel-to-stage matrix on every image — which makes it the dataset that says
what a `raw` store is being asked to carry, and the one that can be checked against itself.

| What | Value |
| --- | --- |
| plate | one, `CP186A`; the 6-well format is measured from the stage, not recorded |
| wells | two, delivered as `Well1` and `Well2`, written `A/1` and `A/2` |
| fields of view | 8 ISS and 40 phenotyping per well, of 320 and 1364 in the full acquisition |
| ISS rounds | twelve, cycle labels 1 to 12, no gap |
| channels | ISS `DAPI, Cy3, A594, Cy5, Cy7`; phenotyping `DAPI, GFP, A594, Cy5, 750` |
| tile shape | `(c, 1480, 1480)` `uint16`, one z plane, both modalities, 10 percent overlap |
| pixel size | ISS 1.2143 µm at 10x/0.45, phenotyping 0.6071 µm at 20x/0.75, ratio exactly 2 |
| library | 82678 rows over 20391 gene symbols and 80862 distinct guides, 2270 non-targeting |

```text
cpg0021_sample.zarr/
├── zarr.json                       # collection; sp-ops:spec
├── library                         # table: 82678 rows, one per delivered guide row ← Q19
└── plate1_raw/                     # collection; plate CP186A; sp-ops:stage "raw"
    ├── A/1/                        # collection; well ← Q18; scene: 680 transforms ← Q40
    │   ├── iss/
    │   │   └── tiles/
    │   │       ├── layout          # shapes: 8 polygons, measured; stage readout beside ← Q49
    │   │       ├── image_metadata  # table: 480 rows, one per acquired image ← Q6
    │   │       ├── tile0/          # collection; sp-ops:tile {"index": 0, "site": 0}
    │   │       │   ├── round0/     # collection; acquisition iss-c1
    │   │       │   │   ├── channel0     # multiscale (y, x); DAPI, role nuclear
    │   │       │   │   └── channel1 ... channel4   # Cy3, A594, Cy5, Cy7; role base
    │   │       │   └── round1/ ... round11/        # acquisitions iss-c2 to iss-c12
    │   │       └── tile1/ ... tile7/
    │   └── pheno/
    │       └── tiles/              # one round only, so no round level
    │           ├── layout          # shapes: 40 polygons
    │           ├── image_metadata  # table: 200 rows
    │           └── tile0/ ... tile39/
    │               ├── channel0    # DAPI, role nuclear
    │               └── channel1 ... channel4       # GFP, A594, Cy5, 750; role stain
    └── A/2/                        # the same, eight and forty more fields of view
```

1669 RFC-8 nodes, 1360 channel multiscales, 4080 arrays, 1360 tile-to-well transforms, five tables,
four shapes elements, 5.6 GB. Four things about the store need stating, and each is a finding below.

- **The tile positions are measured, not declared,** though this delivery ships a position list.
  Every ND2 records its own stage coordinates and they disagree with the images by up to 68 px,
  consistently, because the recorded pixel size is 1.0 percent too large in ISS and 0.4 percent in
  phenotyping. `layout` holds the measured footprint and keeps the stage readout in four columns
  beside it, because nothing distinguishes the two (Q2, Q49).
- **The tile-to-well transform is an affine with a rotation,** not a translation. The instrument's
  `pixelToStageTransformationMatrix` has a negative determinant: it mirrors x. Taking the well x axis
  against stage x absorbs the mirror and leaves the camera mounting angle, 0.053°, which every
  transform carries. A writer that read the recorded matrix and wrote a translation would place every
  tile mirrored.
- **The phenotyping transforms carry a scale,** 1.00636 in `A/1` and 1.00588 in `A/2`. That is
  registration step 3, the modality registration, done at `raw` because a raw store places both
  modalities in one `well` frame and has no merged image to do it between. It is measured from the
  nuclear channel over 24 tile pairs per well at correlations of 0.77 to 0.91, and it is not the
  ratio of the recorded pixel sizes (Q37). `sp-ops:registration` is bound to a processed multiscale,
  so the store cannot say any of this (Q50).
- **`image_metadata` is the provenance table Q6 proposed,** written here to see whether it works: one
  row per acquired image, with objective, numerical aperture, magnification, camera, binning,
  exposure, filter block, autofocus offset, stage coordinates, timestamp and recorded pixel size. Q6
  puts it at the plate level; the store splits it per modality under each `tiles` collection, which
  [](features.md#merged-and-split-tables) permits and which lets the well and the modality come from
  position in the hierarchy rather than from columns. Its key is `(tile, round, channel)` and `on`
  takes one column pair, so the edge joins on `tile` alone (Q33).

Hygiene: 96 of the 272 images report an acquisition timestamp in the year 3189, and four of the
eleven acquisitions whose clocks are usable stamp all sixteen of their images identically, so a
distinct per-image time exists for 112 of 272; the store writes the recorded value with a
`timestamp_valid` column beside it. The cycle 2 directory is `10x_c2-SBS-2` and the other eleven are
`10X_c<n>-SBS-<n>`. `Well1_Point1` and `Well2_Point2` encode the well twice and the row and column
not at all (Q18). Three phenotyping channels are named by dye or filter and one, `750`, by an
excitation line, and what any of them images is recorded nowhere (Q9, Q51). And `gene_symbol` and
`gene_id` do not agree on identity: 52 symbols carry more than one id, 293 ids more than one symbol.

### Rebuilding the stores

`scripts/check_sp_ops_zarr.py` walks a store from the root collection, checks every requirement in
the [](extension.md) registry and the [](layout.md) level table, and compares every array against
the source page it was written from. Advisories are checks this exercise suggests the specification
should require, not ones it does.

`experimentC_scallops` and `biohub_example` are built by `scripts/build_store.py`, which shares one
converter and writes each store into its own folder under `stores/`. `experimentC` and
`cpg0021_sample` still have their own scripts and are not ported yet.

```bash
python scripts/build_store.py experimentC_scallops
python scripts/build_store.py biohub_example

python scripts/build_experimentC_zarr.py path/to/experimentC experimentC.zarr
python scripts/build_cpg0021_zarr.py path/to/cpg0021_sample cpg0021_sample.zarr

python scripts/check_sp_ops_zarr.py stores/experimentC_scallops/experimentC_scallops.zarr \
    --scallops path/to/experimentC_scallops
python scripts/check_sp_ops_zarr.py stores/biohub_example/biohub_example.zarr \
    --zarr path/to/biohub_example
python scripts/check_sp_ops_zarr.py experimentC.zarr --tiffs path/to/experimentC
python scripts/check_sp_ops_zarr.py cpg0021_sample.zarr --nd2 path/to/cpg0021_sample/.../CP186A
```

| Store | Checks | Failed | Advisories |
| --- | --- | --- | --- |
| `experimentC.zarr` | 1810 | 0 | 0 |
| `experimentC_scallops.zarr` | 361 | 4, the empty tile collections of Q14 | 1, the reads-to-library edge of Q15 |
| `biohub_example.zarr` | 435 | 0 | 2, the empty `sp-ops:merged.source` of Q8 |
| `cpg0021_sample.zarr` | 27036 | 0 | 0 |

`experimentC_scallops` is the only store that does not check clean, and both results are findings
rather than build defects.

The two ported stores are written through [ome-zarr-py](https://github.com/ome/ome-zarr-py), which
supplies the arrays and the pyramid while the metadata stays RFC-8 only. Two consequences are
visible on disk and neither is checked: every pyramid level carries the Zarr v3 `dimension_names`
the library writes, and levels above 0 come from its `local_mean` and `nearest` resampling rather
than a 2x2 block mean, so a label level above 0 can differ by one row from a repeated `[::2]`
subsample. Level 0 is unchanged, and it is the only level compared against the source.

## Requirements a dataset cannot meet

| Q | Question | Dataset |
| --- | --- | --- |
| Q1 | Base identity is required and not recorded | `experimentC` |
| Q2 | `layout` is a MUST with no metadata path to satisfy it | `experimentC` |
| Q3 | The plate id is not a field of the delivery | `experimentC` |
| Q4 | A single-well subset cannot declare the plate geometry | `experimentC` |
| Q5 | `tile.index` conflates grid position and site id | `experimentC` |
| Q6 | `raw` has nowhere to keep instrument provenance | `cpg0021_sample` |
| Q7 | A table that annotates nothing has no defined edges | `experimentC` |
| Q8 | `merged.source` cannot be filled by a merged-only store | `biohub_example` |
| Q9 | `role` cannot describe a predicted or label-free channel | `biohub_example` |
| Q10 | No home for the provenance of a derived element | `biohub_example` |
| Q11 | A cell table has no `label` column to join on | `biohub_example` |
| Q12 | Compartment membership can be unrecorded entirely | `biohub_example` |
| Q13 | RFC-5 has no transform for a B-spline registration | `experimentC_scallops` |
| Q14 | A stitch stage has no per-tile image to put in a tile | `experimentC_scallops` |
| Q15 | The reference a read was decoded against is absent | `experimentC_scallops` |
| Q16 | `labels.source` can dangle | `experimentC_scallops` |
| Q17 | Diagnostics and calibration have no granularity | `experimentC_scallops` |
| Q18 | The `well` row and column are recorded nowhere | `cpg0021_sample` |
| Q19 | `library` has no unique row key, so `n:1` is false | `cpg0021_sample` |

### Q1. `sp-ops:channels` requires a base identity the dataset does not record

From `experimentC`, `experimentC_scallops` · Affects `sp-ops:channels`

`role` is MUST and its closed set includes `base`, but `experimentC` records dyes only — `Cy3`,
`A594`, `Cy5`, `Cy7`, with no dye-to-base mapping in the images or the barcode table — so
`iss.sel(round=0, c="DAPI")`, the specification's own read, cannot address a base by its identity.
The pipeline assigns `G, T, A, C` downstream, at stitch time, but only inside a free-text
`scallops_command`: still unrecoverable, and a permuted assignment would make every barcode in the
store wrong with nothing to detect it.

Fix. Base identity is a `processed` decision, so say so, and add an optional dye or filter field
beside `name`. Q51 needs that field too.

### Q2. `sp-ops:tiles.layout` is a MUST with no metadata path to satisfy it

From `experimentC`, `experimentC_scallops`, `cpg0021_sample` · Affects `sp-ops:tiles.layout`

`layout` MUST hold one polygon per field of view in the well frame. `experimentC` ships no position
list — its TIFF tags hold the full 3198-position plate list, of which two sites are present — so
its polygons were reconstructed from image content. Shipping a list does not settle it:
`experimentC_scallops` declares its polygons from `stage_positions.parquet`, while
`cpg0021_sample`'s per-image stage coordinates are wrong by up to 68 px, so its polygons are
measured too. Nothing in a store distinguishes the three cases.

Fix. Keep the MUST and say what a writer does when positions are absent or wrong: record the layout
as measured, and record how it was obtained. A layout has no provenance field, which is Q6's gap in
a second place.

### Q3. The plate identifier is not a field of the dataset

From `experimentC` · Affects `sp-ops:plate`

`sp-ops:plate` MUST carry the physical plate id, which is what ties a plate's stages together. Here
it survives only inside an acquisition directory name embedded in the TIFF tags, and is withheld on
this page for the reason [](references.md) gives.

Fix. The requirement is right and the gap is in the delivery. One sentence in [](layout.md): the
plate id is expected from the acquisition system or the submitter, and is not recoverable from pixel
data.

### Q4. A single-well delivery cannot declare the plate geometry

From `experimentC`, `cpg0021_sample` · Affects plate `rows` and `columns`

A plate collection declares `rows` and `columns`, and the only trace of the format here is a
substring of Q3's directory name, so the store declares one row and one column rather than invent
the rest. [](layout.md#screen-and-plates) guarantees that plate collections of one physical plate
declare the same acquisitions, so a processed image can reference them without opening the raw
plate; the same argument applies to rows and columns, and a subset store cannot honour it.

Fix. Say whether `rows` and `columns` describe the physical plate or only the wells present. If the
plate, a subset store needs a way to say it cannot fill them; if only what is present, the guarantee
weakens. Q18 sharpens the choice.

### Q5. `sp-ops:tile.index` conflates a grid position with an acquisition site id

From `experimentC`, `experimentC_scallops` · Affects `sp-ops:tile.index`

`index` matches the `tile` column of `layout`, and the registry does not say what the integer means.
`experimentC`'s two fields of view are sites 102 and 103 of a 3198-position acquisition. The
pipeline shows what renumbering costs: scallops rewrote them as grid indices 0 and 1 in its position
reports, its provenance raster and every file name, leaving the site ids only inside a `source`
column holding an input path, so recovering them means parsing a file name.

Fix. Fix `index` as the position in the modality's own tile grid and add an optional field for the
acquisition's identifier — the stores keep both, as `index` and `site`. The grid position orders the
tiles; the site id joins back to the instrument.

### Q6. `raw` has nowhere to keep instrument provenance

From `cpg0021_sample`, `experimentC`, `biohub_example` · Affects D1, D5, [](features.md)

D1 and D5 make `raw` the reprocessable record, and none of the twelve attribute keys holds how the
pixels were acquired. All three deliveries carry it and all three stores dropped it: `experimentC`
in TIFF tags, `biohub_example` in a YAML sidecar, `cpg0021_sample` in every ND2 — exposure differing
fourfold across the channels of one round, objective and numerical aperture differing between
modalities, 2x2 binning, autofocus offsets of 7154 to 7224 in ISS against 9445 in phenotyping,
per-image stage coordinates, filter blocks, seven laser lines with their powers, camera serial and
temperature.

Fix. A plate-level table with one row per acquired image: a table like any other, needing no new key
beyond an edge. `cpg0021_sample` writes one as `image_metadata`, and writing it exposes Q17's gap —
one row per image is `(tile, round, channel)` granularity, and [](features.md)'s ladder starts at
the cell.

### Q7. A screen-level table that annotates nothing has no defined relationships

From `experimentC` · Affects `sp-ops:relationships`

`sp-ops:relationships` is MUST for a table that describes an element and SHOULD otherwise. In a
raw-only store `library` describes nothing in the store, because there are no reads to join it to,
so the store writes an empty edge list on the screen collection.

Fix. Say that an empty edge list is the correct value for a collection with no joinable pairs, or
drop the SHOULD for collections that contain none. Q17 is the harder version.

### Q8. `sp-ops:merged.source` is a MUST that a merged-only submission cannot fill

From `biohub_example` · Affects `sp-ops:merged`

`sp-ops:merged` is MUST on a merged collection, with a `source` referencing the tiles it was
stitched from; this delivery discarded its tiles, so the store writes `"source": []`. [](layout.md)
explicitly blesses the shape — "no tiles and no raw data, and is still a usable store" — so the
specification permits a store and then requires a field it cannot fill. The tiles demonstrably
existed: `cells` carries 2249 distinct tile ids and a grid overlay renders their boundaries.

Fix. Let `source` hold tile identifiers rather than references. This delivery has exactly those
identifiers; making the key optional would lose them instead.

### Q9. `role` cannot describe a label-free, reconstructed, or predicted channel

From `biohub_example`, `cpg0021_sample` · Affects `sp-ops:channels.role`, D7

Four of six channels here are not stains: `Phase2D` and `Focus3D` are label-free brightfield
reconstructions, `nuclei_prediction` and `membrane_prediction` virtual stains from a model. With
`role` limited to `nuclear, base, stain, other` the store writes `other` three times and calls the
nuclear-looking channel `nuclear` — except it is a prediction, so
[D7](design-decisions.md#d7-registration-anchors-are-declared-with-the-nuclear-channel-as-the-default)'s
default anchor would register on model output. The phenotyping round has no nuclear stain and the
ISS round has a Hoechst stain, so the modalities would anchor on different kinds of thing. The
source metadata is richer: a `channel_type` of `labelfree`, `fluorescence` or `predicted`, and a
marker, target, fluorophore and wavelengths.

Fix. Separate what a channel is for, the current role, from how it was produced — measured,
reconstructed, predicted — and let it carry its marker and fluorophore, which `cpg0021_sample` needs
too for a channel named `750`. Then say in D7 whether a prediction may anchor a registration.

### Q10. There is no home for the provenance of a derived element

From `biohub_example` · Affects `labels.source`, D8

Every label group records how it was made — `cellpose-sam`, a version, the stitching rule, diameter
100, flow threshold 0.7, IoU 0.1, tile 4096, overlap 512 — and the channel it was computed from.
RFC-8 `labels.source` references an image node, not a channel, so all twelve labels point at the
same six-channel image and which channel each came from is unrecoverable. The method and parameters
have no key at all.

Fix. Let `labels.source` reference a channel of an image, and add a key for the method and
parameters behind any derived element. This is Q6 on the processed side: without it a processed store
can be read but not audited or regenerated. Q15 and Q47 are the same gap from other directions.

### Q11. A cell table has no label column, and the specification's edge needs one

From `biohub_example` · Affects [](features.md#merged-and-split-tables), D3

The edge from labels to its table is `{"on": {"left": "value", "right": "label"}}`, and
`cell_data.parquet` has no `label` column: the value is the last component of `cell_uid`, a string
like `Biohub_OPS0001_A1_2027_19418950`. That is features.md's third merged-table encoding, "a
hierarchical unique id column ... next to plain `well`, `modality`, `site`, `label` columns", minus
the plain columns, so the id has to be parsed. The store derives all four, and the derivation checks
out: every one of the 251 cells inside the delivered excerpt has its derived label in `cell_seg`.

Fix. Say that the plain columns accompany the hierarchical id rather than replacing it. An id whose
components must be parsed to join is the naming grammar
[D3](design-decisions.md#d3-names-are-opaque-and-attributes-carry-the-meaning) rejects, moved from a
path into a column.

### Q12. Compartment membership can be unrecorded, and then only a spatial join recovers it

From `biohub_example` · Affects D8, [](joinable-components.md)

Twelve compartments were segmented — the cell, the nucleus, ten organelle classes — and none records
membership.
[D8](design-decisions.md#d8-derived-data-lives-at-the-tile-or-merged-collection-it-was-computed-on)
puts a `cell_label` column on a compartment's feature table; there are no feature tables here, so
nothing links a nucleolus to its cell. The numbering spaces are disjoint too — `cell_seg` runs
20064998 to 20066368, `nuclear_seg` 282305 to 321319 — so the values cannot be matched either. The
store writes eleven `sjoin` edges on `within` at `status: "suggested"`.

Fix. The mechanism works: this is what `suggested` is for, and it belongs in
[](joinable-components.md) as the worked example, because labels without feature tables is the
common case. Add a SHOULD: a compartment label SHOULD share its parent's numbering or carry a
membership column, so membership is data rather than a suggestion. Q48 is the shared-numbering case.

### Q13. RFC-5 has no transform for the registration this pipeline computed

From `experimentC_scallops` · Affects [](extension.md), A3, [](layout.md#registration)

[](extension.md) adds no transformation type, because RFC-5's four "cover alignment and stitching".
They do not cover this dataset: each of the eight non-reference ISS rounds was registered by elastix
as an `AffineTransform` of six parameters composed with a `RecursiveBSplineTransform` of 1020
parameters on a 30 by 17 cubic control grid. Discarding the B-spline is tolerable for seven rounds,
whose largest control displacement is 0.53 to 1.23 px, and not for cycle 10, where it is 34.3 px
with a 99th percentile of 31.4 px. The registered array is the only evidence the transform existed,
and the transform is not invertible from it.

Fix. Add a transform type for a displacement field or a B-spline control grid, which is what
registration of fixed cells across rounds produces, or failing that a way to reference an opaque
external transform with its parameters. Without one, [](layout.md#registration)'s claim that every
registration step "is a coordinate transformation between RFC-5 coordinate systems" is false for
step 2.

### Q14. A tile collection MUST hold an image, and a stitch stage has no per-tile product

From `experimentC_scallops` · Affects `sp-ops:tiles`, the [](layout.md) level table

The level table makes the tile level "MUST have at least one under `tiles`". Scallops stitches
straight from the raw TIFFs, writing only illumination fields in between, and those are one per well
and round. So the stitch stage has a tile layout, a per-tile position report and a per-tile eval
report, and no per-tile array: the store writes two tile collections that hold nothing, which is the
four failures the checker reports.

Fix. Let a `tiles` collection carry its `layout` and its tile-granularity tables with no tile
collections under it. Moving `layout` up to the modality splits the tile level's metadata across two
collections for no gain.

### Q15. The reference a read was decoded against is not in the store

From `experimentC_scallops` · Affects the `reads` to `library` edge

Q23 proposed a nine-base prefix join, the reads are nine bases, and the join still fails: 2.4
percent of the 15590 reads match a library prefix, against 2.2 percent expected by chance from 5738
barcodes over 4⁹ reads. These reads were never decoded against this library. What they were decoded
against is absent — `barcode_match` is true for 6733 reads over 1932 distinct barcodes, of which 183
are library prefixes, and `closest_match` lies inside the set observed in this well for 79 percent
of rows. The store has nowhere to name that whitelist, nor to record that the `library` it carries
is not it, so it writes the declared edge and the checker reports an advisory.

Fix. The reference a base call was decoded against is provenance of `reads` and belongs wherever Q10
puts it. A store that cannot say which barcode list produced its calls cannot be audited, and this
one ships a `library` edge a reader would take on trust. Q28 is the other half.

### Q16. `labels.source` can resolve outside the store

From `experimentC_scallops` · Affects `labels.source`, D8

`segment.zarr` holds a `labels/` group and nothing else, and all five label arrays declare
`image-label.source.image: "../../images/A1"`. No such group exists: the image is three directories
away, in `stitch/pheno/stitch/stitch.zarr/images/A1`. So the one link tying labels to their image,
which D8 cites as its reason for keeping derived data beside it, is dangling in the delivery. The
store repoints all five at `pheno/merged/image` by id.

Fix. One sentence: `labels.source` MUST resolve, and MUST use an explicit external path when the
image is in another store. A reader cannot tell a resolvable reference from this one without trying
it, and a writer copying a pipeline's output verbatim reproduces the break.

### Q17. Run-level diagnostics and calibration have no granularity

From `experimentC_scallops`, `cpg0021_sample` · Affects [](features.md), `sp-ops:relationships`

Three ops-stage elements describe the run rather than anything in space: two 98-row threshold sweeps
of precision, recall, f1 and a confusion matrix, and a 4 by 4 base crosstalk matrix. The granularity
ladder is cell, tile, well, plate, each with an element to point at, and `sp-ops:relationships` is
MUST for a table that describes one — a threshold sweep has no element and no meaningful edge. Q7
had an answer for that shape, an empty edge list; this is worse, because these tables do belong to
something, the run of a pipeline step, which the specification cannot name. Two rungs are missing
below as well: `bases`, 561240 rows of one intensity per read, round and base, is read granularity,
and `cpg0021_sample`'s `image_metadata` is `(tile, round, channel)`.

Fix. Add a granularity for the parameters and diagnostics of a processing step, joined to nothing,
and say an empty edge list is correct for it. Add read granularity next to cell, since `reads` is
already first-class, and a per-image rung for Q6.

### Q18. The `well` attribute is a MUST and the delivery records only an ordinal

From `cpg0021_sample` · Affects the RFC-8 `well` attribute

The RFC-8 `well` attribute is a row and a column, and this delivery records neither: well identity
survives only in the `Well1` and `Well2` prefix of each file name, and the ND2 metadata has no well
field at all — not in `text_info`, not in the custom tag table, not in the experiment loop. The
format is recoverable only from the stage: matching the two wells' fields of view by index puts
their centres 39107.6 µm apart in x with a standard deviation of 0.1 µm, the 39.12 mm pitch of a
6-well plate, so they are adjacent columns of one row. Which row, and which two columns, is not
recoverable at all. The store writes `A/1` and `A/2` over two rows and three columns, and both are
inferences.

Fix. Q3 and Q4 one level down, and the same sentence fixes it: the row and column are expected from
the acquisition system or the submitter. Add that a writer that assigns them SHOULD say so, because
an ordinal in a file name is the common case and `A/1` asserts more than it knows.

### Q19. `library` has no unique row key, and the declared read join is not n:1

From `cpg0021_sample` · Affects `library`, edge `cardinality`

`library` is declared one row per guide, with the `reads` edge at `cardinality: "n:1"`. This library
has 82678 rows and 80862 distinct guides: the 2270 non-targeting rows are 454 sequences, each listed
five times, identical in every column, so no column identifies a row and the store indexes by
ordinal. All 80408 targeting rows are distinct, so the join is n:1 over them and n:5 over the
controls. `cardinality` cannot say that, and a reader that trusts `n:1` silently multiplies every
control read by five — the rows an analyst weights most heavily.

Fix. Say that the element on the `1` side of an `n:1` edge MUST have a unique key in the joined
column, and that a writer whose source does not MUST deduplicate or name the key. Q28's coverage
field is the neighbour and does not cover this: coverage is how much of a table an edge reaches,
this is one key reaching several rows.

## Assumptions the datasets contradict

| Q | Question | Dataset |
| --- | --- | --- |
| Q20 | The modalities need not differ in magnification | `experimentC` |
| Q21 | A merged image can be twice a tile, not 100 times | `experimentC` |
| Q22 | The recorded pixel size disagrees with the geometry | `experimentC`, `cpg0021_sample` |
| Q23 | Read length and barcode length differ | `experimentC`, `cpg0021_sample` |
| Q24 | The named `library` columns are not the ones delivered | `experimentC` |
| Q25 | The processed half was untested — now resolved | `experimentC` |
| Q26 | Feature definitions can exist with no values | `biohub_example` |
| Q27 | A denormalised column has drifted from its source | `biohub_example` |
| Q28 | Coverage, not cardinality, is what an edge needs | `biohub_example` |
| Q29 | An atlas sits above the screen the root fixes | `biohub_example` |
| Q30 | Stacked rounds cannot say they are unregistered | `experimentC_scallops` |
| Q31 | `sigma` is a real axis the fixed order excludes | `experimentC_scallops` |
| Q32 | A merged image is not already in the well frame | `experimentC_scallops` |
| Q33 | The peak join needs three columns, `on` takes one | `experimentC_scallops` |
| Q34 | A table is split by column group, not by element | `experimentC_scallops` |
| Q35 | A raw store can place one tile in twelve places | `cpg0021_sample` |
| Q36 | The modalities cover different parts of the well | `cpg0021_sample` |
| Q37 | The modality scale is not the ratio of pixel sizes | `cpg0021_sample` |

### Q20. The two modalities were imaged at the same magnification

From `experimentC` · Affects D2, D7, [](layout.md#registration)

Four places assume otherwise: [](layout.md) explains sixteen phenotyping tiles against four ISS
tiles by the magnifications differing, D2 rests its per-modality split of `tiles` and `merged` on
differing tile counts and footprints, and [](layout.md#registration) and D7 make the modality
registration an affine with a scale. In `experimentC` both modalities are 10x, 1.32 µm, 1024 by
1024, from the same position grid at the same two sites, and the measured nuclear offset between
them is 4 px in `y` and 0 in `x`: a translation at scale 1. The wording is "usually" and "may", so
nothing is violated — but D2's justification is void here, and the arrangement it rejected, one grid
shared by both modalities, is the one this dataset has. The store writes a byte-identical `layout`
under both.

Fix. Keep the layout, give D2 a justification that does not depend on the magnifications differing,
and say what a writer does when the modalities share a grid. Sharing one `layout` by reference is
the obvious economy and cannot currently be expressed.

### Q21. Tile and merged images do not differ by two orders of magnitude

From `experimentC` · Affects D2

D2 argues that a tile image and a merged image differ by two orders of magnitude in size, and so
need different chunking, sharding and pyramid depth. This well has two tiles, and its merged image
would be about 1028 by 2015 px, roughly twice a tile.

Fix. Keep the separation of `tiles` and `merged`, for the reason D8 gives: a reader opening one of
them gets everything computed on it. The size argument is not load-bearing and should not carry the
decision alone.

### Q22. The recorded pixel size and the measured geometry disagree by 2.2 percent

From `experimentC`, `cpg0021_sample` · Affects RFC-5 coordinate systems, [](features.md)

Every `experimentC` image records 1.32 µm per pixel. The 1280 µm stage spacing between the two sites
predicts 969.7 px; the measured displacement is 991 px, identical across all ten acquisitions.
Either the pixel is 1.2916 µm or the stage scale is off by 2.2 percent, and the dataset does not say
which. A coordinate system carries one pixel size with no way to mark it nominal or calibrated, and
a raw store has nowhere to put the residual, since [](features.md#tile-and-well-features) puts
`well_features` on a plate-level `wells` element. The store keeps 1.32 µm and uses the measured
displacement, so its well-frame micrometres deliberately are not stage micrometres.
`cpg0021_sample` reproduces this on both modalities at once, 1.0 percent for ISS and 0.4 for
phenotyping — and that the two differ means it is not one stage calibration, which is Q37.

Fix. Say which of the two a coordinate system carries; if both are wanted, the calibrated value
belongs on the image and the nominal one with Q6's provenance. Separately, allow [](features.md)'s
quality-control tables at `raw`, so a residual has somewhere to go before `processed` exists.

### Q23. Nine ISS rounds against twenty-nucleotide barcodes breaks the declared library join

From `experimentC`, `cpg0021_sample` · Affects the `reads` to `library` edge

The `reads` to `library` edge is a key join on `barcode` against `barcode`. `experimentC`'s library
holds 5738 twenty-nucleotide barcodes and nine rounds were imaged, so a read is at most nine bases:
the join cannot match unless one side is truncated, and nothing records the read length or a prefix
length. All 5738 are unique in their first nine bases, so the store adds a nine-base prefix column
to make the join expressible. `cpg0021_sample` shows the prefix join at scale — twelve cycles
against 20-nucleotide guides, the first twelve bases resolving 80862 of 82678 rows, which is every
row the table can resolve at any length. `biohub_example` needs nothing, 10 bases against ten
cycles; `experimentC_scallops` is where a prefix is not enough, because its reads were decoded
against another reference (Q15).

Fix. The read length is a property of the ISS modality and belongs in its metadata; with it the edge
can name a prefix length. The derived column is a workaround — a pipeline parameter in a table — and
it breaks the moment a screen gains a round.

### Q24. The library columns the specification names are not the ones the dataset has

From `experimentC`, `cpg0021_sample` · Affects [](joinable-components.md)

The library is specified as `barcode`, `perturbation_id`, `role`, `control_type`. `experimentC` has
`barcode`, `sgRNA`, `gene_symbol`: the store derives `role` and `control_type` from the symbol being
`non-targeting`, 100 rows of 5738, and sets `perturbation_id` to the gene symbol, which is no stable
id — 950 symbols, up to twelve guides each. `biohub_example` has exactly the four, so the mismatch
is not universal, and the column names are called illustrative — but the one table every screen has
cannot be written as specified.

Fix. Say which facts about a guide a reader needs rather than which columns: an identifier that
joins to a read, a perturbation identity, whether the guide is a control, and, per Q19, which column
is the key. A screen with only a gene symbol can then say so.

### Q25. The dataset exercises the raw half of the specification only

From `experimentC` · Resolved by `experimentC_scallops`

`experimentC` has no `intermediate` and no `processed` stage, and of the elements
[](joinable-components.md) names only `library` exists. Each of the others is a MAY, so the store is
conformant, but it carries no edge anywhere and `sp-ops:rounds`, `sp-ops:registration`,
`sp-ops:merged` and two of the three leaf node types are never written, so the central claim — that
this layout joins pixels to perturbations — was untested. `experimentC_scallops` is the counterpart
this entry asked for and writes all of them. The claim is still not demonstrated end to end, but for
a different reason: the chain is complete except for its last link, and that link is Q15.

Fix. None for the specification. What remains is a processed dataset whose reads join to its own
library, which none of the four deliveries provides.

### Q26. Feature definitions can exist without a feature matrix, and three vocabularies do not meet

From `biohub_example` · Affects [](features.md#cell-features)

Feature names are specified to live in the `var` of the table holding their values. This delivery
has 2935 feature definitions — type, compartment, channel, unit, software — and no per-cell values
at all, so they have no `var` to live in and the store writes them as a screen-level table, which
the specification has no slot for. The three feature vocabularies in the delivery are also mutually
disjoint: the plate's 2935 definitions, the atlas's 35246, and the 66 column names of the atlas
matrix share no identifier.

Fix. Say where a feature dictionary lives when it is shared across tables, and give it an edge to
the tables it describes. Then a checker can report the disjointness, which today nothing can see.

### Q27. A denormalised column disagrees with the table it was copied from

From `biohub_example` · Affects D9, edge `status`

`cell_data` carries both `barcode` and `perturbation_id`. The barcode join to the library is
perfect, all 831587 rows. The copied `perturbation_id` disagrees with what the library gives for the
same barcode in 80659 rows, 9.7 percent, over 335 barcodes, and 32 of its values are not in the
library at all. The cause is vocabulary drift, not corruption: retired HGNC symbols against current
ones — `AARS` against `AARS1`, `HIST1H2BK` against `H2BC12` — and 211 control groups collapsed into
one `NTC`. So following the edge and reading the column give different answers, and nothing says
which is authoritative. This is the exercise's strongest evidence for
[D9](design-decisions.md#d9-relationships-are-an-edge-list-on-the-lowest-collection-that-contains-both-ends):
the edge was right and the copy had rotted.

Fix. State that a column duplicating a value reachable over an edge is a cache and the edge is
authoritative, and make disagreement something `check_relationships` reports. A `status` of
`computed` today asserts that a join column exists, not that it still agrees.

### Q28. Coverage, not cardinality, is what an edge needs to declare

From `biohub_example` · Affects edge `cardinality`, [](joinable-components.md)

The `cells` table is a subset of the labels it describes: in the delivered excerpt 251 of 859
segmented cells have a row, because only cells with a confident barcode are listed. The edge says
`cardinality: "1:1"`, which is true of the rows present and badly misleading about what is absent.
Two thirds of the table's rows describe wells whose pixels are not in the delivery, so they have no
label element to point at from any store built out of it.

Fix. The query sketch already promises `check_relationships` will report "cardinality, coverage, and
dangling keys". Let an edge declare coverage too, so a reader knows before loading that a table
covers a third of its labels rather than all of them. Q15, Q19 and Q36 want the same field.

### Q29. The root is one screen, and an atlas sits above it

From `biohub_example` · Affects D1, [](features.md)

`atlas/aggregated_data.h5ad` is 1052 perturbations by 66 features, aggregated over 77 screens, with
Leiden clusterings at fifteen resolutions and UMAP and PHATE embeddings. [](features.md)'s
granularities are cell, tile, well and plate, so perturbation is missing, and
[D1](design-decisions.md#d1-a-plate-collection-is-one-physical-plate-at-one-stage) fixes the root as
one screen, so there is no level above a screen to hold something aggregated over 77 of them. The
store omits the atlas, because putting it inside this screen would assert that it belongs to this
screen.

Fix. Add perturbation as a granularity, joined by an edge to `library` rather than to a spatial
element, and say whether a collection above the screen is in scope. A cross-screen atlas is the
object an analyst is most likely to open first.

### Q30. Stacked rounds cannot declare that they are not registered

From `experimentC_scallops` · Affects `sp-ops:registration`, D6

[D6](design-decisions.md#d6-axes-are-a-subset-of-round-t-c-z-y-x-in-that-order-singleton-axes-are-omitted-and-rounds-are-always-stacked)
stacks rounds always, and `sp-ops:rounds` MUST record the acquisition behind every slice. The stitch
stage produces nine well images, one per cycle, each stitched on its own but all on one grid, so the
store stacks them: `(9, 5, 1002, 1972)`, indistinguishable from the registered array in
`plate1_processed` — same shape, axes, channels, coordinate system, pixel size. The difference
between them is the whole ops stage. `sp-ops:registration` is the only key that would say so and it
is a SHOULD, so its absence means "not stated" rather than "not registered", and a reader gets
rounds misaligned by up to 34 px with nothing warning it. [](layout.md) does say channels are "not
yet aligned" in `raw`, but raw is the one case where the layout itself carries the answer, because
channels are separate elements there.

Fix. Make `sp-ops:registration` MUST on any image with a `round` axis, and let it state that rounds
are unregistered as well as name an anchor and a reference. The same applies to channels within a
round; Q50 makes the argument one stage earlier.

### Q31. `sigma` is a real axis the fixed order has no room for

From `experimentC_scallops` · Affects D6

D6 fixes the axes as a subset of `round, t, c, z, y, x` and rejects a writer-chosen order until "a
use case shows a measurable gain". The spot detection step writes `(sigma, t, c, y, x)`, giving
`sigma`, the scale-space parameter of a multi-scale blob detector, a `type` of `null` because
OME-NGFF has no type for it. It is singleton in this run, which D6 would omit, but it is not
incidental: `sigma` is a column on `peaks` and on `reads` and part of the key that joins them.

Fix. This is the use case D6 asked for, and it argues for something narrower than a free order:
allow writer-defined axes after the known ones, ordered but not named by this specification. Then
say a writer SHOULD flatten such an axis into columns when it is singleton, which is what the store
did.

### Q32. A merged image is not already in the well frame

From `experimentC_scallops` · Affects [](layout.md#registration)

[](layout.md#registration) ends "Merged images are already in the `well` frame". This stitcher crops
`fuse_crop_width`, 11 px, from every edge of the fused mosaic: the two tiles span 1024 by 1993.7 px
and every array in the dataset is 1002 by 1972, so the merged image's first pixel is at well pixel
(11, 11) — and every scallops group declares `translation: [0, 0, 0]`. A reader that believes either
the sentence or the source metadata places the merged image, its five label arrays and its 15590
reads 11 px from where they are, which is more than the round registration residual the ops stage
worked to remove. The store derives 14.52 µm from `fuse_crop_width` and the array shapes.

Fix. Delete the sentence. A merged image's transform into the well frame is whatever stitching
produced, commonly not the identity. Q22 is the neighbour: there the well and stage frames disagree
on scale, here on origin.

### Q33. `read` is a position hash, and the peak join needs three columns

From `experimentC_scallops`, `cpg0021_sample` · Affects edge `on`, [](joinable-components.md)

[](joinable-components.md) gives `peaks` the columns `x, y, read` and calls `read` the join key to
its decoded read. `peaks` has no `read` column: it has `y, x, sigma, peak`, and the join to `reads`
is on `(y, x, sigma)`, which matches all 15590 exactly. And `read` is not an identifier: it is
`y * 1972 + x`, the flattened pixel index in the merged image, so re-cropping or re-stitching
renumbers every read and two wells in one table collide. The composite key is the more serious half,
because `on` is one `{left, right}` pair and cannot express it — the store writes the edge on `y`
alone at `status: "suggested"`, the only expressible thing and wrong. `cpg0021_sample` hits the same
wall with `image_metadata` keyed on `(tile, round, channel)`.

Fix. Let `on` take a list of column pairs. Separately, either require a read identifier that does
not encode geometry, or say that `read` is scoped to one image and drop the claim that `peaks`
carries it.

### Q34. A compartment's table is split by column group, not by source

From `experimentC_scallops` · Affects [](features.md#merged-and-split-tables)

[](features.md#merged-and-split-tables) splits a table by the element it describes. This pipeline
splits by column group instead: each compartment arrives as `A1.parquet` with the measurements and
`A1-objects.parquet` with the bounding box, centre and area, keyed on the same label and neither
complete on its own. For cytosol they disagree — 4525 labels, 4525 rows of geometry, 4508 of
measurements — so 17 objects have a bounding box and no features. Above them `merge/A1.parquet`
fuses all three compartments and the barcode calls into 4706 by 275 with `Cells_`, `Cytoplasm_` and
`Nuclei_` prefixes: a fourth merged encoding where features.md lists three, keyed on the nucleus, so
every cell-level and cytosol-level value is left-joined.

Fix. Say that a split is by described element and that one element's table is one table, so a writer
shipping measurements and geometry separately is expected to join them. Then pick the default merged
encoding features.md leaves open, and note the prefix form as a fourth in use.

### Q35. A raw store can place one field of view in twelve places

From `cpg0021_sample` · Affects D5, `sp-ops:tiles.layout`

`layout` holds one polygon per field of view, so the tile footprint is a property of the tile, while
[D5](design-decisions.md#d5-raw-channels-are-separate-images-with-their-own-coordinate-systems)
makes every raw channel of every round its own multiscale with its own coordinate system, so the
tile-to-well transform is per channel array and can differ per round. The two disagree about
granularity, and this dataset has the metadata to make the disagreement matter. Every ND2 records
its own stage coordinates, and for the same field of view they move across the twelve ISS rounds by
50 µm in x and 20 µm in y, which is 41 px and 17 px. The images do not: registering the nuclear
channel of `A/1` tile 0 against cycle 1 across all twelve rounds puts every round within 2.5 px of
the reference, at correlations of 0.977 to 0.993. The recorded per-round position is noise.

So a writer that placed each round's channel arrays at their own recorded stage positions — the
obvious reading of D5, and the only one under which a per-array transform earns its existence —
would produce a store misregistered by up to 41 px, with every MUST satisfied, `layout` untouched,
and nothing anywhere to detect it. A writer that used one footprint per tile gets it right, and the
specification does not say which to do.

Fix. Say that a tile's footprint in the well frame is a property of the tile, that the transforms of
its channel arrays differ from it only by measured channel and round alignment, and that a writer
MUST NOT pass an instrument's per-image position readout through as that alignment. Then Q40's
coordinate system on the tile collection stops being only an economy: it is where the footprint
belongs, and it makes this error unwritable rather than merely discouraged.

### Q36. The two modalities cover different parts of the well

From `cpg0021_sample` · Affects [](layout.md), D2

Nothing requires a well's modalities to cover the same ground, and here they do not. In `A/1` the
eight ISS fields cover 23.5 mm² and the forty phenotyping fields 28.2 mm², intersecting over
17.5 mm²: 74 percent of the ISS footprint and 62 percent of the phenotyping one. In `A/2` it is 63
and 58 percent, and each well has about 10.8 mm² of phenotyped area with no ISS coverage at all.
[](layout.md) permits grids that "may differ in tile count, size, and overlap" and D2 rests on
exactly that — but the central claim is that the layout joins pixels to perturbations, and 38 to 42
percent of the phenotyped area here can never receive a read. The two `layout` elements are the only
record, they are per modality, and nothing compares them.

Fix. Nothing changes in the layout. The intersection of the modalities' footprints is a fact a
reader needs before deciding what a store is good for, and it is computable from what is already
written: make it a validator check, and say in [](layout.md) that a partial overlap is expected in a
subset delivery. This is Q28's argument for pixels rather than rows.

### Q37. The modality registration scale is not the ratio of the recorded pixel sizes

From `cpg0021_sample` · Affects D7, [](layout.md#registration)

D7 makes the modality registration "an affine that includes a scale", and both merged images keep
their native pixel size. This dataset agrees and then shows the scale cannot be composed from those
two sizes: ISS records 1.2142857 µm at 10x and phenotyping 0.6071429 µm at 20x, a ratio of exactly
2, while solving each grid against its own stage spacing puts the ISS pixel 1.0 percent and the
phenotyping pixel 0.4 percent below the recorded value, a measured ratio of 1.988. Registering the
phenotyping nuclear channel onto the ISS one over 24 tile pairs per well, a translation alone leaves
up to 30.4 µm across the well and adding a scale of 1.00636 leaves 5.3 µm. So composing the declared
pixel sizes is wrong by 25 ISS pixels at the edge of the well, and Q22's gap is what lets it happen.

Fix. Q22's, for two modalities at once: a coordinate system says whether its pixel size is nominal
or calibrated. And D7 should say the modality transform is measured, not derived from the
objectives, which are what a writer will reach for and are in exact ratio when the optics are not.

## Inconsistencies inside the specification

| Q | Question | Dataset |
| --- | --- | --- |
| Q38 | The well is the only name spanning two path segments | every store |
| Q39 | Two pages disagree on where the stitch transform lives | every store |
| Q40 | Placing raw tiles costs one transform per channel array | `experimentC`, `cpg0021_sample` |
| Q41 | `sp-ops:channels` in array order says nothing in `raw` | `experimentC` |
| Q42 | The inside of a multiscale is never shown | every store |
| Q43 | A single-resolution image has no home for its channels | `biohub_example` |
| Q44 | Conforming to the axis order can rewrite pixels | `biohub_example` |
| Q45 | No transform is written with its input's dimensionality | every store |
| Q46 | Labels need not agree with their source image | `biohub_example` |
| Q47 | Two segmentations of one compartment cannot be told apart | `experimentC_scallops` |
| Q48 | Compartment membership rides on a numbering convention | `experimentC_scallops` |
| Q49 | `layout` and the tile transforms need not agree | `cpg0021_sample` |
| Q50 | `sp-ops:registration` has no home in `raw` | `cpg0021_sample` |
| Q51 | Channel names are not unique within a well | `cpg0021_sample` |

### Q38. The well is the only name that spans two path segments

From every store · Affects [](layout.md), D3

Every level is one Zarr path segment except the well, named `A/1`. Writing it forces an intermediate
group at the row which is neither an RFC-8 node nor an sp-ops one, and the stores leave it an
untyped Zarr group. D3 argues that `=` is unavailable in names because OME-NGFF path names are
restricted to alphanumerics, `-` and `_`, and by that same rule `A/1` is not a legal single name
either.

Fix. Either make row and column two levels of the hierarchy, matching the RFC-8 `plate` attribute
that lists rows and columns separately, or name the well `A1` and leave the row and column in the
`well` attribute where they already are. The second is smaller and loses nothing, because names
carry no meaning.

### Q39. Two pages disagree on where the stitching transform lives

From every store · Affects [](layout.md#modalities-tiles-and-merged-images), [](extension.md)

[](layout.md#modalities-tiles-and-merged-images) says tile images map into the well frame by the
stitching transform stored on the modality collection. The complete example in [](extension.md) puts
`scene`, and the `well` coordinate system, on the well collection. Only the well collection works:
the well frame is shared by both modalities, so the well is the lowest collection containing both
endpoints, which is the rule [](joinable-components.md#storage) states for edges and
[](layout.md#registration) for transformations. The stores follow [](extension.md).

Fix. Fix the sentence in [](layout.md).

### Q40. Placing raw tiles in the well frame costs one transform per channel array

From `experimentC`, `cpg0021_sample` · Affects D5, RFC-5 coordinate systems

D5 makes every raw channel its own multiscale with its own coordinate system, and no coordinate
system is defined for a raw tile as a whole. Mapping one well of `experimentC` into the well frame
took 94 transforms carrying two distinct translations between them; `cpg0021_sample` writes 680 per
well carrying 48 distinct positions, sixty copies of each ISS position and five of each phenotyping
one. The multiplier is rounds times channels either way.

Fix. Define a coordinate system on the tile collection. Stitching is then one transform per tile
into the well frame and channel alignment one per channel into the tile frame, which is exactly the
first and third registration steps of [](layout.md#registration). The count stops multiplying, and
Q35 shows the same coordinate system is where the tile footprint belongs.

### Q41. `sp-ops:channels` in array order says nothing in `raw`

From `experimentC`, `cpg0021_sample` · Affects `sp-ops:channels`, `sp-ops:axis`

The key is defined as one entry per channel in array order. A raw channel array has axes `(y, x)`
and no `c` axis, so every raw channel node carries a list of one and the ordering clause is vacuous.
`sp-ops:axis` on the same node then repeats an index that the node's position in `nodes` already
gives.

Fix. State that in `raw` the list holds exactly one entry, and either drop `index` from
`sp-ops:axis` on a channel node or say what it adds. The key earns its full definition in
`processed`, where channels are stacked.

### Q42. The inside of a multiscale is never shown

From every store · Affects [](extension.md), A3

The specification shows a multiscale node's attributes but never its levels. RFC-8 requires a
singlescale node to carry `coordinateTransformations` in its attributes, while [](extension.md) says
a node with a `path` and no `nodes` is stored in its own `zarr.json`, which a Zarr array cannot do
for an RFC-8 `nodes` list. The stores inline the singlescale nodes in the multiscale group's
`zarr.json`, as RFC-8's own example does, with a `scale` at level 0 and a `sequence` of `scale` and
`translation` below it, for the half-pixel shift a 2x2 mean introduces. Related: RFC-5 as published
names a coordinate system with `name`, while RFC-8 and every example here use `id`.

Fix. Show one complete multiscale, levels included, in [](extension.md), and note the `name` against
`id` divergence in A3, which currently records RFC-5 as released with no caveat. Q45 is the same
problem one level up.

### Q43. `sp-ops:channels` is specified on `multiscale`, so a single-resolution image has no home for it

From `biohub_example` · Affects `sp-ops:channels`

The registry binds `sp-ops:channels` to `multiscale`, and RFC-8 also defines `singlescale`. The
three RGBA overlays here have exactly one resolution level, and the store writes them as one-level
multiscales so their channels have the specified home, which dresses a singlescale as a multiscale
for the sake of one attribute.

Fix. Bind the key to both node types, or say that a single-resolution image is written as a
one-level multiscale and `singlescale` appears only inside one.

### Q44. The fixed axis order can require rewriting pixels, not metadata

From `biohub_example` · Affects D6

D6 fixes the axis order as a subset of `round, t, c, z, y, x`. The source's images are
`(1, 6, 1, 2048, 2048)` with uppercase `T, C, Z, Y, X` and singleton `T` and `Z`: squeezing and
lowercasing those is a metadata edit. The three overlays are stored channel-last, `(y, x, rgba)`,
and conforming means transposing the array.

Fix. Keep the rule, it earns its place. Say in D6 that conforming may require rewriting pixels
rather than metadata, so that a conversion is budgeted as a rewrite.

### Q45. No transform in the specification has the dimensionality of its input

From every store · Affects [](extension.md), [](layout.md#registration)

[](layout.md#registration) notes that a tile-to-well transform "is a `byDimension` transform in
practice, because `round` and `c` pass through unchanged; the example shows the spatial part only".
The complete example in [](extension.md) then maps `./pheno/merged/image`, a `(c, y, x)` image, into
the two-axis `well` frame with a two by three affine. No `byDimension` transform is ever written
out, and the stores follow the examples, so their transforms are underdetermined the same way.

Fix. Write one `byDimension` transform in full in [](extension.md). It is the form every real store
needs and the only one the specification never shows. This is Q42 one level up: the parts a writer
cannot guess are the parts that are abbreviated.

### Q46. Nothing requires a labels element to agree with the image it came from

From `biohub_example` · Affects `labels.source`

All twelve label groups declare 0.325 µm per pixel in the store and 0.65 in the source, on arrays of
identical shape to the image, which declares 0.325. The source says which is wrong: an
`op_units_correction` note records that the image was corrected from 0.65 to 0.325 and the label
groups were not. The pixels confirm it twice — the tail of every `cell_uid` in the excerpt is a
`cell_seg` value at 1:1, and `membrane_prediction` is enriched 2.6-fold on `cell_seg` boundaries at
1:1, 1.665 against 0.651 in the interiors, while under a two-fold reading the enrichment vanishes,
0.685 against 0.669. So the store corrects the labels, and a naive conversion would have produced a
store misregistered by a factor of two, silently, with every MUST satisfied.

Fix. Require a labels element and its `labels.source` image to agree on physical extent, and make it
a validator check. `scripts/check_sp_ops_zarr.py` implements it as an advisory: restoring the
source's 0.65 makes it report `extent (1331.2, 1331.2) um disagrees with its source image (665.6,
665.6) um`. Q49 is the same shape for geometry.

### Q47. Two segmentations of one compartment have no expression

From `experimentC_scallops` · Affects labels naming, D3, [](extension.md)

The pipeline ships two compartments twice: `A1-nuclei` with 4706 labels and `A1-nuclei.all` with
4823, `A1-cell` with 4589 and `A1-cell.all` with 4706, the `.all` pass being the segmentation before
filtering and the filtered set a strict subset. Nothing here distinguishes them — they are two
labels elements of the same compartment at the same granularity on the same grid, and a reader
meeting `nuclei` and `nuclei_unfiltered` side by side has only the names to go on, which
[D3](design-decisions.md#d3-names-are-opaque-and-attributes-carry-the-meaning) says carry no
meaning. The names cannot be carried over either: RFC-8 ids permit `.` and OME-NGFF path names do
not, so `A1-nuclei.all` is a legal id and an illegal path.

Fix. Let a labels element name its compartment and, optionally, the processing variant it
represents, so that "nuclei, unfiltered" is metadata rather than a naming convention. Same shape as
Q10: what a derived element is, as against what it is called. The `.` divergence is worth one line
in [](extension.md).

### Q48. Compartment membership rides on a numbering convention

From `experimentC_scallops` · Affects [](features.md), D9

[](features.md) requires a compartment other than the cell to record its parent as a column,
`cell_label` in the examples, joined to the `cells` labels by an edge. None of the three feature
tables here has one. Membership is implicit: the pipeline numbers a nucleus, its cell and its
cytosol with the same integer, so nucleus 1743 belongs to cell 1743 — exact where both exist, silent
where they do not, and 117 of the 4706 nuclei have no cell. Nothing states the convention, and it is
not the only possible one; the store derives `cell_label` from it and writes 0 where no cell exists,
a guess that happens to be checkable, since the labels arrays agree.

Fix. Keep the column requirement. Add that a writer deriving membership from shared numbering MUST
materialise it as a column, and that the edge is what a reader follows, never the numbering. Q12 is
the same requirement failing the other way.

### Q49. Nothing requires `layout` and the tile-to-well transforms to agree

From `cpg0021_sample` · Affects `sp-ops:tiles.layout`, `scene`

A tile's position in the well frame is written twice: as a polygon in the modality's `layout`, and
as the transform from the tile's coordinate system into `well` in the containing collection's
`scene`. The specification requires both and relates them nowhere, so a store can take its layout
from the images and its transforms from the stage readout, or the reverse, and satisfy every MUST
while placing one field of view in two places. Rewriting this store's ISS layout at the recorded
stage positions, which is what a writer following the metadata alone produces, leaves the transforms
untouched and moves seven of the eight polygons by up to 82 µm — 68 px, about half a tile's overlap
strip.

Fix. Require that a tile's `layout` polygon and its tile-to-well transforms place it in the same
position, and make it a validator check; `scripts/check_sp_ops_zarr.py` implements the comparison as
an advisory, `check_layout_against_scene`. This is Q46 for geometry rather than pixel size: two
records of one fact, no requirement that they agree, and a plausible conversion that breaks it
silently.

### Q50. `sp-ops:registration` has no home in `raw`, where the modality registration first happens

From `cpg0021_sample` · Affects `sp-ops:registration`, [](layout.md#registration)

`sp-ops:registration` is specified on a processed multiscale, and [](layout.md#registration) puts
the modality registration between the two merged images. A raw store has neither. It does have the
`well` coordinate system, shared by both modalities, which [](extension.md)'s complete example puts
on the well collection with transforms for both — so the moment a raw store writes those transforms
it has registered the modalities, and it has no attribute in which to say so. This store carries a
measured scale of 1.00636 and a translation on all 200 phenotyping transforms of well `A/1`, from 24
tile pairs at correlations of 0.77 to 0.91, and records neither the anchor channel, the reference
modality, nor that any registration happened. A reader cannot tell it from a store whose phenotyping
tiles were placed by their stage coordinates, 30 µm out.

Fix. Bind `sp-ops:registration` to any node that declares a transform into a frame it shares with
another element, not only to a processed multiscale, and let a well collection carry one. Then a raw
store can say which channel anchored it and what the transform was measured from — the same thing
Q10 asks for derived elements and Q6 for raw pixels. Q30 is this one stage later.

### Q51. Channel names are not unique within a well, and channels are addressed by name

From `cpg0021_sample` · Affects `sp-ops:channels`, [](layout.md#reading-the-store-with-spatialdata)

[](layout.md#reading-the-store-with-spatialdata) reads a channel as `iss.sel(round=0, c="DAPI")`,
and `sp-ops:channels` is authoritative over array position, so the name is the handle. Here ISS
records `DAPI, Cy3, A594, Cy5, Cy7` and phenotyping records `DAPI, GFP, A594, Cy5, 750`: `A594` and
`Cy5` name a sequencing base in one modality and an antibody or dye stain in the other, on the same
well, at the same stage. `role` does not disambiguate them, because it is what the channel is for
and not what it is — `A594` is `base` under `iss` and `stain` under `pheno` — so selecting by name
across the well returns two different measurements. This is the collision Q1 and Q9 make possible:
once base identity and marker identity are absent, the only names left are instrument settings, and
instrument settings repeat.

Fix. Say that `sp-ops:channels` names are unique within a modality, not within a well, and that a
channel is addressed by modality and name together. Then Q1's dye field and Q9's marker field
become what makes two `A594` channels distinguishable, which is the strongest argument for either.

## What the datasets confirm

Several decisions held up under the exercise, which is worth recording alongside the rest.

- **D2 and D7, the modalities differ in magnification.** `biohub_example` images ISS at 5x/0.15 and
  phenotyping at 20x/0.55, a ratio of four; `cpg0021_sample` images 10x/0.45 against 20x/0.75, a
  ratio of two, with 8 and 40 fields of view per well. So the modality registration really is an
  affine with a scale and the two grids really are independent. Q20 is about the justification being
  written as though it always holds; Q37 is the refinement.
- **D3, names are opaque.** `experimentC`'s missing ISS cycle 6 needed no name: the store writes
  `round5` with `sp-ops:axis` value 7 and the acquisition it came from. `cpg0021_sample` delivers
  wells as `Well1` and `Well2` with no row or column anywhere, so every level had to be named from
  something other than the delivery's own strings, and the two things the store could not invent are
  the two the reader is told about in Q18 rather than left to infer from a path. Q11 is the
  counter-example, a store that encoded a join key into a string.
- **D4, there is no fixation timepoint level.** `experimentC_scallops` is the dataset D4 argues from
  and it holds up: a `t` axis whose values are the cycle labels 1 to 10 without 6, transform folders
  `t=2` to `t=10`, and a `bases` table whose `t` column is the cycle. Every one is this
  specification's `round`, and nothing in the dataset uses `t` for elapsed time.
- **D5 and D7, raw channels are separate and the anchor is declared.** In `experimentC` the nuclear
  channel drifts by up to 11 px in `y` and 17 px in `x` between the first and last ISS round, so
  rounds are genuinely unregistered in `raw`, and the base channels share almost no structure with
  it — phase-correlation peaks of 0.02 to 0.04 — so within-round alignment cannot be measured
  through the nuclear anchor from those images alone. That is the case for declaring the anchor
  rather than inferring it. `cpg0021_sample` has a nuclear channel in all thirteen acquisitions, so
  every round and both modalities anchor on the same kind of thing, which `biohub_example` could not
  provide in Q9 — and it also shows that the per-channel coordinate system is the mechanism by
  which a plausible writer misregisters a store, which is Q35.
- **D6, singleton axes are omitted.** `experimentC` has one z plane per channel and `biohub_example`
  ships `(1, 6, 1, 2048, 2048)` with singleton `T` and `Z`. Neither says anything the squeezed form
  does not.
- **D8, compartments are not fixed and are not nested.** `biohub_example` segments twelve
  compartments, ten of them organelle classes inside the cell, and the flat arrangement takes them
  without strain. Nesting them under `cells` would have failed on the first nucleolus.
- **D9, relationships are an edge list.** Q27 is the case for it: the edge to the library is exact
  over all 831587 rows while the column copied from it has drifted on 9.7 percent of them. A reader
  that follows edges gets the right answer and one that trusts the copy does not.

## Grouping and priority

A read of the questions above through the lens that the layout is permissive: a store MAY
ship only the subset of collections a dataset needs. Most divergences recorded on this page
are a store using part of the object by design, which is fine. The entries that need a spec
response fall into a few groups, and the largest risk is not the MUST conflicts.

### 1. MUST tension: the spec is not permissive enough — done

A MUST fired on a store the specification elsewhere says is legal. Resolved by relaxing the
MUST to conditional ("MUST if present"), not by failing the store. Implemented in
[](extension.md) and [](layout.md).

- **Q8** `sp-ops:merged.source` MUST reference the tiles stitched from, but a merged-only
  delivery discarded its tiles. [](layout.md) already blesses this store. `source` MAY now
  hold tile ids, or be empty.
- **Q14** The `tiles`/`tile` level table made a `tile` MUST exist under any `tiles`
  collection, so a stitch stage that writes `tiles/` only to hold `layout` and
  tile-granularity tables (no per-tile array) was non-conformant, and the `tiles` row did not
  state the `intermediate` case at all. The `tile` row now reads "if it holds per-tile
  images," and `intermediate` is named alongside `raw`/`processed`.
- **Q7** `sp-ops:relationships` MUST on a table describing an element, but a raw-only
  `library` joins to nothing. [](extension.md) now states an empty edge list is correct.

### 2. Silent-correctness traps (the real risk) — pending

A plausible writer following the spec and the source metadata produces a store where every
MUST holds and the pixels or joins are wrong, with nothing to detect it. These argue for a
validator layer more than for new fields. Ranked by blast radius:

1. **Q35** a raw store can place one field of view in 12 places. Per-channel transforms vs
   one footprint per tile; passing the instrument's per-image stage readout through
   misregisters by up to 41 px. Add: a tile footprint is a property of the tile, and a
   writer MUST NOT pass a per-image position readout through as alignment.
2. **Q19** `library` has no unique row key, and the declared `n:1` read join is `n:5` for
   the non-targeting rows, so a reader that trusts `n:1` multiplies every control read by
   five. The `1` side of an `n:1` edge MUST have a unique key.
3. **Q46** nothing requires a labels element to agree with its source image on physical
   extent; a factor-of-two pixel-size mismatch shipped silently. Require agreement, make it
   a check.
4. **Q30 / Q50** a stacked-but-unregistered image is indistinguishable from a registered
   one, and `sp-ops:registration` is a SHOULD with no home in `raw`. Make it MUST on any
   image with a `round` axis, or any node declaring a transform into a shared frame, and let
   it state "not registered".
5. **Q49** nothing requires `layout` and the tile-to-well transforms to agree; they can
   differ by 82 px and both satisfy their MUSTs. Require agreement, make it a check.

Same family, lower blast radius: Q37 (modality scale is not the ratio of recorded pixel
sizes, 30 µm), Q32 (a merged image is not already in the well frame; the sentence is false,
11 px), Q27 (a denormalised column drifted 9.7 percent from the authoritative edge), Q22
(recorded pixel size vs measured geometry, 2.2 percent), Q51 (channel names are not unique
within a well; selecting by name returns two different measurements), Q15 (a `library` edge
that matches 2.4 percent of reads, i.e. chance), Q5 (renumbering tiles loses the site-id
link silently).

### 3. Provenance: reuse the OME model, do not invent sp-ops keys — pending

Q6 (raw instrument metadata) and Q10 (derived-element provenance) are real gaps, but the
proposed fix of an `sp-ops:instrument` key or a bespoke table is the wrong default. The OME
data model already covers most of Q6's list: `Instrument`/`Objective`/`Detector`, per-image
acquisition date and instrument/objective settings, per-channel detector settings, and
per-plane stage position, exposure and timestamp. RFC-8 states it replaces
`bioformats2raw.layout` and that some of that metadata "is not yet represented in the
proposed structures... intended to be addressed through... extensions." So the right ask is
to reuse the OME data model and Bio-Formats, extending them where a field is genuinely
missing, rather than mint sp-ops-private keys. The layout-provenance half of **Q2**
(measured vs a stage readout) is the same shape at the tile level.

### 4. Join and table model gaps (additive, not blocking) — pending

None blocks conformance; each lets a store state something true it currently cannot.

- **Q33** `on` takes one column pair; a peak-to-read join needs three (`y, x, sigma`).
- **Q28** an edge declares cardinality but not coverage; a table over a third of its labels
  looks like one over all.
- **Q11 / Q48** a cell or compartment table needs plain label and parent-label columns
  rather than an id parsed out of a string, or membership riding on a numbering convention.
- **Q12** compartment membership can be unrecorded; a spatial join at `status: suggested`
  recovers it. Mechanism works; add a SHOULD.
- **Q23 / Q26 / Q34** a read length the join needs, an edge from feature definitions to the
  tables they describe, and a fourth merged-table encoding `features.md` does not name.

### 5. Internal inconsistencies and missing examples (editorial) — pending

- **Q38** the well name `A/1` is two nested HCS-style levels (row `A`, then `1`), not a
  single node id. State that explicitly so the id-rule contradiction dissolves.
- **Q1 / Q9** the `role` vocabulary is open, not exhaustive; say so. Base identity (Q1) is
  a `processed`-stage decision, and a channel MAY carry its marker or fluorophore (Q9).
  Rewording, not a MUST conflict.
- **Q39** two pages disagree on where the stitching transform lives; only the well
  collection works.
- **Q45 / Q42** no `byDimension` transform is ever written out, and a multiscale's inner
  levels are never shown, yet both are the forms a writer needs.
- **Q32** delete "merged images are already in the `well` frame" (also group 2).
- **Q41, Q44, Q47, Q24, Q21, Q20, Q40, Q36** smaller wording and example fixes.

### 6. Partial or missing data: not a spec problem — pending

The requirement is right; the one delivery lacks the fact. At most a documentation
sentence. **Q3** (plate id in a directory name only), **Q18** (the `well` ordinal), **Q16**
(a `labels.source` that dangles in the delivery), **Q25** (the raw-only evidence gap, now
largely settled by the scallops dataset). The per-dataset "hygiene" notes are delivery
defects, not spec findings.

Reviewed and not spec changes: **Q4** (a subset declaring only the present wells is
allowable under the OME HCS spec) and **Q43** (a single-resolution image is written as a
one-level multiscale, which is already supported).

### 7. Confirmations

D2/D7 (modalities differ in magnification, ratios of 4 and 2), D3 (opaque names), D4 (no
fixation-timepoint level, `t` maps to `round`), D5, D6, D8, D9 all held. The scallops
dataset settles Q1, Q2, Q5, Q25.

### Carried over from the merged spec PR

The earlier conformance comment raised three items. Two are reproduced here on other
datasets: `merged.source` (Q8, done — see group 1) and the well name (Q38, still pending —
see group 5). The third is not on this page: blank/background reference fields of view used
for illumination correction and background subtraction have no home, so a converter drops
them. Worth a `kind` field on `sp-ops:tile` (`field` vs `background`) or a sibling
`calibration` collection.

### Suggested order

1. ~~Relax the group 1 MUSTs (Q8, Q14, Q7), which are cheap and match the permissive
   intent.~~ Done.
2. Decide the validator story for group 2; the traps are the real risk and several are
   already implemented as advisories.
3. Reuse OME and Bio-Formats for provenance (Q6, Q10) rather than new keys.
4. Add the blank-tile capability the merged PR raised.
