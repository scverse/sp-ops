# Store audit

`scripts/check_sp_ops_zarr.py` reports both rebuilt stores at the counts
[](open-questions.md#rebuilding-the-stores) records: `experimentC_scallops` 361 checks with the four
Q33 failures, `biohub_example` 435 checks clean. Everything on this page is therefore something the
checker does not test. Each entry came from reading the two stores back against the requirement
text of [](layout.md), [](extension.md), [](features.md) and [](joinable-components.md), and each
names the store it came from.

Ten entries. Six are requirements a store does not meet, four are places where two pages, or a page
and its data, cannot both be right. Entries carry stable `S` ids so they can be cited without
colliding with the `Q` series of [](open-questions.md), the `D` decisions, or the `A` assumptions.

| | `experimentC_scallops` | `biohub_example` |
| --- | --- | --- |
| stage | `intermediate`, `processed` | `processed` |
| multiscales | 21 (14 image, 7 labels) | 16 (4 image, 12 labels) |
| tables · points · shapes | 14 · 2 · 2 | 3 · 0 · 0 |
| relationship edges | 13 | 13 |
| tables with no incident edge (S3) | 5 of 14 | 1 of 3 |

## Requirements a store does not meet

### S1. A modality has a third child the hierarchy does not name

From `experimentC_scallops` · Affects [](layout.md#modalities-tiles-and-merged-images), D2

[](layout.md#modalities-tiles-and-merged-images) opens "A modality collection has two children",
and the level table gives a modality exactly `tiles` and `merged`. Both `intermediate` modalities
have three: `plate1_intermediate/A/1/iss` and `.../pheno` each hold `tiles`, `merged` and
`illumination`, the last carrying nine and one flat field profiles in the tile frame. There is
nowhere else for them. They are not a field of view, so they are not `tiles`; they are not the
stitched well, so they are not `merged`. The checker never sees them: `walk_modality` looks up the
names `tiles` and `merged` and ignores every other child, so a modality can carry any number of
undeclared collections and check clean.

Fix. Say whether a modality MAY hold further collections, and if so that a reader ignores the ones
it does not know. Then either name a calibration child or accept that the two-children sentence is
a description of the common case rather than a rule. This is Q36 as a structural question rather
than a granularity one: `illumination` is per round and per channel, and the feature ladder starts
at the cell.

### S2. `sp-ops:axis` is written on a multiscale, outside `raw`

From `experimentC_scallops` · Affects `sp-ops:axis`

[](extension.md) binds `sp-ops:axis` to a "round or channel node" and makes it MUST in `raw`.
`plate1_intermediate/A/1/iss/illumination/round0` is a `multiscale` whose attributes are
`sp-ops:channels`, `sp-ops:axis` and `coordinateSystems`, with
`sp-ops:axis {"name": "round", "index": 0, "value": 1}`. The round it names is not a collection and
the store is not `raw`, so the key is being used outside both halves of its definition — as the
only way to say which imaging pass a profile belongs to.

Fix. Either bind `sp-ops:axis` to any node that represents one position along an axis, whatever the
stage, or give a non-`raw` element another way to name its round. Q17 asks the same question from
the other end, where the key says nothing because a raw channel array has no `c` axis.

### S3. Six of seventeen tables have no incident edge

From both stores · Affects `sp-ops:relationships`, [](features.md)

[](extension.md) makes `sp-ops:relationships` "MUST for every table that describes an element", and
[](features.md) opens by saying every granularity is "a table whose rows describe one element at
the same level of the hierarchy, linked to it by an edge". Six tables have no edge at either end:

| Table | Rows describe |
| --- | --- |
| `plate1_intermediate/A/1/iss/merged/stitch_features` | one stitching run per round |
| `plate1_intermediate/A/1/pheno/merged/stitch_features` | the one stitching run |
| `plate1_processed/A/1/iss/merged/crosstalk` | the 4 by 4 base bleed matrix |
| `plate1_processed/A/1/iss/merged/peak_thresholds_labels` | a threshold sweep, 98 rows |
| `plate1_processed/A/1/iss/merged/peak_thresholds_crosstalk` | a threshold sweep, 98 rows |
| `feature_definitions` | 2935 feature names, no values (Q24) |

None of them describes an element. A stitching score describes a run, a bleed matrix describes an
optical path, a threshold sweep describes a decision, and a feature dictionary describes other
tables' columns. `check_relationships` is called with `required=False` everywhere, so the MUST is
never enforced and these pass.

Fix. Q7 proposes that an empty edge list is the correct value for a collection with no joinable
pairs, and Q36 proposes a granularity for the parameters and diagnostics of a processing step. Both
are needed, and the MUST should be narrowed to "every table that describes an element", with the
converse stated: a table that describes no element MUST say so rather than being silent. As written
the requirement cannot distinguish a diagnostic table from a forgotten edge.

### S4. A table column name puts a `.` into a path segment

From `experimentC_scallops` · Affects D3, [](extension.md)

D3 records that OME-NGFF path names are restricted to alphanumerics, `-` and `_`, and that RFC-8
ids match `[a-zA-Z0-9-_.]+`. `peak_thresholds_labels` and `peak_thresholds_crosstalk` each carry a
column literally named `f0.5`, and AnnData encodes an `obs` column as a group, so the store contains

```text
plate1_processed/A/1/iss/merged/peak_thresholds_labels/obs/f0.5
```

a path segment with a `.` in it. Nothing in the specification reaches inside a table, so nothing
forbids it and nothing detects it, but the character restriction D3 relies on is broken by data
rather than by a writer's naming choice. Q42 notes the same divergence for a labels element named
`.all`; that one a writer can rename, this one is a column an analyst asked for.

Fix. Say whether the path restriction applies inside a leaf element or only to the nodes the
specification names. If it applies throughout, a writer has to mangle column names and record the
mapping, which is worth saying explicitly because it is lossy.

### S5. A merged collection's only images are renderings

From `biohub_example` · Affects [](layout.md), `sp-ops:channels`, Q20

`plate1_processed/A/1/iss/merged` holds exactly two elements, `iss_gene_image` and
`iss_guide_image`, both `(4, 2048, 2048)` `uint8` RGBA rasters of a gene and guide assignment. They
are pictures of a result, not measurements. Nothing marks them as such, so they satisfy every
requirement a measured image satisfies: the checker's `check(len(images) >= 1)` for a merged
collection is met by them, and `sp-ops:channels` is filled with four entries named `R`, `G`, `B`,
`A` at role `other` — an array-order channel contract used to describe colour planes. The one
declared ISS modality of this delivery consists entirely of renderings, and a reader following the
metadata cannot tell.

Fix. Q20 asks `role` to separate what a channel is for from how it was produced. This is the
stronger version: a rendering is not a channel stack at all, and needs either its own node type or
a flag on the multiscale. Until then the requirement that a merged collection hold an image is
satisfiable by a screenshot.

### S6. `sp-ops:registration` has no way to say there is nothing to register against

From `biohub_example` · Affects `sp-ops:registration`, D7

`sp-ops:registration` is a SHOULD on a processed multiscale. Four of `biohub_example`'s processed
multiscales omit it: the three renderings of S5, and `plate1_processed/A/1/pheno/merged/image`,
which omits it correctly — it is a merged-only submission with one image per well, so there is no
second element to register to and no anchor channel that means anything. The key has no value for
"this is the reference" or "registration does not apply", so a conformant store that legitimately
has nothing to say is indistinguishable from one whose writer forgot.

Fix. Give `sp-ops:registration` a form that states the element is its own reference, and say that
the SHOULD does not apply to a derived raster. Q37 asks for the same expressiveness in the opposite
case, where stacked rounds are not registered and no key can say so, and Q50 asks for it one stage
earlier. All three want the key to be able to describe an absence.

## Where two pages, or a page and its data, disagree

### S7. `layout` to `tile_features` is 1:1 in the specification and 1:n in the data

From `experimentC_scallops` · Affects [](features.md#tile-and-well-features)

[](features.md#tile-and-well-features) gives the tile table as "one row per tile" and its edge as

```json
{"from": "layout", "to": "tile_features", "on": {"left": "tile", "right": "tile"},
 "cardinality": "1:1"}
```

A multi-round modality does not have one row per tile. `plate1_intermediate/A/1/iss` has a `layout`
of 2 polygons and a `tile_features` of 18 rows, one per tile and round, because the stitcher scores
every round separately; the store declares the edge `1:n`. The phenotyping modality, with one
round, has 2 rows and would be `1:1`. So the same element is `1:1` or `1:n` depending on how many
rounds a modality has, and the page states only the single-round case.

Fix. Either say tile granularity is one row per tile and per round, making the edge `1:n` and the
key two columns — which Q40 also needs — or keep one row per tile and say where a per-round score
goes instead. The example's `1:1` should not be the only cardinality shown.

### S8. Two columns the specification names by name are absent

From `experimentC_scallops` · Affects [](joinable-components.md)

[](joinable-components.md) tabulates the elements every screen has with the columns their rows
carry. Two are missing from the store:

| Element | Columns the page names | Columns present |
| --- | --- | --- |
| `iss/merged/peaks` | `x`, `y`, `read` | `y`, `x`, `sigma`, `peak` |
| `pheno/merged/cells_features` | features, `barcode` once assigned | `label`, geometry, features, `cell_label`, `has_features` |

`peaks` has no `read`, so the join the page calls "the join key between a peak and its decoded
read" cannot be made; the store declares that edge `suggested` on `y` alone. The barcode calls
exist, in a sibling `cell_barcodes` table of 2798 rows against 4589 cells, which
[](features.md#merged-and-split-tables) permits as a split.

The page does hedge — "`cell_label`, `barcode`, and `read` are example column names; the edge, not
this page, fixes the names a store uses". But the hedge covers naming, not absence: no renaming
makes a `read` column appear on `peaks`.

Fix. Separate the two claims the table currently makes. Which facts an element must carry is a
requirement; which column carries them is not. Then say `peaks` need not be decodable on its own,
which is what Q40 is really about, and that a named column may live in a split table.

### S9. Axis names are now recorded twice, with nothing requiring agreement

From both stores · Affects [](extension.md), Q18

Both stores are written through ome-zarr-py, which sets the Zarr v3 `dimension_names` on every
pyramid level array. So each level now records its axis names twice: once in core Zarr metadata and
once in the RFC-8 `coordinateSystems[].axes[].name` of its `singlescale` node. Across the two
stores that is 121 level arrays, and all 121 agree — but only because one writer produced both, and
nothing in the specification or the checker compares them.

Fix. Say which is authoritative and require the other to agree, then make it a validator check.
This is the shape of Q31, where a labels element and its source image both record a pixel size and
nothing requires them to match, and of Q49, where `layout` and the tile-to-well transforms both
record a position. Two records of one fact and no stated precedence is a pattern worth fixing once
rather than three times.

### S10. `ome.version` is a placeholder, so a reader cannot tell what it is reading

From both stores · Affects A2, [](layout.md#screen-and-plates)

Every `ome` attribute in both stores carries `"version": "0.x"`, which is what
[](layout.md#screen-and-plates) shows and what A2 tracks, because RFC-8 is a draft with no released
version number. A reader therefore cannot tell which revision of the node model a store was written
against, and two stores written a year apart are indistinguishable. The `sp-ops:spec` version
(`0.2.0-draft`) dates this specification but says nothing about the RFC-8 revision underneath it.

Fix. Until RFC-8 has a number, record the draft the store was written against — a date or the RFC
revision — rather than `0.x`. A2 should also state what a reader does with a version it does not
recognise, which RFC-8's own extensibility rules answer for prefixed keys but not for the node
model itself.

## What the audit confirms

Eight entries of [](open-questions.md) are reproduced by the rebuilt stores exactly as recorded,
and are not restated above: Q14 (the row half of `A/1` carries no metadata, in both stores and both
plates of `experimentC_scallops`), Q19 (`sp-ops:merged.source` is `[]` on both `biohub_example`
modalities), Q24 (`feature_definitions` annotates nothing), Q33 (four empty tile collections, the
four checker failures), Q34 (the reads-to-library edge, the one advisory), Q36 (run-level
diagnostics, which S3 counts), Q40 (the peak key, which S8 sharpens) and Q42 (the `.` divergence,
which S4 finds a second instance of).

Three things the audit checked and found correct, worth recording because each is a plausible way
to get a store wrong: every labels element is `int32` as [](features.md) gives it; every labels
element agrees with its `labels.source` image on physical extent to within a micrometre, which is
the Q31 advisory and which the `biohub_example` pixel-size correction is what makes true; and every
element id in both stores is unique and matches `[a-zA-Z0-9-_.]+`.
