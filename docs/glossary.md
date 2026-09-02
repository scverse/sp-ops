# Glossary

This page defines the domain terms and file format terms that the sp-ops specification uses. Each definition is short and, where it helps, names the object of the running example from the [design record](design-decisions.md#running-example). The assay acronyms used below are optical pooled screening (OPS), in situ sequencing (ISS), sequencing by synthesis (SBS), and field of view (FOV). The format acronyms are high-content screening (HCS), Open Microscopy Environment (OME), Next-Generation File Format (NGFF), and request for comments (RFC).

:::{admonition} Status
:class: note
Definitions carry one of three labels, matching the status categories of the [overview page](overview.md#every-statement-is-normative-existing-behaviour-or-a-proposal). "Existing behaviour" describes released software or standards, namely OME-NGFF 0.5, spatialdata v0.8.0, and the ngio table specifications. "This specification" marks a term that sp-ops defines. "(proposed)" marks a term that depends on unreleased work. That work is RFC-8 collections (status D1), RFC-5 coordinate transformations (status S4), the hierarchical SpatialData branch, or the element relationships prototypes. Facts taken from the Chan Zuckerberg Initiative (CZI) OPS data standard v0.1.0, which its authors mark as Draft, carry the label "(OPS data standard)". Requirements use MUST, SHOULD, and MAY in the sense of RFC 2119.
:::

## The running example supplies the names

Definitions below refer to these objects. All names follow the design record; the `t` values are folder labels from the scallops layout, not measured timepoints.

| Object | Running example name | Status |
| --- | --- | --- |
| Plate store | `ops_plate.zarr` | illustrative |
| Well | `A/1` | real (audit); scallops well `A1` |
| Tile | `f0` | illustrative |
| Tiles per well | `f0`, `f1`, `f2`, `f3` | illustrative |
| Pyramid levels per tile | 3 | illustrative |
| Fixation timepoint | `t2` | folder label (scallops) |
| ISS cycle image | `A/1/f0/t2/iss/r1` | this specification |
| Phenotypic image | `A/1/f0/t2/pheno` | this specification |
| Label images | `A/1/f0/t2/nuclear_seg`, `A/1/f0/t2/cell_seg` | real names (audit) |
| Registered frame | `A/1/f0/t2` | this specification |
| Cell feature table | `A/1/cells` | this specification |
| Perturbation library | `library` | this specification; columns from the OPS data standard |
| Stitched image (`stitched` profile) | `A/1/0`, one `merged` acquisition per well | real name (audit); see the [stitched profile example](design-decisions.md#stitched-profile-example) |

## Plate hierarchy terms run from plate to channel

```{glossary}
plate
  A plate is the top of the HCS hierarchy in OME-NGFF 0.5 (existing behaviour). Its `plate` metadata lists `rows`, `columns`, `wells`, and `acquisitions`; the running example plate is `ops_plate` with row `A` and columns `1`, `2`, and `3`.

well
  A well is one position on the plate, addressed by a row name and a column name, so `A/1` is row `A`, column `1`. In OME-NGFF 0.5 the well group lists its images under `well.images`, each with a `path` (existing behaviour). The integer `acquisition` key is required only when the plate has more than one acquisition.

field of view (FOV)
tile
  A field of view (FOV), called a tile in this specification, is one stage position in one well imaged across every acquisition. The running example tiles are `f0` to `f3` in each well (illustrative), and the `tiles` shapes element records their layout.

tiles
  `tiles` is the shapes element in each well with one rectangle per tile, indexed by the tile number that `sp-ops:tile` carries (this specification). The well collection references it through `sp-ops:tileLayout` (proposed).

acquisition
  An acquisition is one pass of the microscope over the plate that produces one image per tile (this specification). OME-NGFF 0.5 lists acquisitions on the plate with an integer `id`, a `name`, and a `maximumfieldcount`; this specification names them `iss-t<t>-r<r>`, `pheno-t<t>`, or `merged-t<t>`. Its `kind` in `sp-ops:acquisitions` is `iss`, `pheno`, or `merged`. A `merged` acquisition is one stitched image per well assembled after registration from the ISS cycles and the phenotypic round of one `t`, with `r` null; a writer MUST NOT use it when the raw acquisitions are stored ([D2](design-decisions.md#d2-plates-and-wells-stay-valid-ome-ngff-05-the-rfc-8-view-is-a-sidecar)).

timepoint (t)
  A fixation timepoint `t` is one population of fixed cells, so images from different `t` values cannot be aligned to each other. The example values are folder labels from the scallops layout (`t=2` to `t=10`), and the design record warns that their meaning is unconfirmed.

cycle
round
  A cycle, also called a round, is one ISS acquisition that reads one position of the barcode. Cycles are indexed `r`; the scallops files `A1-1.ome.tiff` to `A1-10.ome.tiff` give the running example its cycle set, in which cycle `6` is absent.

channel (c)
  A channel `c` is one wavelength recorded in one acquisition. When the channels of one acquisition share a pixel grid they form the `c` axis of a `(c, y, x)` image; when they do not, each channel is its own `(1, y, x)` element until resampled ([D4](design-decisions.md#d4-timepoints-and-cycles-are-separate-elements-only-aligned-channels-are-stacked)). `sp-ops:channels` gives each channel a `name`, a `role`, and for base channels a `base` (this specification).

profile
  A profile is the value of `sp-ops:spec.profile` and says how a well was imaged (this specification). A writer MUST use `tiled` when a well has more than one tile and `stitched` when each acquisition yields one image per well; the audited Biohub store is `stitched`, with one `merged` acquisition per well (see the [stitched profile example](design-decisions.md#stitched-profile-example)).

`images` table
  `images` is the per-well ngio condition table with one row per acquisition image element, raw or resampled (this specification). It annotates `footprints` and records `tile`, `acquisition`, `kind`, `t`, `r`, and `c` per row, so it is the tabular mirror of the JSON metadata ([D4](design-decisions.md#d4-timepoints-and-cycles-are-separate-elements-only-aligned-channels-are-stacked)).

flattened name
  A flattened name is the hierarchical element name with every `/` below the well replaced by `-` (this specification). `A/1/f0/t2/iss/r2` becomes the OME-NGFF 0.5 image path `f0-t2-iss-r2` and the spatialdata v0.8.0 element name `A-1-f0-t2-iss-r2`, and the replacement is reversible ([D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080)).

derived image
  A derived image is an image computed from acquisition images, such as the spot images `spots/max` and `spots/std` or a resampled cycle under `reg/` (this specification). Derived images are not acquisitions and are not `well.images` entries.
```

## Assay terms link images to perturbations

```{glossary}
optical pooled screening (OPS)
  Optical pooled screening (OPS) is a pooled clustered regularly interspaced short palindromic repeats (CRISPR) screen read out by microscopy. The perturbation in each cell is decoded from a barcode read by ISS, and the phenotype is measured by imaging the same fixed cells.

in situ sequencing (ISS)
  In situ sequencing (ISS) reads the guide barcode directly in fixed cells, one position per cycle. The author's draft calls these acquisitions ISS rounds or SBS rounds; each cycle images the nuclear stain 4′,6-diamidino-2-phenylindole (DAPI) and up to four base channels.

sequencing by synthesis (SBS)
  Sequencing by synthesis (SBS) is the chemistry behind the ISS cycles. The author's draft uses "SBS rounds" and "ISS rounds" as two names for the same acquisitions.

DAPI
  DAPI (4′,6-diamidino-2-phenylindole) is the nuclear stain of the running example. It is imaged in every ISS cycle and in the phenotypic round, so it is the anchor channel for registration. A depositor with another nuclear stain keeps that stain's name and gives it the role `nuclear`.

anchor channel
  The anchor channel is the channel whose `sp-ops:channels` role is `nuclear`, DAPI in the running example (this specification). Registration estimates each affine from the anchor channel of an image to the anchor channel of the reference image.

base call
  A base call is one nucleotide read at one spot in one cycle. The scallops file `reads/bases/A1.parquet` holds the calls with their locations; this specification stores them as the `bases` points element of each (tile, `t`), with a `read` column that joins to `reads`.

read
  A read is the sequence assembled from the base calls of one spot across cycles. The scallops file `reads/reads/A1.parquet` holds one row per read with its `sequence`; this specification stores it as the per-well `reads` table, identified by the uint64 `read` column.

spot detection
  Spot detection finds the fluorescent spots that carry barcodes in the ISS cycles. The scallops `spot-detect.zarr` holds `max` and `std` images and a `peaks` parquet; this specification stores them as `spots/max`, `spots/std`, and `spots/peaks` in each (tile, `t`).

barcode
  A barcode is the sequence that ISS reads to identify one guide. It is the primary key of `perturbation_library.csv`, one row per single guide RNA (sgRNA), and it is unique within an aggregation (OPS data standard).

guide (sgRNA)
  A guide, or single guide RNA (sgRNA), is the CRISPR reagent that produces one perturbation in a cell. Several guides can target one gene, so each guide has its own barcode but shares a `perturbation_id` with the others.

`perturbation_id`
  `perturbation_id` is the submitter-defined join key that all sgRNAs targeting the same gene share (OPS data standard). It appears in `library`, in `cells.obs`, and in the OPS `cell_data.parquet`; real examples are `AARS1`, `ADSS2`, and `GET3`.
```

## Cell readout terms describe one segmented cell

```{glossary}
`cell_uid`
  `cell_uid` is the globally unique identifier of one cell in the OPS `cell_data.parquet` (OPS data standard). This specification stores it in `cells.obs` and recommends the form `<row><col>_<tile>_t<t>_<label>`, for example `A1_f0_t2_812`.

segmentation labels
  A label image assigns an integer label value to every pixel, so that all pixels of one object share one value. The running example has `nuclear_seg` and `cell_seg` as int32 label images. In the 0.5 layout they are stored under the image they were computed from, at `<image>/labels/<name>`; in the hierarchical view they are named as siblings of that image, for example `A/1/f0/t2/cell_seg`, or `A/1/cell_seg` in the audited `stitched` store ([D10](design-decisions.md#d10-element-names-are-the-on-disk-paths-and-a-hyphen-flattens-them-for-v080) rule 6).

bounding box
  A bounding box is the axis-aligned rectangle that encloses one object. The scallops `-objects.parquet` files hold cell bounding boxes; this specification stores them as the `cell_bbox` shapes element, whose index equals the label value.

CellProfiler features
  CellProfiler features are per-object measurements, such as an area per compartment (`cell_AreaShape_Area` is an illustrative name), produced by the CellProfiler software. The scallops layout writes them per compartment (`cell`, `cytosol`, `nuclei`); this specification stores them in the `cells` feature table with `compartment` in `var`.

foreign key
  A foreign key is a column whose values identify rows of another table, so the two tables can be merged. `perturbation_id` in `cells` is a foreign key into `library`, and `read` in `bases` is a foreign key into `reads`.

spatial join
  A spatial join matches rows of two elements by a geometric predicate instead of by a key. This specification records spatial joins with the predicates `within`, `intersects`, `contains`, and `dwithin`, evaluated in a named coordinate system.

element relationship
  An element relationship (proposed) is one edge in `sp-ops:relationships` that records a key join or a spatial join between two elements. The edge schema follows the Padua `spatialdata_elements_graph` and Venice `element_relationships` prototypes, neither of which is released.
```

## Geometry terms describe alignment between images

```{glossary}
reference image
  The reference image of one (tile, `t`) is the acquisition image that maps into the registered frame by a pure scale (this specification). It is the acquisition whose `sp-ops:acquisitions` entry has `anchor: true`, by default the ISS cycle with the lowest `r`. `sp-ops:registration.reference` MAY override it for one tile.

registered frame
  The registered frame is the coordinate system shared by every element of one (tile, `t`), named `A/1/f0/t2` in the running example and `A/1/t2` in the `stitched` profile, where the tile level is omitted (this specification). Pixel alignment holds only inside it. The well frame `A/1` and the plate frame `plate` place tiles and wells without aligning cells across timepoints.

intrinsic coordinate system
  The intrinsic coordinate system of an image is its pixel grid scaled to physical units by the multiscale `scale` (RFC-5, proposed). The sidecar names it `intrinsic`. OME-NGFF 0.5 images declare no coordinate system, so a reader synthesises it from the image `axes` and `scale`.

registration
  Registration estimates the transformation that aligns one image onto another. In this specification every acquisition image at one (tile, `t`) is registered to the reference image through the anchor channel. The result is an affine into the frame `A/1/f0/t2`.

resampling
  Resampling writes image pixels onto a new grid after registration, so that several images share one pixel grid. `spatialdata.rasterize` performs it into a named coordinate system with an explicit box and resolution (existing behaviour).

resampled product
  A resampled product is an image written onto the common grid of a registered frame after resampling (this specification, MAY). It lives under `reg/`, for example `A/1/f0/t2/reg/iss/r2` or the stacked `reg/iss_stack`, carries an identity to the frame, and never replaces the raw acquisition image ([D6](design-decisions.md#d6-resampling-uses-the-largest-contained-box-by-default)).

stitching
  Stitching places the tiles of one well next to each other in the well frame. In this specification it is one translation per registered frame whose value comes from the tile's `tiles` row. Pixels are not merged, and how the translation is estimated is out of scope.

common area
  The common area is the region of the registered frame over which resampled images are defined. The `contained` rule takes the intersection of the image footprints, and the `containing` rule takes their union. The author's draft calls these the largest contained and the smallest containing bounding box.

footprints
  `footprints` is the shapes element in each well with one axis-aligned rectangle per acquisition image element, indexed by `image_id` (this specification). The `images` and `fov_features` tables annotate it, and the common area is computed from it.

scene
  A scene (proposed) is the RFC-5 group above a set of images that share a spatial relationship; it holds their coordinate systems and transformations. This specification writes a scene on each `t` collection, on each well, and on the plate in the sidecar ([D5](design-decisions.md#d5-cycles-are-registered-to-the-dapi-channel-of-the-first-iss-cycle-at-each-timepoint)). The plate scene defines the OPTIONAL coordinate system `plate` and one `translation` per well, from the well frame `A-1` to `plate`; each `input` is a cross-document RFC-8 `Reference` and MUST carry `id` and `path`, because the well frame is defined in the well document.

coordinate system
  A coordinate system is a named set of axes in which positions are expressed. RFC-5 (proposed) defines it as a JSON object with a `name` and an `axes` array; spatialdata v0.8.0 already names a coordinate system on every element (existing behaviour). This specification names its frames `A/1/f0/t2`, `A/1`, and `plate`.

coordinate transformation
  A coordinate transformation maps points from an input coordinate system to an output coordinate system, in the forward direction (RFC-5, proposed). spatialdata v0.8.0 provides `Identity`, `MapAxis`, `Translation`, `Scale`, `Affine`, and `Sequence` and stores them on elements (existing behaviour). The sidecar (proposed) writes the RFC-5 types `identity`, `translation`, `scale`, `affine`, and `byDimension`.
```

## Table terms follow the ngio vocabulary

```{glossary}
ROI table
  A region of interest (ROI) table is the ngio table type whose rows are regions given as number columns, `x_micrometer`, `y_micrometer`, `z_micrometer`, `len_x_micrometer`, `len_y_micrometer`, and `len_z_micrometer`, with default index `FieldIndex` (existing behaviour). This specification stores the same geometry as the `tiles` shapes element and MAY derive an ROI table from it.

masking ROI table
  A masking ROI table is the ngio table type whose rows are regions of interest (ROIs) tied to labels in a label image (existing behaviour). Each row corresponds to one label. The running example stores the same geometry as the `cell_bbox` shapes element and does not use this type.

feature table
  A feature table is the ngio table type with one row per object and one column per measured feature (existing behaviour). This specification uses it for `cells`, `fov_features`, and `well_features`. For the last two, the annotated region is a shapes element instead of a label image.

condition table
  A condition table is the ngio table type that records experimental conditions or metadata about images or experiments (existing behaviour). This specification uses it for `images`, one row per acquisition image, and for `library`, one row per barcode, the row unit of `perturbation_library.csv` (its `granularity` value is `perturbation`, see [D8](design-decisions.md#d8-table-types-use-the-ngio-vocabulary-under-one-namespaced-dictionary)).

generic table
  A generic table is the ngio fallback table type, "not tied to any specific domain or use case" (existing behaviour). This specification uses it for `reads`, and a validator MUST warn on it ([D8](design-decisions.md#d8-table-types-use-the-ngio-vocabulary-under-one-namespaced-dictionary)).

granularity
  Granularity is the row unit of a table, recorded in `uns["sp-ops"]["granularity"]` and in `sp-ops:table.granularity` (this specification). Allowed values are `cell`, `image`, `well`, `read`, and `perturbation`.

`region`
`region_key`
`instance_key`
  `region`, `region_key`, and `instance_key` are the three fields of `spatialdata_attrs` on a table (existing behaviour). `region` names the annotated element or elements. `region_key` names the `obs` column that holds that name per row. `instance_key` names the `obs` column that holds the instance id, such as a label value.

`spatialdata_attrs`
  `spatialdata_attrs` is the dictionary that the spatialdata `TableModel` writes to `adata.uns` to link a table to spatial elements (existing behaviour). This specification leaves it exactly as `TableModel` defines it and puts its own table metadata in `adata.uns["sp-ops"]`.

AnnData
  AnnData is an annotated data matrix with `X`, `obs`, `var`, `uns`, `obsm`, and `obsp`. Every spatialdata table is an AnnData, and the OPS data standard lists AnnData v0.10 or later among its dependencies.

ngio
  ngio is the BioVisionCenter library whose table specifications this specification reuses. Its five table types, `generic_table`, `roi_table`, `masking_roi_table`, `feature_table`, and `condition_table`, were originally defined as part of Fractal.
```

## Format terms name the standards this specification builds on

```{glossary}
OME-NGFF
  The Next-Generation File Format (NGFF) of the Open Microscopy Environment (OME) community specifies how bioimages and their metadata are stored in Zarr. It includes the HCS plate and well layout. The OPS data standard pins version 0.5 for the image store (OPS data standard).

OME-Zarr
  OME-Zarr is an OME-NGFF dataset stored in Zarr. The image store of an OPS submission is an OME-Zarr HCS plate.

Zarr v3
  Zarr version 3 is the chunked array storage format that OME-NGFF 0.5 uses. Each group or array has a `zarr.json` with `"zarr_format": 3`, and this specification places its extension keys in the group `attributes` object next to `ome`.

Parquet
  Parquet is a columnar file format for tables. The OPS data standard lists Parquet 2.6 for `cell_data.parquet`, and scallops writes its features, reads, and bases as Parquet files.

GeoParquet
  GeoParquet is Parquet with a geometry column, written and read by geopandas. spatialdata v0.8.0 stores each shapes element as a `shapes.parquet` file inside its Zarr group (existing behaviour), which the author's draft calls a geoparquet file.

RFC-5
  OME-NGFF request for comments 5 (RFC-5) adds named coordinate systems and the transformation types to OME-NGFF. Its status is S4 (update implementations) at version 0.6.dev3, so the `scene` objects this specification writes in the sidecar are proposed.

RFC-8
  OME-NGFF RFC-8 (proposed) defines the `Node`, `Collection`, `Path`, and `Reference` interfaces, the prefixed extension naming scheme, and string-id HCS plate and well attributes. Its status is D1, which the RFC itself calls early, so every RFC-8 structure in this specification is a proposal.
```

## Container terms describe collections and SpatialData objects

```{glossary}
collection
  A collection (proposed) is the RFC-8 node type that groups other nodes, may nest, and may carry metadata in `attributes`. This specification uses collections for the plate, each well, each tile, each `t`, and the `iss` group of cycle images inside a `t`.

sidecar
  The sidecar (proposed) is the standalone `collection.json` document written at the plate root and at each well root. It carries the RFC-8 view while the Zarr groups stay valid OME-NGFF 0.5.

node
  A node (proposed) is the common RFC-8 JSON structure with `type`, `id`, `name`, and `attributes`, where type-specific fields live inside `attributes`. RFC-8 defines the node types `collection`, `multiscale`, and `singlescale`; this specification adds `sp-ops:shapes`, `sp-ops:points`, and `sp-ops:table`.

multiscale
  A multiscale is an image pyramid, one array per resolution level, described by `multiscales` metadata in OME-NGFF 0.5 (existing behaviour). RFC-8 makes it the `multiscale` node type (proposed); the pyramid depth of the running example tiles is in the table above (illustrative).

SpatialData element
  A SpatialData element is one object of kind images, labels, points, shapes, or tables, parsed by the matching spatialdata model (existing behaviour). Every entry in the [hierarchical element paths](design-decisions.md#hierarchical-element-paths) is one element.

hierarchical SpatialData
  Hierarchical SpatialData (proposed) is an experimental spatialdata branch that allows `/` in element names, returns sub-views such as `sdata["A/1"]`, and prints a tree repr. Its slides state, of the application programming interface (API), "This represents an experimental phase. The API may evolve."; spatialdata v0.8.0 rejects `/`, so the released fallback is the flattened name `A-1-f0-t2-iss-r2`.

probe-verified
  "Probe-verified" marks a statement about spatialdata v0.8.0 that was tested by running the release in an isolated environment. The label is a convention of this specification, defined on the [overview page](overview.md#every-statement-is-normative-existing-behaviour-or-a-proposal), and it separates tested behaviour from documented behaviour.

writer, reader, validator
  A writer is software that produces a store, a reader is software that opens one, and a validator is software that checks a store against this specification. Normative sentences name which of the three they bind ([overview](overview.md#every-statement-is-normative-existing-behaviour-or-a-proposal)).
```

## Sources

### OME-NGFF 0.5 is released; RFC-5 and RFC-8 are proposals

- [OME-NGFF dev specification, plate metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#plate-metadata): `acquisitions`, `rows`, `columns`, `wells`, `field_count`, and the acquisition fields `id`, `name`, `maximumfieldcount`.
- [OME-NGFF dev specification, well metadata](https://ngff.openmicroscopy.org/specifications/dev/index.html#well-metadata): `well.images[].path` and the conditional `acquisition` key.
- [OME-NGFF 0.5](https://ngff.openmicroscopy.org/0.5/) and its [HCS layout](https://ngff.openmicroscopy.org/0.5/#hcs-layout): the released version the OPS data standard pins.
- [OME-NGFF RFC-8, HCS metadata](https://ngff.openmicroscopy.org/rfc/8/index.html#high-content-screening-hcs-metadata): `Node`, `Collection`, `Path`, `Reference`, extension naming, status D1.
- [OME-NGFF RFC index](https://ngff.openmicroscopy.org/rfc/index.html): entry point for RFC-5, coordinate systems, scenes, and transformation types, status S4, version 0.6.dev3.

### Zarr v3, Parquet, ngio tables, and RFC 2119 are released

- [Zarr v3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html): `zarr.json` and `zarr_format`.
- [Apache Parquet file format](https://parquet.apache.org/docs/file-format/): the columnar format used by the OPS data standard and scallops.
- [ngio table specifications](https://biovisioncenter.github.io/ngio/stable/table_specs/overview/): the five table types, their origin in Fractal, and the feature type vocabulary.
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.txt): the meaning of MUST, SHOULD, and MAY.

### spatialdata v0.8.0 and its libraries supply the in-memory model

- [spatialdata documentation](https://spatialdata.scverse.org/en/stable/): `rasterize`, `TableModel`, the transformation classes, and the v0.8.0 element models.
- [spatialdata tables tutorial](https://spatialdata.scverse.org/en/stable/tutorials/notebooks/notebooks/examples/tables.html): the `region`, `region_key`, `instance_key` annotation model.
- [anndata documentation](https://anndata.readthedocs.io): `X`, `obs`, `var`, `uns`, `obsm`, `obsp`.
- [geopandas documentation](https://geopandas.org/en/stable/): the GeoDataFrame behind shapes elements and `read_parquet`.

### The prototypes and discussions are unreleased

- [Hierarchical SpatialData slides](https://raw.githubusercontent.com/LucaMarconato/spatialdata/refs/heads/vibecoded-experiment/hierarchical-spatialdata/slides-hierarchical-spatialdata.html): `/` in element names, sub-views, tree repr, and the experimental status statement.
- [Padua hackathon issue 6](https://github.com/scverse/2026_04_hackathon_padua/issues/6): the `spatialdata_elements_graph` prototype.
- [scverse project view of Padua issue 6](https://github.com/orgs/scverse/projects/70/views/1?reload=1&pane=issue&itemId=169148807&issue=scverse%7C2026_04_hackathon_padua%7C6): the author's draft links the same issue through this view.
- [Venice hackathon relationships prototype](https://github.com/BiocCodingCollaborations/VeniceHackathon2026/tree/main/interoperability/relationships): `element_relationships` and `join_strategy`.

### Two real datasets and one draft standard anchor the running example

- [scallops and Biohub OPS layout (HackMD)](https://hackmd.io/@D9GB-ZDcTQyFd7U5aMmk5g/r18soYBuzx): cycle files, `t=` folders, `-objects.parquet` bounding boxes, CellProfiler features per compartment, `read` join column.
- CZI OPS data standard v0.1.0 (draft; no public URL appears in the source material): `cell_uid`, `perturbation_id`, `barcode`, `perturbation_library.csv`, and the format dependency table.
- Public Biohub OPS submission, audited 2026-09-02 against that standard: the well set, label names, and label dtype marked "real (audit)" in the table above. The bucket path and plate identifier are withheld because this repository is public.
