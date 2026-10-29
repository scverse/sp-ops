# Store builders

`build_store.py` builds a dataset into `../stores/<name>/<name>.zarr`, with the
build log beside it. `check_sp_ops_zarr.py` validates a store against the
specification and, given the source, against the pixels it was written from.

Both are run from the repository root:

```bash
python zarr_store_converters/build_store.py biohub_example
python zarr_store_converters/check_sp_ops_zarr.py \
    ../stores/biohub_example/biohub_example.zarr --zarr ../datasets/biohub_example
```

`cpg0021_sample` needs its ND2 root rather than the dataset root, because that
is where `--nd2` expects the acquisition directories:

```bash
python zarr_store_converters/build_store.py cpg0021_sample
python zarr_store_converters/check_sp_ops_zarr.py \
    ../stores/cpg0021_sample/cpg0021_sample.zarr --nd2 \
    ../datasets/cpg0021_sample/cpg0021-periscope/broad/images/20200805_A549_WG_Screen/images/CP186A
```

Dependencies live in the `convert` group: `uv sync --group convert`. Note that
`uv sync` makes the environment match exactly the groups you name, so to keep
the docs build too, ask for both: `uv sync --group convert --group docs`.

## Layout

```
spops/
├── rfc8.py       RFC-8 node and RFC-5 coordinate metadata, as plain dicts. No I/O.
├── elements.py   The four element writers: multiscale, table, shapes, points.
├── converter.py  ScreenConverter, the shared skeleton of a build.
└── datasets/     One subclass per dataset.
```

## Three things to know before changing `elements.py`

**ome-zarr-py writes the arrays, never the metadata.** RFC-8 says its `Multiscale`
node replaces the `multiscales` block that ome-zarr-py emits, and assumption A2
says this store writes RFC-8 nodes, so `group.attrs["ome"]` is overwritten
after every library call. `write_labels`, `write_plate_metadata` and
`write_well_metadata` are structurally wrong here and are never used.

**The `multiscales` block is put back, on purpose.** No reader in circulation
finds a pyramid in the `singlescale` nodes: napari-ome-zarr dispatches on
`multiscales` and nothing else, and napari-sp-ops reads its levels from
`multiscales[0].datasets`, so a store without the block opens as zero layers in
napari. `rfc8.multiscales_block` rebuilds it from the same `level_body` numbers
as `level_nodes`, alongside the nodes rather than instead of them, so the two
cannot drift and an RFC-8 reader still gets the coordinate systems. Do not drop
it again without checking what opens the store.

**Pyramid levels are renamed on disk.** ome-zarr-py names them `s0`, `s1`, `s2`
and that is not configurable, so `_rename_levels` moves them to `0`, `1`, `2`.
This is load bearing: `check_sp_ops_zarr.py` reads level 0 by literal name in
`extent_um`, and when that returns `None` the label-extent advisory is skipped
*and its counter is not incremented*, so the check total silently drops rather
than failing. zarr-python 3 has no rename API -- `Group.move` does not exist and
`AsyncGroup.move` raises `NotImplementedError` -- so the rename is a filesystem
move and every element writer requires a `LocalStore`.

## Expected checker output

These counts are the regression gate. A change that alters them is a change to
the store, not a refactor. All three rows were measured on 2026-09-04 by
rebuilding each store from this package and running the checker on the result,
and they agree with `docs/open-questions.md`. The 340 and 422 this table
carried before that were stale: the stores they describe check at 361 and 435
today, unchanged and unrebuilt, so the figures were wrong rather than the
stores.

| Store | Checks | Failed | Advisories |
| --- | --- | --- | --- |
| `experimentC_scallops` | 361 | 4, the empty `intermediate` tile collections of Q33 | 1, the reads-to-library edge of Q15 |
| `biohub_example` | 435 | 0 | 2, the empty `sp-ops:merged.source` of Q19 |
| `cpg0021_sample` | 27036 | 0 | 0 |

`check_sp_ops_zarr.py` never reads `multiscales`, so adding that block moved
none of these numbers.

The four scallops failures are a finding, not a defect: a stitch stage has no
per-tile product, so its tile collections are empty. Do not "fix" them.

`check_sp_ops_zarr.py` exits non-zero when anything fails, so scallops exits 1 by
design. Assert the printed line, not the exit code.

`cpg0021_sample` is the only store whose numbers move between builds. Its tile
positions are measured from the pixels rather than read from the delivery's
position list, so a change to `spops/datasets/cpg0021_geometry.py` changes the
transforms. The check count does not depend on them: the layout and the
transforms are derived from the same solve, so they agree whatever it returns.

## The raw loop

`ScreenConverter.raw_tiles` walks tile -> [round ->] channel for a `raw` plate
and takes a `read(tile, round)` callback for the pixels. It was held back until
there was more than one dataset to generalise from; `cpg0021_sample` is the
first caller and `experimentC` is shaped to be the second, so keep the seam
where it is -- a delivery varies in its file format, not in the shape below the
tile, which `docs/layout.md` fixes.

## Not yet ported

`build_experimentC_zarr.py` still stands alone and takes `DATASET_DIR OUT.zarr`.
It writes `sp-ops:layout_id`, which is not in the `docs/extension.md` registry
and nothing reads; drop it on the way through.
