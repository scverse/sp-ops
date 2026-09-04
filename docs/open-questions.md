# Open questions

Every entry on this page came out of writing a real dataset as a conformant store and
checking the result against the specification. Each has an id, the observation from that
exercise, and what the specification should do about it. The ids are stable; an entry that is
resolved moves into the page it fixes.

Four datasets are described first, because every entry refers to one of them.
`experimentC` covers the `raw` stage and `biohub_example` the `processed` stage;
`experimentC_scallops` is `experimentC` after a pipeline, and covers `intermediate` and
`processed` over pixels whose raw form is already written. `cpg0021_sample` is a second `raw`
delivery, in a vendor format with its acquisition metadata intact, and it is the one that
says what a `raw` store is being asked to carry. Between them they exercise the whole
specification, and where they disagree is recorded below.

## Dataset example: experimentC

`experimentC` is an optical pooled screen delivered as flat TIFF exports and one barcode
table. It covers one well of one plate, two fields of view, nine ISS rounds, and one
phenotyping round, with no derived data of any kind, so it exercises the `raw` stage and
nothing else.

| What | Value |
| --- | --- |
| wells | one, `A1` |
| fields of view | two, Micro-Manager sites 102 and 103, overlapping by about 33 px |
| ISS rounds | nine, cycle labels 1 to 5 and 7 to 10; cycle 6 was not acquired |
| ISS channels | five: `DAPI_10p`, `Cy3`, `A594`, `Cy5`, `Cy7` |
| phenotyping | one round, two channels: `DAPI_10p`, `GFP` |
| tile shape | `(c, 1024, 1024)`, `uint16`, one z plane, one timepoint |
| pixel size | 1.32 µm, 10x objective, 2x2 binning, in both modalities |
| library | 5738 guides over 950 gene symbols, 100 of them non-targeting |
| derived data | none: no reads, peaks, labels, or feature tables |

This is the dataset behind the running example in [](layout.md). The nine ISS rounds whose
cycle labels skip 6 are the gap [](design-decisions.md#d3-names-are-opaque-and-attributes-carry-the-meaning)
describes, and the store below writes it as `round5` with `value: 7`.

### The store

`scripts/build_experimentC_zarr.py` writes the dataset as one screen collection. Because the
dataset holds raw data only, the screen has one plate collection, at stage `raw`, and the
screen-level `library` table.

```text
experimentC.zarr/
├── zarr.json                    # collection; sp-ops:spec
├── library                      # table: one row per guide
└── plate1_raw/                  # collection; plate; sp-ops:plate; sp-ops:stage "raw"
    └── A/1/                     # collection; well {row A, column 1}; scene: the well frame
        ├── iss/                 # collection; sp-ops:modality "iss"
        │   └── tiles/           # collection; sp-ops:tiles
        │       ├── layout       # shapes: one polygon per tile, measured, not declared
        │       ├── tile102/     # collection; sp-ops:tile {"index": 102}
        │       │   ├── round0/  # collection; acquisition iss-c1; sp-ops:axis {round, 0, 1}
        │       │   │   ├── channel0   # multiscale (y, x); DAPI_10p, role nuclear
        │       │   │   └── channel1 ... channel4   # Cy3, A594, Cy5, Cy7; role base
        │       │   ├── round1/  # acquisition iss-c2
        │       │   └── ... round8/    # acquisition iss-c10; round5 is cycle 7
        │       └── tile103/     # collection; sp-ops:tile {"index": 103}
        └── pheno/               # collection; sp-ops:modality "pheno"; acquisition pheno
            └── tiles/           # one round only, so no round level
                ├── layout
                └── tile102/ tile103/
                    ├── channel0 # DAPI_10p, role nuclear
                    └── channel1 # GFP, role stain
```

123 RFC-8 nodes, 94 channel multiscales, 282 arrays over three pyramid levels, 169 MB.

The tile offsets in the well frame are measured, not declared. The dataset ships no position
list, so `layout` and the tile-to-well transforms come from normalised cross correlation of
the nuclear overlap strip between the two fields of view. Tile 103 sits 991 px in `x` and 4 px
in `y` from tile 102, the same value in all nine ISS rounds and in the phenotyping round, at
correlations of 0.945 to 0.954.

`scripts/check_sp_ops_zarr.py` walks the store from the root collection, checks every
requirement in the [](extension.md) registry and the [](layout.md) level table, and compares
every channel array against the TIFF page it was written from.

```bash
python scripts/build_experimentC_zarr.py path/to/experimentC experimentC.zarr
python scripts/check_sp_ops_zarr.py experimentC.zarr --tiffs path/to/experimentC
# 1810 checks run, 0 failed, 0 advisories
```

### Dataset hygiene

Three things about the delivery are not specification problems, but they are what a reader
meets first.

- The phenotyping folder sits outside the folder holding the nine ISS cycle folders, and is
  labelled `c0`, as though phenotyping were ISS cycle 0.
- The phenotyping stain is named in the folder name and nowhere else. The recorded channel
  name is `GFP`; the folder name says the channel images a p65 antibody. A reader learns the
  antibody only by parsing a directory name, which is the practice D3 sets out to remove.
- The Micro-Manager acquisition prefix disagrees with the folder name for three of the nine
  ISS cycles, `10X-c5-SBS-5` against `10X_c5-SBS-5`.

## Dataset example: biohub_example

`biohub_example` is the public submission [](layout.md) cites for the merged-only case: one
stitched image and a stack of segmentations per well, no tiles and no raw data. It ships as
an OME-NGFF 0.5 HCS plate with Parquet, CSV and YAML sidecars, and it is the complement of
`experimentC` — where that one exercises `raw` and nothing else, this one exercises
`processed` and nothing else.

The delivery holds two stores. A three-well manifest declares the real thing, a stitched
image of 104650 by 105144 px per well, and carries no pixels. Beside it sits a 2048 by 2048
excerpt of well `A/1` that does carry pixels, positioned by a translation of 15600 µm, so it
is a genuine crop of the full well rather than a thumbnail. The store below is built from the
excerpt, which is the only part with data.

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

### The store

`scripts/build_biohub_zarr.py` writes it as one plate collection at stage `processed`. Two
corrections are applied on the way, and they are why this is a rewrite and not a relabelling:
the axes are squeezed and lowercased, and the labels are written at the image's pixel size
rather than the one they declare, for the reason in Q31.

```text
biohub_example.zarr/
├── zarr.json                    # collection; sp-ops:spec; edge cells → library
├── library                      # table: 4211 guides
├── feature_definitions          # table: 2935 features, no values anywhere (Q24)
└── plate1_processed/            # collection; plate; sp-ops:plate; sp-ops:stage "processed"
    ├── cells                    # table: 831587 cells, all three wells, plate level
    └── A/1/                     # collection; well; scene: the well frame
        ├── pheno/               # collection; sp-ops:modality "pheno"; acquisition pheno
        │   └── merged/          # collection; sp-ops:merged {"source": []}  ← Q19
        │       ├── image        # multiscale (c, y, x) float32, 6 channels, 5 levels
        │       ├── cell_seg     # multiscale (y, x) int32; labels.source → image
        │       ├── nuclear_seg  # ... and ten more compartments
        │       └── grid_overlay # multiscale (c, y, x) uint8; a rendering, not data
        └── iss/                 # collection; sp-ops:modality "iss"
            └── merged/          # collection; sp-ops:merged {"source": []}
                ├── iss_gene_image   # multiscale (c, y, x) uint8 RGBA
                └── iss_guide_image  # multiscale (c, y, x) uint8 RGBA
```

23 RFC-8 nodes, 124 arrays, three tables, 149 MB. Wells `A/2` and `A/3` are declared in the
plate's columns but carry no node, which [](layout.md#screen-and-plates) permits, because the
delivery has no pixels for them; their rows are in the plate-level `cells` table.

The well collection carries sixteen transforms, one per merged element, all the same
translation, and eleven `sjoin` edges at `status: "suggested"` for the compartment
membership nothing in the delivery records. See Q23.

```bash
python scripts/build_biohub_zarr.py path/to/biohub_example biohub_example.zarr
python scripts/check_sp_ops_zarr.py biohub_example.zarr --zarr path/to/biohub_example
# 435 checks run, 0 failed, 2 advisories
```

The two advisories are the empty `sp-ops:merged.source` of Q19. Advisories are checks this
exercise suggests the specification should require, not ones it does; the other one,
comparing a labels element's physical extent against its source image, is what catches Q31.

### What the two datasets disagree about

Several entries below are specific to one dataset, and reading them together is more useful
than reading either alone.

| Question | `experimentC` | `biohub_example` |
| --- | --- | --- |
| ISS base identity (Q1) | absent; dye names only | recorded: `DAPI`, `G`, `T`, `A`, `C` with wavelengths and exposures |
| barcode against cycles (Q11) | 20-base library, 9 cycles | 10-base library, 10 cycles; every row joins |
| library columns (Q12) | `barcode`, `sgRNA`, `gene_symbol` | exactly the four the specification names |
| instrument provenance (Q6, Q21) | in TIFF tags | in a YAML sidecar; neither has an sp-ops home |
| modality magnification (Q8) | both 10x, scale 1 | ISS 5x/0.15, phenotyping 20x/0.55 |
| tile layout (Q2) | measured from image overlap | tile ids in a table, the grid shipped as a bitmap |

The most useful line is the last but one. `experimentC` contradicts the assumption that the
two modalities differ in magnification; `biohub_example` confirms it, at a ratio of four. The
general case in [](design-decisions.md#d2-modality-is-split-at-the-well-and-tiles-and-merged-are-separate-children-of-a-modality)
is right, and Q8 is about its justification being stated as though it always holds.

### Dataset hygiene

- The `labels/` group declares its contents twice, in `ome.labels` and in a sibling `labels`
  key, listing twelve and thirteen names against fifteen groups on disk. The two ISS
  renderings appear in neither list, so the only ISS-derived rasters in the submission are
  the ones a reader following the metadata never sees.
- `cell_seg` reports three cell counts that cannot all describe the same thing: `n_cells`
  590472 attributed to plate statistics, `n_cells_linked` 267449 which is exactly the number
  of table rows for well `A/1`, and a `_legacy_statistics.n_cells` of 44734217.
- `nuclear_seg` is two rows shorter than the image in the manifest, 104648 against 104650, so
  the labels are not quite the same grid even before Q31.
- The channel named `mCherry` was imaged with mScarlet-I and the one named `GFP` with mEGFP,
  per the same metadata block that names them.

## Dataset example: experimentC_scallops

`experimentC_scallops` is the same screen as `experimentC`, the same well and the same two
fields of view, run through the [scallops](https://github.com/Genentech/scallops) pipeline.
It carries no raw tiles at all: what it holds is a stitch stage and an ops stage, so it is
the processed counterpart Q13 asked for, over pixels whose `raw` form is already written as
a conformant store. Where the other two datasets are a `raw` delivery and a `processed`
delivery from different screens, this one is the pipeline in between, and it is the only
dataset here that exercises `intermediate`.

| What | Value |
| --- | --- |
| wells | one, `A1` |
| fields of view | two, grid indices 0 and 1, renumbered from Micro-Manager sites 102 and 103 |
| ISS rounds | nine, cycle labels 1 to 5 and 7 to 10; the pipeline calls the axis `t` |
| ISS channels | five, named at stitch time: `DAPI`, `G`, `T`, `A`, `C` |
| phenotyping | one round, two channels: `DAPI`, `NFkB` |
| merged shape | `(1002, 1972)`, 11 px cropped from every edge of a `(1024, 1993.7)` mosaic |
| pixel size | 1.32 µm in both modalities, both stitched from the same position list |
| stitch stage | 10 illumination fields, 10 stitched well images, per-tile position and eval reports |
| ops stage | registered ISS stack, 39987 peaks, 15590 reads, 561240 base intensities |
| segmentation | five label arrays: 4706 nuclei, 4589 cells, 4525 cytosol, and two unfiltered |
| features | 141 cell, 49 nuclei, 38 cytosol columns, plus one 275-column fusion of all three |
| library | the same 5738 guides; not the reference the reads were decoded against (Q34) |

The pipeline's own vocabulary is the one
[D4](design-decisions.md#d4-there-is-no-fixation-timepoint-level) maps from, and this dataset
is the evidence for that mapping: `iss-registered-t0.zarr` declares axes `t, c, y, x` with
`t: [1, 2, 3, 4, 5, 7, 8, 9, 10]`, the cycle labels, and its transform folders are
`iss-transforms-t0/A1/t=2` to `t=10`. The store writes that axis as `round`.

### The store

`scripts/build_experimentC_scallops_zarr.py` writes it as one screen collection with two
plate collections, `intermediate` for the stitch stage and `processed` for the ops stage,
plus the screen-level `library`. There is no `raw` plate: those pixels are `experimentC`,
and the two stores share the plate id.

```text
experimentC_scallops.zarr/
├── zarr.json                     # collection; sp-ops:spec; edge reads → library (Q34)
├── library                       # table: 5738 guides
├── plate1_intermediate/          # collection; plate; sp-ops:stage "intermediate"
│   └── A/1/
│       ├── iss/
│       │   ├── tiles/            # collection; sp-ops:tiles
│       │   │   ├── layout        # shapes: 2 polygons, from the stage position list
│       │   │   ├── tile_features # table: 18 rows, one per tile and round
│       │   │   └── tile102/ tile103/   # empty: no per-tile product exists  ← Q33
│       │   ├── merged/           # collection; sp-ops:merged
│       │   │   ├── image         # multiscale (round, c, y, x); stitched, unregistered ← Q37
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
        │       ├── bases         # table: 561240 rows, one per read, round and base ← Q36
        │       ├── crosstalk     # table: the 4 by 4 base bleed matrix ← Q36
        │       └── peak_thresholds_labels, peak_thresholds_crosstalk   # 98 rows each ← Q36
        └── pheno/
            └── merged/
                ├── image         # multiscale (2, 1002, 1972)
                ├── nuclei, cells, cytosol              # labels (y, x) int32
                ├── nuclei_unfiltered, cells_unfiltered # the pre-filter pass ← Q42
                ├── nuclei_features, cells_features, cytosol_features
                ├── cell_barcodes  # table: 2798 cells with a called barcode
                └── merged_features    # table: 4706 by 275, all three compartments ← Q41
```

42 RFC-8 nodes, 112 declared node entries, 21 multiscales, 318 arrays, 14 tables, two shapes
and two points elements, 359 MB.

Three things in the store are derived rather than copied. The tile layout comes from
`stage_positions.parquet`, which is the position list Q2 says `experimentC` lacks, so the
polygons here are declared rather than measured. Both merged images carry a 14.52 µm
translation into the well frame for the stitcher's 11 px fuse crop, which no source metadata
records (Q39). And `tile_provenance` is written as the grid index plus one, because the
source numbers tiles from zero and zero is the labels background.

The phenotyping merged image is written into both plate collections, because nothing between
the stitch and the segmentation touched it. [D1](design-decisions.md#d1-a-plate-collection-is-one-physical-plate-at-one-stage)
lets a whole plate collection be referenced by path from another store, but there is no way
for one stage to say that a single element of it is another stage's element unchanged, so the
array is duplicated.

```bash
python scripts/build_experimentC_scallops_zarr.py path/to/experimentC_scallops \
    path/to/experimentC_raw experimentC_scallops.zarr
python scripts/check_sp_ops_zarr.py experimentC_scallops.zarr \
    --scallops path/to/experimentC_scallops
# 361 checks run, 4 failed, 1 advisories
```

This is the only one of the three stores that does not check clean, and both results are
findings rather than build defects. The four failures are the empty tile collections of Q33,
which the specification requires to exist and requires to hold an image. The advisory is
Q34: the reads-to-library edge the specification declares matches 2.4 percent of reads, and
5738 barcodes over the 4⁹ possible nine-base reads is 2.2 percent by chance.

### What this dataset settles

Four entries written against `experimentC` can be answered now that the same pixels have
been through a pipeline.

- Q1, base identity. The dataset confirms the second of the two proposed resolutions: base
  identity is a processing decision that appears in `processed` only. The raw store records
  `Cy3, A594, Cy5, Cy7`; the stitch step assigns `G, T, A, C` and the phenotyping stain
  becomes `NFkB`, the antibody target that `experimentC` left in a folder name. But the
  assignment survives only inside a free-text `scallops_command` string, so the dye-to-base
  mapping is still unrecoverable, and a permuted flag would make every barcode in the store
  wrong with nothing to detect it.
- Q2, the layout MUST. Satisfied here from `stage_positions.parquet`, and the store's
  polygons are declared, not measured. The gap Q2 identifies remains: nothing distinguishes
  this layout from `experimentC`'s reconstructed one.
- Q5, tile index against site id. Confirmed exactly as predicted. Scallops renumbered sites
  102 and 103 to grid indices 0 and 1, in the position reports, in the provenance raster and
  in the file names it wrote. The site ids survive only inside a `source` column holding the
  input path, so recovering them means parsing a file name. The store keeps both, `index`
  and a `site` field.
- Q13, the missing processed half. This is it. `peaks`, `reads`, `cells`, `cells_features`,
  `nuclei_features`, `merged` and `tile_features` all exist here, `sp-ops:rounds`,
  `sp-ops:registration` and `sp-ops:merged` are all written, and all three leaf node types
  are used. The central claim is still not demonstrated end to end, but for a different
  reason than Q13 gave: the pixels-to-perturbations chain is complete except for its last
  link, and that link is Q34.

### Dataset hygiene

- The stitcher scored a normalised cross correlation between 0.003 and 0.022 on the one
  overlapping pair, and kept the nominal stage offset, 1280 µm over 1.32 µm per px, exactly
  969.69697 px, in all ten acquisitions. The `experimentC` exercise measured 991 px from the same images at
  correlations of 0.945 to 0.954. The two disagree by 21.3 px, and they are not reconcilable:
  at 991 px the overlap is 3.2 percent, below the pipeline's own `min_overlap_fraction` of
  4 percent, so the pair would have been rejected. Whichever is right, the recorded
  `fraction` of 5.303 percent is computed from the offset the stitcher assumed.
- `segment.zarr` holds only a `labels/` group, and every label in it declares
  `image-label.source.image: "../../images/A1"`. That group does not exist in that store; the
  image is three directories away in `stitch/pheno/stitch/stitch.zarr`. See Q35.
- Two segmentations end in `.all`, `A1-nuclei.all` and `A1-cell.all`. RFC-8 ids permit `.`
  and OME-NGFF path names do not, so the names cannot be carried over. See Q42.
- The 4 by 4 base crosstalk matrix ships as an OME-NGFF multiscale with `y` and `x` space
  axes, so a viewer following the metadata will render a calibration matrix as a 4-pixel
  image.
- `spot-detect.zarr/images/A1-max` declares five axes, `sigma, t, c, y, x`, and gives `sigma`
  a `type` of `null`. See Q38.

## Dataset example: cpg0021_sample

`cpg0021_sample` is a two-well subset of the public
[cpg0021-periscope](https://github.com/broadinstitute/cellpainting-gallery) whole-genome
optical pooled screen, delivered as Nikon ND2 files straight off the microscope with one
guide table beside them. Like `experimentC` it carries no derived data, so it exercises the
`raw` stage and nothing else. Unlike `experimentC` its images arrive in a vendor format with
their acquisition metadata intact — stage coordinates, objective, exposure, filter block,
autofocus offset and a pixel-to-stage matrix on every image — which makes it the dataset that
says what a `raw` store is being asked to carry, and the one that can be checked against
itself.

| What | Value |
| --- | --- |
| plate | one, `CP186A`; the 6-well format is measured from the stage, not recorded |
| wells | two, delivered as `Well1` and `Well2`, written `A/1` and `A/2` |
| fields of view | 8 ISS and 40 phenotyping per well, of 320 and 1364 per well in the full acquisition, from the site numbering |
| ISS rounds | twelve, cycle labels 1 to 12, no gap |
| ISS channels | five: `DAPI`, `Cy3`, `A594`, `Cy5`, `Cy7` |
| phenotyping | one round, five channels: `DAPI`, `GFP`, `A594`, `Cy5`, `750` |
| tile shape | `(c, 1480, 1480)`, `uint16`, one z plane, one timepoint, both modalities |
| pixel size | ISS 1.2143 µm at 10x/0.45, phenotyping 0.6071 µm at 20x/0.75, ratio exactly 2 |
| tile overlap | 10 percent in both modalities, in both axes |
| library | 82678 rows over 20391 gene symbols and 80862 distinct guides, 2270 non-targeting |
| derived data | none: no reads, peaks, labels, or feature tables |

The two modalities really do differ in magnification here, by a factor of two, so this
dataset takes D2's and D7's side of Q8 rather than `experimentC`'s. It also has a nuclear
stain in both modalities, which `biohub_example` did not, so
[D7](design-decisions.md#d7-registration-anchors-are-declared-with-the-nuclear-channel-as-the-default)'s
default anchor is available for every one of the thirteen acquisitions.

### The store

`scripts/build_cpg0021_zarr.py` writes the dataset as one screen collection with one plate
collection at stage `raw` and the screen-level `library` table.

```text
cpg0021_sample.zarr/
├── zarr.json                       # collection; sp-ops:spec
├── library                         # table: 82678 rows, one per delivered guide row ← Q45
└── plate1_raw/                     # collection; plate CP186A; sp-ops:stage "raw"
    ├── A/1/                        # collection; well {row A, column 1} ← Q44; scene: 680 transforms
    │   ├── iss/                    # collection; sp-ops:modality "iss"
    │   │   └── tiles/              # collection; sp-ops:tiles
    │   │       ├── layout          # shapes: 8 polygons, measured, stage readout beside ← Q2, Q49
    │   │       ├── image_metadata  # table: 480 rows, one per acquired image ← Q6
    │   │       ├── tile0/          # collection; sp-ops:tile {"index": 0, "site": 0}
    │   │       │   ├── round0/     # collection; acquisition iss-c1; sp-ops:axis {round, 0, 1}
    │   │       │   │   ├── channel0     # multiscale (y, x); DAPI, role nuclear
    │   │       │   │   └── channel1 ... channel4   # Cy3, A594, Cy5, Cy7; role base
    │   │       │   └── round1/ ... round11/        # acquisitions iss-c2 to iss-c12
    │   │       └── tile1/ ... tile7/
    │   └── pheno/                  # collection; sp-ops:modality "pheno"; acquisition pheno
    │       └── tiles/              # one round only, so no round level
    │           ├── layout          # shapes: 40 polygons
    │           ├── image_metadata  # table: 200 rows
    │           └── tile0/ ... tile39/
    │               ├── channel0    # DAPI, role nuclear
    │               └── channel1 ... channel4       # GFP, A594, Cy5, 750; role stain
    └── A/2/                        # the same, eight and forty more fields of view
```

1669 RFC-8 nodes, 1360 channel multiscales, 4080 arrays over three pyramid levels, 1360
tile-to-well transforms, five tables, four shapes elements, 5.6 GB.

Four things about the store need stating, and each is a finding below.

The tile positions are measured, not declared, even though this delivery does ship a position
list. Every ND2 records the stage coordinates of its own field of view, and those coordinates
disagree with the images: normalised cross correlation of the nuclear overlap of every
adjacent pair puts the tiles up to 68 px from where the stage says, consistently, because the
recorded pixel size is 1.0 percent too large in ISS and 0.4 percent too large in
phenotyping. The store's `layout` holds the measured footprint and keeps the stage readout in
four columns beside it, because nothing in the specification distinguishes the two (Q2, Q49).
The solve used 9 and 8 of 12 candidate ISS pairs and 76 and 86 of 103 phenotyping pairs, at
residuals of 0.18 to 2.51 px.

The tile-to-well transform is an affine with a rotation, not a translation. The instrument's
`pixelToStageTransformationMatrix` has a negative determinant: it mirrors x. Taking the well
x axis against stage x absorbs the mirror and leaves a rotation of 0.053°, the camera mounting
angle, which every transform in the store carries. A writer that read the recorded matrix and
wrote a translation would place every tile mirrored.

The phenotyping transforms carry a scale of 1.00636 in well `A/1` and 1.00588 in `A/2` on top
of that rotation. That is registration step 3, the modality registration, done at the `raw`
stage because a raw store places both modalities in one `well` frame and there is no merged
image to do it between. The scale is measured from the nuclear channel over 24 overlapping
ISS-to-phenotyping tile pairs per well at correlations of 0.77 to 0.91, and it is not the
ratio of the recorded pixel sizes (Q48). `sp-ops:registration` is bound to a processed
multiscale, so the store cannot say any of this (Q50).

`image_metadata` is the provenance table Q6 proposed, written here to see whether it works. It
holds one row per acquired image — 480 per well for ISS, 200 for phenotyping — with the
objective, numerical aperture, magnification, camera, binning, exposure, filter block,
autofocus offset, stage coordinates, acquisition timestamp and recorded pixel size. Q6 puts it
at the plate level; the store splits it per modality under each `tiles` collection instead,
which [](features.md#merged-and-split-tables) permits and which lets the well and the modality
come from its position in the hierarchy rather than from columns. Its key is still
`(tile, round, channel)`, and `on` takes one column pair, so the edge the store declares joins
on `tile` alone. That is Q40 again, reached from the other end.

```bash
python scripts/build_cpg0021_zarr.py path/to/cpg0021_sample cpg0021_sample.zarr
python scripts/check_sp_ops_zarr.py cpg0021_sample.zarr \
    --nd2 path/to/cpg0021_sample/cpg0021-periscope/broad/images/*/images/CP186A
# 27036 checks run, 0 failed, 0 advisories
```

`--nd2` compares all 1360 raw channel arrays against the ND2 page each was written from. This
exercise also adds one advisory, `check_layout_against_scene`, which recomputes every tile's
footprint from the tile-to-well transforms in the well's `scene` and compares it against the
`layout` polygon for the same tile. It passes here because both come from the same solve.
Rewriting this store's ISS layout at the recorded stage positions, which is what a writer
following the metadata alone produces, leaves the transforms untouched and makes the advisory
report seven disagreements of up to 82 µm. Nothing in the specification requires the two to
agree, which is Q49.

### What this dataset settles

- Q6, instrument provenance. This is the dataset the entry was written about without having
  one to hand. Every fact it lists is here and is per image: exposure differing by a factor of
  four across the channels of one round, objective and numerical aperture differing between
  modalities, 2x2 binning, autofocus offsets from 7154 to 7224 in ISS against 9445 in
  phenotyping, per-image stage coordinates and filter blocks. The delivery records more still
  — the seven laser lines with their per-channel powers, the camera serial and temperature —
  which the store drops for want of a field. The plate-level table is the workable half of
  Q6's two options, and writing it exposes the granularity gap: one row per acquired image is
  a `(tile, round, channel)` granularity, and [](features.md)'s ladder is cell, tile, well,
  plate. Q36 already asked for two more rungs; this is a third.
- Q8, the modalities' magnification. Confirmed, at a ratio of two. D2's justification holds
  for this dataset: 8 ISS tiles against 40 phenotyping tiles per well, independent grids,
  independent stitching, and a modality registration that genuinely needs a scale. Q8 stands
  as written, about `experimentC` being the case the justification does not cover.
- Q10, the recorded pixel size against the measured geometry. Reproduced on a second dataset
  and on both modalities at once, at 1.0 percent for ISS and 0.4 percent for phenotyping.
  What is new is that the two differ, so the disagreement is not a single stage calibration:
  see Q48.
- Q11, read length against barcode length. Twelve cycles against 20-nucleotide guides. The
  first twelve bases resolve 80862 of the 82678 rows, which is every row the table can
  resolve at any length, so twelve cycles are sufficient and the prefix join Q11 proposes
  works. The store writes `barcode_prefix_12`. The remaining 1816 rows are Q45.
- Q16, one transform per channel array. 680 transforms per well, carrying 48 distinct tile
  positions between them: sixty copies of each ISS position, one per round and channel, and
  five of each phenotyping position. `experimentC` measured 94 transforms for one well of two
  fields of view; the multiplier is rounds times channels either way, so the cost per tile
  rose from 45 to 60 with the three extra cycles and the store as a whole is fourteen times
  the size for the same reason.

### Dataset hygiene

- 96 of the 272 images carry an acquisition timestamp outside any plausible window: every
  file of ISS cycle 6 and all 80 phenotyping files report a Julian day in the year 3189. Of
  the eleven acquisitions whose clocks are usable, four stamp all sixteen of their images with
  one identical timestamp, so a distinct per-image acquisition time exists for 112 of the 272
  images. The store writes the recorded value with a `timestamp_valid` column beside it.
- The cycle 2 directory is `10x_c2-SBS-2` and the other eleven are `10X_c<n>-SBS-<n>`.
- `Well1_Point1` and `Well2_Point2` encode the well twice and the row and column not at all.
  See Q44.
- Three of the five phenotyping channels are named by dye or filter rather than by what they
  stain, and one, `750`, by an excitation line. What any of them images is recorded nowhere.
  See Q51 and Q20.
- The library's `gene_symbol` and `gene_id` do not agree on identity: 52 symbols carry more
  than one `gene_id`, and 293 `gene_id`s carry more than one symbol. The 2270 non-targeting
  rows all carry `gene_id` -1.

## Requirements a dataset cannot meet

### Q1. `sp-ops:channels` requires a base identity the dataset does not record

Observation. The registry marks `sp-ops:channels` MUST on images, with `role` drawn from
`nuclear`, `base`, `stain`, `other`, and the running example names the four ISS base channels
`A`, `G`, `C`, `T`. The dataset records dye and filter names only, `Cy3`, `A594`, `Cy5`,
`Cy7`, and carries no dye-to-base mapping, neither in the images nor in the barcode table. The
store writes the recorded names with role `base`, so the specification's own read,
`iss.sel(round=0, c="DAPI")`, cannot address a base by its identity.

Proposed resolution. Either add an optional field beside `name` for the recorded dye or
filter, so a raw channel can be honest about what was measured and still be labelled once the
base assignment is known, or state that base identity is a processing decision that appears in
`processed` only. The second is closer to the rest of the specification: `raw` is what the
instrument produced.

### Q2. `sp-ops:tiles.layout` is a MUST with no metadata path to satisfy it

Observation. `sp-ops:tiles` MUST reference a `layout` shapes element with one polygon per
field of view in the well frame. The dataset ships no position list. The TIFF tags do embed a
Micro-Manager position list, but it is the full 3198-position plate list and only two of those
sites are present, so it is not a per-well layout. The store's `layout` had to be
reconstructed from image content.

Proposed resolution. Keep the MUST, it is the right requirement, but say what a writer does
when positions are absent: record the layout as measured, and record how it was obtained.
There is no field for the provenance of a layout, so a reader cannot tell a stage readout from
a cross correlation. That is the same gap as Q6.

### Q3. The plate identifier is not a field of the dataset

Observation. `sp-ops:plate` MUST carry the physical plate id, which is what ties a plate's
stages together. Here the id survives only inside an acquisition directory name embedded in
the TIFF tags. It is withheld on this page for the reason given in [](references.md).

Proposed resolution. None for the specification: the requirement is right and the gap is in
the delivery. Worth one sentence in [](layout.md) saying the plate id is expected from the
acquisition system or the submitter, and is not recoverable from pixel data.

### Q4. A single-well delivery cannot declare the plate geometry

Observation. A plate collection declares `rows` and `columns`. Only well `A1` is present, and
the only trace of the plate format is a substring of that same directory name. The store
declares one row and one column rather than invent the rest. [](layout.md#screen-and-plates)
guarantees that plate collections of one physical plate declare the same acquisitions, so that
a processed image can reference them without opening the raw plate. The same argument applies
to rows and columns, and a single-well subset cannot honour it.

Proposed resolution. Say whether `rows` and `columns` describe the physical plate or only the
wells present. If the plate, a subset store cannot fill them and needs a way to say so. If
only what is present, the guarantee above needs weakening.

### Q5. `sp-ops:tile.index` conflates a grid position with an acquisition site id

Observation. The registry says `index` matches the `tile` column of `layout`, but not what the
integer means. The two fields of view here are sites 102 and 103 of a 3198-position
acquisition. The store keeps 102 and 103, so the link to the source acquisition survives; a
writer that renumbers them 0 and 1, which the recommended names `tile0`, `tile1` invite, loses
that link with nothing recording the loss.

Proposed resolution. Fix `index` as the position in the modality's own tile grid, and add an
optional field for the acquisition's identifier of the field of view. Both are wanted: the
grid position orders the tiles, the site id joins back to the instrument and to pipelines
keyed on it.

### Q6. `raw` has nowhere to keep instrument provenance

Observation. D1 and D5 make `raw` the reprocessable record: written once, never changed, kept
as the instrument produced it. None of the twelve attribute keys holds what this dataset
carries per image. Exposure, which differs across channels by a factor of sixteen. Objective.
Camera binning. Acquisition timestamp, which places the phenotyping round one day before ISS
cycle 1 and the last cycle five days after it. Per-channel focus position, where the nuclear
channel sits 0.7 µm from the base channels of the same round. Stage coordinates. Filter block.
RFC-8 `acquisition` holds an id and a name. All of it was dropped when the store was written.

Proposed resolution. This is the largest gap the exercise found: a `raw` store that cannot say
how its pixels were acquired is not reprocessable in the sense D1 claims. Two options. An
`sp-ops:instrument` key on the acquisition, the round, or the channel, which keeps the facts
next to the pixels they describe. Or a table at the plate level with one row per acquired
image, which scales better, is a table like any other, and needs no new key beyond an edge.

### Q7. A screen-level table that annotates nothing has no defined relationships

Observation. `sp-ops:relationships` is MUST for every table that describes an element and
SHOULD otherwise. In a raw-only store `library` describes no element in the store: there are
no reads to join it to. The store writes an empty edge list on the screen collection.

Proposed resolution. Say that an empty edge list is the correct value for a collection with no
joinable pairs, or drop the SHOULD for collections that contain none.

### Q19. `sp-ops:merged.source` is a MUST that a merged-only submission cannot fill

Observation. The registry marks `sp-ops:merged` MUST on a merged collection, with a `source`
holding references to the tiles it was stitched from. `biohub_example` discarded its tiles;
the store writes `"source": []`. [](layout.md) explicitly blesses this shape of delivery, "no
tiles and no raw data, and is still a usable store", so the specification permits a store and
then requires a field that store cannot fill. The tiles demonstrably existed: the `cells`
table carries 2249 distinct tile ids and a grid overlay renders their boundaries.

Proposed resolution. Let `source` hold tile identifiers rather than references, so a
merged-only store can record which tiles contributed without them being present. This
dataset has exactly those identifiers. Making the key optional would lose them instead.

### Q20. `role` cannot describe a label-free, reconstructed, or predicted channel

Observation. Four of six channels in `biohub_example` are not stains: `Phase2D` and `Focus3D`
are label-free brightfield reconstructions, and `nuclei_prediction` and `membrane_prediction`
are virtual stains from a model. The four roles are `nuclear`, `base`, `stain`, `other`, so
the store writes `other` three times and calls the one nuclear-looking channel `nuclear` —
except it is a prediction, so [](design-decisions.md#d7-registration-anchors-are-declared-with-the-nuclear-channel-as-the-default)'s
default anchor would register on model output. The phenotyping round has no nuclear stain at
all; the ISS round does, a Hoechst DNA stain, so the two modalities would anchor on
different kinds of thing.

The source metadata is richer than the specification here: a `channel_type` of `labelfree`,
`fluorescence`, or `predicted`, and a `biological_annotation` with marker, marker type,
target, fluorophore, and excitation and emission wavelengths.

Proposed resolution. Separate what a channel is for, the current role, from how it was
produced: measured, reconstructed, or predicted. Let a channel carry its marker and
fluorophore. Then say in D7 whether a predicted channel may serve as a registration anchor.

### Q21. There is no home for the provenance of a derived element

Observation. Every label group in `biohub_example` carries how it was made: the method,
`cellpose-sam`, a version, the stitching rule, and the parameters, a diameter of 100, a flow
threshold of 0.7, an IoU threshold of 0.1, a tile size of 4096 and an overlap of 512. It also
names the channel it was computed from. RFC-8 `labels.source` references an image node, not a
channel, so all twelve labels point at the same six-channel image and which channel each came
from is unrecoverable from the store. The method and parameters have no key at all, and the
store drops them.

Proposed resolution. Let `labels.source` reference a channel of an image, not only the image.
Add a key for the method and parameters that produced a derived element, labels, points and
shapes alike. This is Q6 on the processed side: without it a processed store can be read but
not audited or regenerated.

### Q22. A cell table has no label column, and the specification's edge needs one

Observation. The edge between a labels element and its table is
`{"on": {"left": "value", "right": "label"}}`. `cell_data.parquet` has no `label` column. The
label value is the last underscore-separated component of `cell_uid`, a string like
`Biohub_OPS0001_A1_2027_19418950`. That is the third merged-table encoding of
[](features.md#merged-and-split-tables), "a hierarchical unique id column ... next to plain
`well`, `modality`, `site`, `label` columns" — except the plain columns are absent, so the id
has to be parsed. The store derives `label`, `well`, `modality` and `site` and keeps
`cell_uid` as the index. The derivation is sound: every one of the 251 cells that fall inside
the delivered excerpt has its derived label present in `cell_seg`.

Proposed resolution. Say in [](features.md#merged-and-split-tables) that the plain columns
accompany the hierarchical id rather than being an alternative to it. An id whose components
must be parsed to join is the naming grammar
[D3](design-decisions.md#d3-names-are-opaque-and-attributes-carry-the-meaning) rejects, moved
out of a path and into a column.

### Q23. Compartment membership can be unrecorded, and then only a spatial join recovers it

Observation. Twelve compartments were segmented: the cell, the nucleus, and ten organelle
classes. [](design-decisions.md#d8-derived-data-lives-at-the-tile-or-merged-collection-it-was-computed-on)
says a compartment nesting inside a cell carries a `cell_label` column on its feature table
instead of nesting in the hierarchy. There are no feature tables here, and no label element
carries a membership column, so nothing links a nucleolus to its cell. The numbering spaces
are disjoint too: in the excerpt `cell_seg` runs 20064998 to 20066368 and `nuclear_seg` runs
282305 to 321319, so the values cannot simply be matched. The store therefore writes eleven
`sjoin` edges on the predicate `within` at `status: "suggested"`.

Proposed resolution. The mechanism works and needs no change; this is what `suggested` is
for, and it is worth adding to [](joinable-components.md) as the worked example, because a
submission that ships labels without feature tables is the common case. What is worth adding
is a SHOULD: a compartment label SHOULD either share its parent's numbering or carry a
membership column, so that membership is data rather than a suggestion.

### Q32. RFC-5 has no transform for the registration this pipeline computed

Observation. [](extension.md) states plainly that no coordinate transformation type is
added, because "RFC-5 `affine`, `translation`, `scale`, and `byDimension` cover alignment and
stitching". They do not cover this dataset. Each of the eight non-reference ISS rounds was
registered by elastix in two stages, recorded in `iss-transforms-t0/A1/t=<n>`: an
`AffineTransform` of six parameters, then a `RecursiveBSplineTransform` of 1020 parameters on
a 30 by 17 control grid, cubic, composed with the affine. None of RFC-5's four types is a
free-form deformation.

Discarding the B-spline would be tolerable for seven of the eight rounds, where its largest
control displacement is 0.53 to 1.23 px. It is not tolerable for cycle 10, where the largest
is 45.2 µm, 34.3 px, and the 99th percentile is 31.4 px. So the store cannot record how its
own pixels were produced, and cannot approximate it either: the registered array is the only
evidence the transform ever existed, and the transform is not invertible from it.

Proposed resolution. Add a transform type for a displacement field or a B-spline control
grid, which is what registration of fixed cells across rounds actually produces, and which
RFC-5's own scope note does not exclude. Failing that, add a way to reference an opaque
external transform with its parameters, so a `processed` store can at least say which file
warped it. Without one of the two, [](layout.md#registration)'s claim that each of the three
registration steps "is a coordinate transformation between RFC-5 coordinate systems" is false
for step 2 in the general case.

### Q33. A tile collection MUST hold an image, and a stitch stage has no per-tile product

Observation. `sp-ops:tiles` MUST reference a `layout`, and the [](layout.md) level table
makes the tile level "MUST have at least one under `tiles`". Scallops stitches straight from
the raw TIFFs: between the raw tiles and the stitched well image it writes illumination
fields, which are one per well and round rather than one per tile, and nothing else. So the
stitch stage has a tile layout, a per-tile position report and a per-tile eval report, and no
per-tile array anywhere. The store writes `tiles/` with `layout` and `tile_features` and two
tile collections that hold nothing, which is the four failures the exercise reports.

Proposed resolution. Let a `tiles` collection carry its `layout` and its tile-granularity
tables with no tile collections under it, which is what a stage that stitches without
materialising tiles needs. The alternative, moving `layout` up to the modality, splits the
tile level's metadata across two collections for no gain.

### Q34. The reference a read was decoded against is not in the store

Observation. Q11 worked out that nine cycles are enough for this library, because all 5738
barcodes are unique in their first nine bases, and proposed a prefix join. The reads are
indeed nine bases. The join still fails: 2.4 percent of the 15590 reads match a library
nine-base prefix, against 2.2 percent expected by chance from 5738 barcodes over 4⁹ possible
reads. So it is not that the join needs a prefix length, it is that these reads were never
decoded against this library.

What they were decoded against is not in the delivery. `barcode_match` is true for 6733
reads over 1932 distinct barcodes, of which 183 are library prefixes; `closest_match`, the
error-corrected call, lies inside the set of barcodes observed in this well for 79 percent of
rows. Whatever whitelist the pipeline used, the store has nowhere to name it, and nowhere to
record that the `library` it does carry is not it. The store writes the edge the
specification declares and the checker reports it as an advisory.

Proposed resolution. The reference a base call was decoded against is provenance of the
`reads` element, and belongs wherever Q21 puts the provenance of a derived element. It is not
optional detail: a store that cannot say which barcode list produced its calls cannot be
audited, and this one silently ships a `library` edge that a reader would take on trust. Q26
is the other half, since an edge that matched 2.4 percent of its rows should be able to say
so.

### Q35. `labels.source` can resolve outside the store

Observation. `segment.zarr` contains a `labels/` group and nothing else. All five label
arrays in it declare `image-label.source.image: "../../images/A1"`, which would be
`segment.zarr/images/A1`; no such group exists. The image they were computed from is in
`stitch/pheno/stitch/stitch.zarr/images/A1`. So the one link the specification leans on to
tie a labels element to its image, and which
[D8](design-decisions.md#d8-derived-data-lives-at-the-tile-or-merged-collection-it-was-computed-on)
cites as the reason derived data sits next to the image it came from, is dangling in the
delivery. The store repoints all five at `pheno/merged/image` by id.

Proposed resolution. One sentence: `labels.source` MUST resolve, and MUST use an explicit
external path when the image is not in the same store. The requirement is right and the gap
is in the delivery, but a reader has no way to tell a resolvable reference from this one
without trying it, and a writer following a pipeline's output verbatim reproduces the break.

### Q36. Run-level diagnostics and calibration have no granularity

Observation. Three elements in the ops stage describe the run rather than anything in space.
`A1-peak-labels.parquet` and `A1-peak-crosstalk.parquet` are 98-row threshold sweeps, one row
per candidate threshold with precision, recall, f1, accuracy and a confusion matrix. The
crosstalk matrix is 4 by 4, base against base. A fourth, `bases`, is 561240 rows of one
intensity per read, round and base, which is real measurement but at a granularity
[](features.md) does not list either.

The granularity ladder is cell, tile, well, plate, each with an element to point at.
`sp-ops:relationships` is MUST for a table that describes an element and SHOULD otherwise, and
for a threshold sweep there is no element and no meaningful edge. Q7 raised the same shape of
problem for `library` in a raw-only store; that had an answer, an empty edge list. This is
worse, because these tables do belong to something, the run of a pipeline step, and the
specification has no name for it.

Proposed resolution. Add a granularity for the parameters and diagnostics of a processing
step, joined to nothing, and say an empty edge list is correct for it. `bases` is a different
case and simpler: it is a table at read granularity, which is a real granularity this
specification should list next to cell, since `reads` is already a first-class element.

### Q44. The `well` attribute is a MUST and the delivery records only an ordinal

Observation. Every well collection MUST carry the RFC-8 `well` attribute, which is a row and
a column. `cpg0021_sample` records neither. The only trace of well identity is the `Well1`
and `Well2` prefix of each ND2 file name, and the ND2 metadata itself has no well field at
all: not in `text_info`, not in the custom tag table, not in the experiment loop.

The plate format is recoverable, and only from the stage coordinates the images carry. Matching
the two wells' fields of view by index puts their stage centres 39107.6 µm apart in x with a
standard deviation of 0.1 µm, which is the 39.12 mm pitch of a 6-well plate, so the two wells
are adjacent columns of one row. Which row, and which two columns, is not recoverable from
anything in the delivery. The store writes `A/1` and `A/2` and declares two rows and three
columns, and both the labels and the format are inferences.

Proposed resolution. This is Q3 and Q4 one level down, and it needs the same sentence: the
well's row and column are expected from the acquisition system or the submitter, and are not
recoverable from pixel data. Worth adding that a writer that assigns them SHOULD say so,
because an ordinal in a file name is the common case and `A/1` asserts more than it knows.
Q4's question, whether `rows` and `columns` describe the physical plate or only the wells
present, is sharper here than in `experimentC`: the format is measurable and the labels are
not, so a store can honestly declare the shape of the plate while guessing where on it the
data sits.

### Q45. `library` has no unique row key, and the declared read join is not n:1

Observation. [](joinable-components.md) gives `library` one row per guide and declares the
edge from `reads` at `cardinality: "n:1"`. This library has 82678 rows and 80862 distinct
guide sequences. The 2270 non-targeting rows are 454 distinct sequences, each listed five
times, identical in every column. So there is no column, and no combination of the delivered
columns, that identifies a row: the table cannot be indexed by barcode, and the store indexes
it by row ordinal instead.

The consequence for the declared edge is not cosmetic. All 80408 targeting rows are distinct,
so a read matching a targeting guide joins to one row; a read matching a non-targeting guide
joins to five. The join is n:1 over 80408 rows and n:5 over 2270, and `cardinality` has no way
to say that, so a reader that trusts `n:1` and joins will silently multiply every control read
by five. Controls are the rows an analyst weights most heavily.

Proposed resolution. Say that the element on the `1` side of an `n:1` edge MUST have a unique
key in the joined column, and that a writer whose source does not MUST deduplicate or say
which column is the key. Q26's coverage field is the neighbouring gap and does not cover this
one: coverage says how much of a table an edge reaches, and this is about the same key
reaching several rows.

## Assumptions the datasets contradict

### Q8. The two modalities were imaged at the same magnification

Observation. Four places assume otherwise. [](layout.md) explains sixteen phenotyping tiles
against four ISS tiles by the modalities being imaged at different magnifications. D2 rests
its split of `tiles` and `merged` per modality on their different tile counts and footprints.
[](layout.md#registration) and D7 describe modality registration as an affine that includes a
scale, because the magnifications differ.

In this dataset both modalities are 10x, 1.32 µm per pixel, 1024 by 1024, drawn from the same
position grid at the same two sites with the same stage coordinates. The measured nuclear
offset between the modalities at one tile is about 4 px in `y` and 0 in `x`: a pure
translation at scale 1.

Nothing is violated, the wording is "usually" and "may". But D2's justification is void here,
and the arrangement it explicitly rejected, one tile grid shared by both modalities, is the one
this dataset has. The store writes a byte-identical `layout` under both modalities as a
result.

Proposed resolution. Keep the layout, it is the general case, but give D2 a justification that
does not depend on the magnifications differing, and say what a writer does when the two
modalities share a grid. Sharing one `layout` by reference is the obvious economy, and there is
currently no way to express it.

### Q9. Tile and merged images do not differ by two orders of magnitude

Observation. D2 argues that a tile image and a merged image differ by two orders of magnitude
in size, and so need different chunking, sharding, and pyramid depth. This well has two tiles.
Its merged image would be about 1028 by 2015 px, roughly twice a tile.

Proposed resolution. Keep the separation of `tiles` and `merged`, for the reason D8 gives: a
reader opening one of them gets everything computed on it. The size argument is not
load-bearing and should not carry the decision alone.

### Q10. The recorded pixel size and the measured geometry disagree by 2.2 percent

Observation. Every image records a pixel size of 1.32 µm. The stage spacing between the two
sites is 1280 µm, which predicts a 969.7 px displacement; the measured displacement is 991 px,
identical across all ten acquisitions. Either the true pixel size is 1.2916 µm or the stage
scale is off by 2.2 percent, and the dataset does not say which. A coordinate system carries
one pixel size with no way to mark it nominal or calibrated, and a raw store has no place for a
stitching residual: [](features.md#tile-and-well-features) puts `well_features` on a `wells`
shapes element on the plate collection, and a raw store has neither.

The store keeps the recorded 1.32 µm and uses the measured displacement, so its well-frame
micrometres deliberately do not equal stage micrometres.

Proposed resolution. Say which of the two a coordinate system carries. If both are wanted, the
calibrated value belongs on the image and the nominal one with the instrument provenance of
Q6. Separately, allow the quality-control tables of [](features.md) at the raw stage, so a
residual has somewhere to go before `processed` exists.

### Q11. Nine ISS rounds against twenty-nucleotide barcodes breaks the declared library join

Observation. [](joinable-components.md) declares the edge from `iss/merged/reads` to `library`
as a key join on `barcode` against `barcode`, cardinality n:1. The library holds 5738
twenty-nucleotide barcodes, and nine rounds were imaged, so a read is at most nine bases. The
join as declared cannot match unless one side is truncated, and nothing in the specification
records the read length or a prefix length. All 5738 barcodes are unique in their first nine
bases, so nine rounds are sufficient here; the store adds a nine-base prefix column so that
the join is at least expressible.

Proposed resolution. The read length is a property of the ISS modality and belongs in its
metadata. With it a reader knows to compare a prefix, and the edge can say so, for instance an
`on` that names a prefix length. The derived column is a workaround: it puts a pipeline
parameter in a table, and it breaks the moment a screen is extended with more rounds.

### Q12. The library columns the specification names are not the ones the dataset has

Observation. [](joinable-components.md) gives the library one row per guide with `barcode`,
`perturbation_id`, `role`, `control_type`. The dataset has `barcode`, `sgRNA`, `gene_symbol`.
The store derives `role` and `control_type` from the gene symbol being `non-targeting`, 100
rows of 5738, and sets `perturbation_id` to the gene symbol, which is not a stable
perturbation id: 950 symbols, up to twelve guides each. The page does call its column names
illustrative, so the mismatch is soft, but the one table it says every screen has cannot be
written as specified.

Proposed resolution. Keep the names illustrative and say which facts about a guide a reader
needs, rather than which columns: an identifier that joins to a read, a perturbation identity,
and whether the guide is a control. A screen that has only a gene symbol can then say so.

### Q13. The dataset exercises the raw half of the specification only

Observation. There is no `intermediate` and no `processed` stage, and of the elements
[](joinable-components.md) names, only `library` exists: no `peaks`, `reads`, `cells`,
`cells_features`, `nuclei_features`, `merged`, `tile_features`, or `wells`. Each of those is a
MAY, so the store is conformant. It also carries no relationship edge anywhere, and
`sp-ops:rounds`, `sp-ops:registration`, `sp-ops:merged`, and two of the three leaf node types
are never written.

Proposed resolution. None for the specification. It is a gap in the evidence: the central
claim, that this layout joins pixels to perturbations, is untested until a processed
counterpart to this dataset is written. That is the next thing to build.

### Q24. Feature definitions can exist without a feature matrix, and three vocabularies do not meet

Observation. [](features.md#cell-features) puts feature names in the `var` of the table
holding their values. `biohub_example` has 2935 feature definitions, with type, compartment,
channel, unit and software, and no per-cell feature values at all: `cell_data.parquet` holds
identity and position only. The definitions have no `var` to live in, so the store writes them
as a screen-level table, which the specification has no slot for.

Worse, the three feature vocabularies in the delivery are mutually disjoint. The plate's 2935
definitions, the atlas's 35246 definitions, and the 66 column names of the atlas matrix share
no identifier: none of the 66 appears in either definitions file, and none of the 35246
appears among the 2935.

Proposed resolution. Say where a feature dictionary lives when it is shared across tables,
rather than only inside one table's `var`, and give it an edge to the tables it describes.
Then a checker can report the disjointness above, which today nothing can see.

### Q25. A denormalised column disagrees with the table it was copied from

Observation. `cell_data` carries both `barcode` and `perturbation_id`. The barcode join to
the library is perfect: all 831587 rows match, 10-base barcodes against 10 imaged cycles. The
copied `perturbation_id` disagrees with what the library gives for the same barcode in 80659
rows, 9.7 percent, over 335 barcodes, and 32 of its values do not appear in the library at
all.

The cause is vocabulary drift, not corruption. The table holds retired HGNC symbols where the
library holds current ones — `AARS` against `AARS1`, `HIST1H2BK` against `H2BC12`, `METTL7A`
against `TMT1A`, `C12orf45` against `NOPCHAP1` — and it collapses 211 control groups into a
single `NTC`. The atlas agrees with the table rather than the library: 1052 perturbation ids
on each side, 1021 shared, 31 different.

So following the edge and reading the column give different answers, and nothing says which
is authoritative. This is the strongest evidence the exercise found for
[D9](design-decisions.md#d9-relationships-are-an-edge-list-on-the-lowest-collection-that-contains-both-ends):
the edge was right and the copy had rotted.

Proposed resolution. State that a column duplicating a value reachable over an edge is a
cache and the edge is authoritative, and make disagreement something `check_relationships`
reports. A `status` of `computed` currently asserts that a join column exists, not that it
still agrees with the join.

### Q26. Coverage, not cardinality, is what an edge needs to declare

Observation. The `cells` table is a subset of the labels it describes. In the delivered
excerpt 251 of 859 segmented cells have a row, because only cells with a confident barcode
are listed. The edge is written `cardinality: "1:1"`, which is true of the rows present and
badly misleading about what is absent. Two thirds of the table's rows describe wells `A/2`
and `A/3`, whose pixels are not in this delivery, so those rows have no label element to
point at from any store built out of it.

Proposed resolution. The query sketch already promises `check_relationships` will report
"cardinality, coverage, and dangling keys". Let an edge declare coverage as well as
cardinality, so a reader knows before loading that a table covers a third of its labels
rather than all of them.

### Q27. The root is one screen, and an atlas sits above it

Observation. `atlas/aggregated_data.h5ad` is 1052 perturbations by 66 features, with
`observation_unit` of `perturbation_id`, aggregated over 77 screens, carrying Leiden
clusterings at fifteen resolutions and UMAP and PHATE embeddings. The granularities in
[](features.md) are cell, tile, well and plate; there is no perturbation granularity. And
[D1](design-decisions.md#d1-a-plate-collection-is-one-physical-plate-at-one-stage) fixes the
root as one screen, so there is no level above a screen to hold something aggregated over 77
of them. The store omits the atlas: putting it inside this screen would assert that it
belongs to this screen, which is false.

Proposed resolution. Add perturbation as a granularity in [](features.md), joined by an edge
to `library` rather than to a spatial element. Then say whether a collection above the screen
is in scope. A cross-screen atlas is the object an analyst is most likely to open first, so
the answer matters more than its position at the end of this list suggests.

### Q37. Stacked rounds cannot declare that they are not registered

Observation. [D6](design-decisions.md#d6-axes-are-a-subset-of-round-t-c-z-y-x-in-that-order-singleton-axes-are-omitted-and-rounds-are-always-stacked)
says rounds are always stacked, and `sp-ops:rounds` MUST record the acquisition behind every
slice. The stitch stage produces nine well images, one per cycle, each stitched on its own
but all on the same grid, so they stack and the store stacks them. The result is
`(9, 5, 1002, 1972)` with nine `sp-ops:rounds` entries and five `sp-ops:channels`, which is
indistinguishable from the registered array in `plate1_processed`: same shape, same axes,
same channels, same coordinate system, same pixel size.

The difference between them is the whole ops stage. `sp-ops:registration` is the only key
that would say so and it is a SHOULD, so its absence means "not stated" rather than "not
registered", and a reader that opens the intermediate array gets rounds misaligned by up to
34 px with nothing warning it. [](layout.md) does say channels are "not yet aligned" in
`raw`, but the raw stage is the one case where the layout itself carries the answer, because
channels are separate elements there. Once anything is stacked the layout stops helping.

Proposed resolution. Make `sp-ops:registration` MUST on any image with a `round` axis, and
let it state that rounds are unregistered as well as naming an anchor and a reference. The
same argument applies to channels within a round.

### Q38. `sigma` is a real axis the fixed order has no room for

Observation. D6 fixes the axes as a subset of `round, t, c, z, y, x` in that order, and
explicitly rejects a writer-chosen order until "a use case shows a measurable gain". The spot
detection step writes `(sigma, t, c, y, x)`, giving `sigma`, the scale-space parameter of a
multi-scale blob detector, a `type` of `null` because OME-NGFF has no type for it. It is
singleton in this run, which D6 would omit, but `sigma` is not incidental: it is a column on
`peaks` and on `reads` and part of the key that joins them, so the pipeline genuinely varies
it and genuinely needs it per detection.

So this is the use case D6 asked for, and it argues for something narrower than a
writer-chosen order: a place for an axis the specification does not know about. The store
drops the intermediate `A1-max` and `A1-std` arrays and keeps `sigma` as a column, which is
the right call here and only because the axis was singleton.

Proposed resolution. Allow writer-defined axes after the known ones, ordered but not named
by this specification, so a store can keep a scale-space or parameter-sweep stack without
inventing a private convention. Then say a writer SHOULD flatten such an axis into columns
when it is singleton, which is what happened here.

### Q39. A merged image is not already in the well frame

Observation. [](layout.md#registration) ends "Merged images are already in the `well` frame",
and the running example gives tile images a translation and merged images none. This
stitcher crops `fuse_crop_width`, 11 px, from every edge of the fused mosaic: the two tiles
span 1024 by 1993.7 px and every array in the dataset is 1002 by 1972. So the merged image's
first pixel is at well pixel (11, 11), not (0, 0), and every scallops group declares
`translation: [0, 0, 0]`.

A reader that believes either the specification's sentence or the source metadata places the
merged image, its five label arrays and its 15590 reads 11 px from where they are, which is
larger than the round registration residual the ops stage worked to remove. The store derives
the offset from `fuse_crop_width` and the array shapes and writes 14.52 µm on both merged
images.

Proposed resolution. Delete the sentence. A merged image's transform into the well frame is
whatever stitching produced, commonly not the identity, and saying otherwise invites exactly
the metadata this dataset ships. Q10 is the neighbouring case: there the well frame and the
stage frame disagree on scale, here on origin.

### Q40. `read` is a position hash, and the peak join needs three columns

Observation. [](joinable-components.md) gives `peaks` the columns `x, y, read` and says
"`read` is the join key between a peak and its decoded read, following the scallops
convention". Two things are wrong with that in the dataset it names. `peaks` has no `read`
column: it has `y, x, sigma, peak`, and the join to `reads` is on `(y, x, sigma)`, which does
match all 15590 reads exactly. And `read` is not an identifier: it is `y * 1972 + x`, the
flattened pixel index in the merged image. Re-crop or re-stitch the well and every read is
renumbered; put two wells in one table and the keys collide.

The composite key is the more serious of the two, because `on` is a single `{left, right}`
column pair and there is no way to write it. The store writes the edge on `y` alone at
`status: "suggested"`, which is the only expressible thing and is wrong.

Proposed resolution. Let `on` take a list of column pairs. Separately, either require a read
identifier that does not encode geometry, or say in [](joinable-components.md) that `read` is
scoped to one image and drop the claim that `peaks` carries it.

### Q41. A compartment's table is split by column group, not by source

Observation. [](features.md#merged-and-split-tables) contemplates splitting a table by the
element it describes, one per tile or merged collection or modality, and requires a reader to
handle both split and merged forms. This pipeline splits differently: each compartment's
table arrives as two files, `A1.parquet` with the measurements and `A1-objects.parquet` with
the bounding box, centre and area, keyed on the same label and neither one complete on its
own. For cytosol they disagree: 4525 labels in the array, 4525 rows of geometry, 4508 rows of
measurements, so 17 objects have a bounding box and no features.

Above them sits `merge/A1.parquet`, 4706 rows by 275 columns, fusing all three compartments
and the barcode calls with `Cells_`, `Cytoplasm_` and `Nuclei_` column prefixes. That is a
fourth encoding of a merged table, and features.md lists three. It is keyed on the nucleus,
so every cell-level and cytosol-level value is left-joined and absent where the compartment
is. The store writes the three split tables, joined and with a `has_features` flag, and keeps
the fusion beside them.

Proposed resolution. Say that a split is by described element, and that one element's table
is one table, so a writer that ships measurements and geometry separately is expected to join
them. Then pick the default merged encoding features.md leaves open, and note the prefix
form as a fourth in use, since it is what a pipeline hands an analyst.

### Q46. A raw store can place one field of view in twelve places

Observation. `sp-ops:tiles.layout` holds one polygon per field of view, so the tile footprint
is a property of the tile.
[D5](design-decisions.md#d5-raw-channels-are-separate-images-with-their-own-coordinate-systems)
makes every raw channel of every round its own multiscale with its own coordinate system, so
the tile-to-well transform is per channel array and can differ per round. The two disagree
about granularity, and this dataset has the metadata to make the disagreement matter.

Every ND2 records its own stage coordinates, and for the same field of view they move across
the twelve ISS rounds: 50 µm in x and 20 µm in y, which is 41 px and 17 px. The images do not.
Registering the nuclear channel of well `A/1` tile 0 against cycle 1 across all twelve rounds
puts every round within 2.5 px of the reference, at correlations of 0.977 to 0.993, while the
stage readout for the same twelve images spans 41 px. The recorded per-round position is
noise; the field of view did not move.

So a writer that placed each round's channel arrays at their own recorded stage positions —
which is the obvious reading of D5, and the only reading under which the per-array transform
earns its existence — would produce a store misregistered by up to 41 px, with every MUST
satisfied, `layout` untouched, and nothing anywhere to detect it. A writer that used one
footprint per tile gets it right, and the specification does not say which to do.

Proposed resolution. Say that a tile's footprint in the well frame is a property of the tile,
that the transforms of its channel arrays differ from it only by measured channel and round
alignment, and that a writer MUST NOT pass an instrument's per-image position readout through
as that alignment. Then Q16's coordinate system on the tile collection stops being only an
economy: it is the place the tile footprint belongs, and it makes this class of error
unwritable rather than merely discouraged.

### Q47. The two modalities cover different parts of the well

Observation. Nothing requires a well's modalities to cover the same ground, and here they do
not. In well `A/1` the eight ISS fields of view cover 23.5 mm² and the forty phenotyping
fields cover 28.2 mm²; they intersect over 17.5 mm², which is 74 percent of the ISS footprint
and 62 percent of the phenotyping footprint. In `A/2` it is 63 and 58 percent. Each well has
about 10.8 mm² of phenotyped area with no ISS coverage at all.

[](layout.md) says the ISS and phenotyping grids "may differ in tile count, size, and
overlap", which this satisfies, and D2 rests on exactly that. But the central claim of the
specification is that the layout joins pixels to perturbations, and 38 to 42 percent of the
phenotyped area in this delivery can never receive a read. A reader has no way to know that
before loading: the two `layout` elements are the only record, they are per modality, and
nothing compares them.

Proposed resolution. Nothing changes in the layout. What is missing is that the intersection
of the modalities' footprints is a fact about a well that a reader needs before deciding what
a store is good for, and it is computable from what is already written. Make it a validator
check and say in [](layout.md) that a partial overlap is permitted and expected in a subset
delivery. This is Q26's argument at the level of pixels rather than rows: partial coverage is
something a reader needs declared, not left to compute.

### Q48. The modality registration scale is not the ratio of the recorded pixel sizes

Observation. D7 says the modality registration is "an affine that includes a scale" because
the magnifications differ, and [](layout.md#registration) has both merged images keep their
native pixel size. This dataset agrees and then shows the scale cannot be composed from the
two native pixel sizes. ISS records 1.2142857 µm at 10x and phenotyping 0.6071429 µm at 20x,
a ratio of exactly 2. Solving each modality's tile grid against its own stage spacing puts the
ISS pixel 1.0 percent below its recorded size and the phenotyping pixel 0.4 percent below, so
the measured ratio is 1.988. Which of the pixel size and the stage scale is at fault is Q10's
question and does not matter here, because only the ratio enters the modality transform.

The residual is what that costs. Registering the phenotyping nuclear channel onto the ISS
nuclear channel over 24 overlapping tile pairs per well, a translation alone leaves up to
30.4 µm across the well; adding a scale of 1.00636 leaves 5.3 µm. So most of the disagreement
is scale, and its size is close to the 0.6 percent by which the two modalities' pixel-size
measurements differ.

So a writer that registers the modalities by composing their declared pixel sizes is wrong by
30 µm, or 25 ISS pixels, at the edge of the well, and Q10's gap is what lets it happen: a
coordinate system carries one pixel size with no way to mark it nominal or calibrated.

Proposed resolution. Q10's, applied to two modalities at once: a coordinate system says
whether its pixel size is nominal or calibrated. Separately, D7 should say the modality
transform is measured, not derived from the objectives, because the objectives are what a
writer will reach for and they are in exact ratio when the optics are not.

## Inconsistencies inside the specification

### Q14. The well is the only name that spans two path segments

Observation. Every level is one Zarr path segment except the well, named `A/1`. Writing it
forces an intermediate group at the row which is neither an RFC-8 node nor an sp-ops one; the
store leaves it an untyped Zarr group. D3 argues that `=` is unavailable in names because
OME-NGFF path names are restricted to alphanumerics, `-`, and `_`, and by that same rule `A/1`
is not a legal single name either.

Proposed resolution. Either make row and column two levels of the hierarchy, matching the
RFC-8 `plate` attribute that lists rows and columns separately, or name the well `A1` and
leave the row and column in the `well` attribute where they already are. The second is the
smaller change and loses nothing, because names carry no meaning.

### Q15. Two pages disagree on where the stitching transform lives

Observation. [](layout.md#modalities-tiles-and-merged-images) says tile images map into the
well frame by the stitching transform stored on the modality collection. The complete example
in [](extension.md) puts `scene`, and the `well` coordinate system, on the well collection,
with transforms for both modalities. Only the well collection works: the well frame is shared
by both modalities, so the well is the lowest collection containing both endpoints, which is
the rule [](joinable-components.md#storage) states for edges and
[](layout.md#registration) states for transformations. The store follows [](extension.md).

Proposed resolution. Fix the sentence in [](layout.md).

### Q16. Placing raw tiles in the well frame costs one transform per channel array

Observation. D5 makes every raw channel its own multiscale with its own coordinate system, and
no coordinate system is defined for a raw tile as a whole. Mapping this one well into the well
frame therefore took 94 transforms, 90 for ISS and 4 for phenotyping, carrying just two
distinct translations between them. At the scale of the running example it is 260 per well,
780 for the three wells.

Proposed resolution. Define a coordinate system on the tile collection. Stitching is then one
transform per tile into the well frame, and channel alignment one transform per channel into
the tile frame, which is exactly the first and third registration steps of
[](layout.md#registration). The composition is what a reader wants, and the count stops
multiplying.

### Q17. `sp-ops:channels` in array order says nothing in `raw`

Observation. The key is defined as one entry per channel in array order. A raw channel array
has axes `(y, x)` and no `c` axis, so every raw channel node carries a list of one and the
ordering clause is vacuous. `sp-ops:axis` on the same node then repeats an index that the
node's position in `nodes` already gives.

Proposed resolution. State that in `raw` the list holds exactly one entry, and either drop
`index` from `sp-ops:axis` on a channel node or say what it adds. The key earns its full
definition in `processed`, where channels are stacked.

### Q18. The inside of a multiscale is never shown

Observation. The specification shows a multiscale node's attributes but never its levels.
RFC-8 requires a singlescale node to carry `coordinateTransformations` in its attributes,
while [](extension.md) says a node with a `path` and no `nodes` is stored in its own
`zarr.json`, which a Zarr array cannot do for an RFC-8 `nodes` list. The store inlines the
singlescale nodes in the multiscale group's `zarr.json`, as RFC-8's own example does, with a
`scale` at level 0 and a `sequence` of `scale` and `translation` below it, for the half-pixel
shift a 2x2 mean introduces.

Related: RFC-5 as published names a coordinate system with `name`, while RFC-8 and every
example here use `id`. The store follows this specification.

Proposed resolution. Show one complete multiscale, levels included, in [](extension.md), and
note the `name` against `id` divergence in assumption A3, which currently records RFC-5 as
released with no caveat.

### Q28. `sp-ops:channels` is specified on `multiscale`, so a single-resolution image has no home for it

Observation. The registry binds `sp-ops:channels` to `multiscale`, and RFC-8 also defines
`singlescale`. The three RGBA overlays in `biohub_example` have exactly one resolution level.
The store writes them as one-level multiscales so their channels have the specified home,
which dresses a singlescale as a multiscale for the sake of one attribute.

Proposed resolution. Bind the key to both node types, or say that a single-resolution image
is written as a one-level multiscale and `singlescale` appears only inside one.

### Q29. The fixed axis order can require rewriting pixels, not metadata

Observation. [D6](design-decisions.md#d6-axes-are-a-subset-of-round-t-c-z-y-x-in-that-order-singleton-axes-are-omitted-and-rounds-are-always-stacked)
fixes the axis order as a subset of `round, t, c, z, y, x`. The source's images are
`(1, 6, 1, 2048, 2048)` with uppercase `T, C, Z, Y, X` and singleton `T` and `Z`: squeezing
and lowercasing those is a metadata edit. The three overlays are stored channel-last,
`(y, x, rgba)`, and conforming means transposing the array.

Proposed resolution. Keep the rule, it earns its place. Say in D6 that conforming may require
rewriting pixels rather than metadata, so that a conversion is budgeted as a rewrite.

### Q30. No transform in the specification has the dimensionality of its input

Observation. [](layout.md#registration) notes that a tile-to-well transform "is a
`byDimension` transform in practice, because `round` and `c` pass through unchanged; the
example shows the spatial part only". The complete example in [](extension.md) then maps
`./pheno/merged/image`, a `(c, y, x)` image, into the two-axis `well` frame with a two by
three affine. No `byDimension` transform is ever written out. The store follows the examples
and writes two-value translations from `(c, y, x)` images into `well`, so its transforms are
underdetermined the same way.

Proposed resolution. Write one `byDimension` transform in full in [](extension.md). It is the
form every real store needs and the only one the specification never shows. This is Q18 one
level up: the parts a writer cannot guess are the parts that are abbreviated.

### Q31. Nothing requires a labels element to agree with the image it came from

Observation. All twelve label groups in `biohub_example` declare 0.325 µm per pixel in the
store and 0.65 in the source, on an array of identical shape to the image, which declares
0.325. Both cannot be right, and the source says which is wrong: an `op_units_correction`
note on the image records that it was corrected from 0.65 to 0.325 and the label groups were
not. The correction is confirmed twice from the pixels. The tail of every `cell_uid` in the
excerpt is a `cell_seg` value at 1:1, and `membrane_prediction` is enriched 2.6-fold on
`cell_seg` boundaries at 1:1 — 1.665 against 0.651 in the interiors — while under a
two-fold reading the enrichment vanishes, 0.685 against 0.669. So the store corrects the
labels and a naive conversion would have produced a store misregistered by a factor of two,
silently, with every MUST satisfied.

Proposed resolution. Require a labels element and its `labels.source` image to agree on
physical extent, and make it a validator check. `scripts/check_sp_ops_zarr.py` implements it
as an advisory: restoring the source's 0.65 on one label makes it report `extent (1331.2,
1331.2) um disagrees with its source image (665.6, 665.6) um`. Nothing in the specification
requires that today, which is how the source shipped.

### Q42. Two segmentations of one compartment have no expression

Observation. The pipeline ships each of two compartments twice: `A1-nuclei` with 4706 labels
and `A1-nuclei.all` with 4823, `A1-cell` with 4589 and `A1-cell.all` with 4706. The `.all`
pass is the segmentation before filtering, and the filtered set is a strict subset in both
cases. Nothing in this specification distinguishes them. They are two labels elements of the
same compartment at the same granularity on the same grid, and a reader meeting `nuclei` and
`nuclei_unfiltered` side by side has only the names to go on, which
[D3](design-decisions.md#d3-names-are-opaque-and-attributes-carry-the-meaning) says carry no
meaning.

The names also cannot be carried over. RFC-8 ids match `[a-zA-Z0-9-_.]+` and permit the `.`,
while D3 notes OME-NGFF path names are restricted to alphanumerics, `-` and `_`, so
`A1-nuclei.all` is a legal id and an illegal path. The store renames them, which is a rename
D3's own rule forces and which nothing records.

Proposed resolution. Let a labels element name its compartment and, optionally, the
processing variant it represents, so that "nuclei, unfiltered" is metadata rather than a
naming convention. This is the same shape as Q21: what a derived element is, as against what
it is called. The `.` divergence between RFC-8 ids and OME-NGFF path names is worth one line
in [](extension.md), because a writer will meet it the first time it copies a pipeline's
names.

### Q43. Compartment membership rides on a numbering convention

Observation. [](features.md) requires that a compartment other than the cell record its
parent as a column, `cell_label` in the examples, joined to the `cells` labels by an edge.
None of the three feature tables here has such a column. Membership is implicit instead:
the pipeline numbers a nucleus, its cell and its cytosol with the same integer, so nucleus
1743 belongs to cell 1743. It is exact where both exist and silent where they do not: 117 of
the 4706 nuclei have no cell.

Nothing in the delivery states the convention, and it is not the only possible one. The store
derives `cell_label` from it and writes 0 where no cell exists, which is a guess that happens
to be checkable, since the labels arrays agree. Q23 is the same requirement failing the other
way, where membership is genuinely absent and only a spatial join recovers it; this is the
case where it is recoverable but only if a reader knows something the store does not say.

Proposed resolution. Keep the column requirement. Add that a writer deriving membership from
shared label numbering MUST materialise it as a column, and that the edge is what a reader
follows, never the numbering. [D9](design-decisions.md#d9-relationships-are-an-edge-list-on-the-lowest-collection-that-contains-both-ends)
already makes that argument for a different reason in Q25: the edge is authoritative and a
convention is not.

### Q49. Nothing requires `layout` and the tile-to-well transforms to agree

Observation. A tile's position in the well frame is written twice: as a polygon in the
modality's `layout`, and as the transform from the tile's own coordinate system into `well` in
the containing collection's `scene`. The specification requires both and relates them nowhere.
A store can declare a layout measured from the images and transforms taken from the stage
readout, or the reverse, and satisfy every MUST while placing the same field of view in two
places.

`cpg0021_sample` is where the two differ enough to see. Rewriting its ISS layout at the
recorded stage positions, which is what a writer following the metadata alone produces, leaves
the transforms untouched and moves seven of the eight polygons, by up to 82 µm — 68 px, and
about half a tile's overlap strip. `scripts/check_sp_ops_zarr.py` implements the comparison as
an advisory, `check_layout_against_scene`, which recomputes each tile's footprint from its
transforms and reports the disagreement.

Proposed resolution. Require that a tile's `layout` polygon and its tile-to-well transforms
place it in the same position, and make it a validator check. This is Q31 for geometry rather
than for pixel size: two records of one fact, no requirement that they agree, and a plausible
conversion that breaks it silently.

### Q50. `sp-ops:registration` has no home in `raw`, where the modality registration first happens

Observation. `sp-ops:registration` is specified on a processed multiscale, and
[](layout.md#registration) puts the modality registration between the two merged images. A
raw store has neither. It does have the `well` coordinate system, shared by both modalities,
which [](extension.md)'s complete example puts on the well collection with transforms for
both — so the moment a raw store writes those transforms it has registered the modalities,
and it has no attribute in which to say so.

The store therefore carries a measured scale of 1.00636 and a translation on all 200
phenotyping transforms of well `A/1`, derived from 24 tile pairs at correlations of 0.77 to
0.91, and records neither the anchor channel it used, the reference modality, nor that any
registration was performed. A reader cannot tell this store from one whose phenotyping tiles
were placed by their stage coordinates, which would be 30 µm out. Q37 makes the same argument
one stage later, for rounds stacked but unregistered.

Proposed resolution. Bind `sp-ops:registration` to any node that declares a transform into a
frame it shares with another element, not only to a processed multiscale, and let a well
collection carry one for the modality registration. Then a raw store can say which channel
anchored it and what the transform was measured from, which is the same thing Q21 asks for
derived elements and Q6 for raw pixels.

### Q51. Channel names are not unique within a well, and channels are addressed by name

Observation. [](layout.md#reading-the-store-with-spatialdata) reads a channel as
`iss.sel(round=0, c="DAPI")`, and `sp-ops:channels` is declared authoritative over array
position, so the name is the handle. In this dataset the names are not unique within a well.
ISS records `DAPI, Cy3, A594, Cy5, Cy7` and phenotyping records `DAPI, GFP, A594, Cy5, 750`:
`A594` and `Cy5` name a sequencing base in one modality and an antibody or dye stain in the
other, on the same well, at the same stage. `DAPI` is shared too, and there at least it means
the same thing.

`role` does not disambiguate them, because it is what the channel is for and not what it is:
`A594` is `base` under `iss` and `stain` under `pheno`, so a reader that selects by name
across the well gets two different measurements and a reader that selects by name and role
has to know the modality already. This is the collision Q1 and Q20 make possible rather than
a new requirement being broken — dye names are all the dataset has — but it is the case that
shows why: once base identity and marker identity are absent, the only names left are
instrument settings, and instrument settings repeat.

Proposed resolution. Say that `sp-ops:channels` names are unique within a modality, not
within a well, and that a channel is addressed by modality and name together. Then Q1's
optional dye field and Q20's marker field become the thing that makes two `A594` channels
distinguishable, which is the strongest argument for either.

## What the datasets confirm

Several decisions held up under the exercise, which is worth recording alongside the rest.

- D2 and D7, the modalities differ in magnification. `biohub_example` images ISS at 5x/0.15
  and phenotyping at 20x/0.55, a ratio of four, and `cpg0021_sample` images ISS at 10x/0.45
  and phenotyping at 20x/0.75, a ratio of two, with 8 and 40 fields of view per well. So the
  modality registration really is an affine with a scale and the two grids really are
  independent. Two of the three raw deliveries confirm it; Q8 is about the justification being
  written as though it always holds, not about the layout being wrong. Q48 is the refinement:
  the scale is real and is not the ratio of the declared pixel sizes.
- D3, names are opaque, at the level of the well. `cpg0021_sample` delivers its wells as
  `Well1` and `Well2` and no row or column anywhere, so every level of the hierarchy had to
  be named from something other than the delivery's own strings. The two things the store
  could not invent, the well labels and the plate format, are the two the reader is told
  about in Q44 rather than left to infer from a path.
- D5, raw channels are separate images with their own coordinate systems, and D7's default
  anchor. `cpg0021_sample` has a nuclear channel in all thirteen of its acquisitions, so
  every round and both modalities anchor on the same kind of thing, which is the case
  `biohub_example` could not provide in Q20. What it also shows is that the per-channel
  coordinate system is the mechanism by which a plausible writer misregisters a store, which
  is Q46.
- D4, there is no fixation timepoint level. `experimentC_scallops` is the dataset D4 argues
  from, and it holds up: `iss-registered-t0.zarr` declares a `t` axis whose values are the
  cycle labels 1 to 10 without 6, its transform folders are `t=2` to `t=10`, and its `bases`
  table carries a `t` column that is the cycle. Every one of them is this specification's
  `round`, and nothing in the dataset uses `t` for elapsed time. Mapping the axis to `round`
  cost nothing and removed the ambiguity D4 predicts.
- D3, names are opaque. The missing ISS cycle 6 in `experimentC` needed no name: the store
  writes `round5` with `sp-ops:axis` value 7 and the acquisition it came from, and nothing
  had to parse a string. The counter-example in Q22 is a store that did encode a join key
  into a string, and it has to be parsed back out.
- D5 and D7, raw channels are separate and the anchor is declared. In `experimentC` the
  nuclear channel drifts by up to 11 px in `y` and 17 px in `x` between the first and last
  ISS round, so rounds are genuinely unregistered in `raw`. The base channels share almost no
  structure with the nuclear channel, phase-correlation peaks of 0.02 to 0.04, so within-round
  alignment cannot be measured through the nuclear anchor from those images alone. That is the
  case D7 makes for declaring the anchor rather than inferring it.
- D6, singleton axes are omitted. Both datasets carry them: `experimentC` has one z plane per
  channel, `biohub_example` ships `(1, 6, 1, 2048, 2048)` with singleton `T` and `Z`. Neither
  says anything the squeezed form does not.
- D8, compartments are not fixed and are not nested. `biohub_example` segments twelve
  compartments, ten of them organelle classes inside the cell, and the flat arrangement takes
  them without strain. Nesting them under `cells` would have failed on the first nucleolus.
- D9, relationships are an edge list. Q25 is the case for it: in `biohub_example` the edge to
  the library is exact over all 831587 rows while the column copied from it has drifted on
  9.7 percent of them. A reader that follows edges gets the right answer and a reader that
  trusts the copy does not.
