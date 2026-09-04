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
the store, not a refactor. The figures in `docs/open-questions.md` are from an
older build of both stores; the ones below were measured on 2026-09-04 against
the stores in `../stores`.

| Store | Checks | Failed | Advisories |
| --- | --- | --- | --- |
| `experimentC_scallops` | 340 | 4, the empty `intermediate` tile collections of Q33 | 0 |
| `biohub_example` | 422 | 0 | 2, the empty `sp-ops:merged.source` of Q19 |

`check_sp_ops_zarr.py` never reads `multiscales`, so adding that block moved
none of these numbers.

The four scallops failures are a finding, not a defect: a stitch stage has no
per-tile product, so its tile collections are empty. Do not "fix" them.

`check_sp_ops_zarr.py` exits non-zero when anything fails, so scallops exits 1 by
design. Assert the printed line, not the exit code.

## Not yet ported

`build_experimentC_zarr.py` and `build_cpg0021_zarr.py` still stand alone and take
`DATASET_DIR OUT.zarr`. Porting them needs two things this base class does not
have yet, deliberately: the `raw` tile -> round -> channel loop, and the
cross-correlation geometry solver that only `cpg0021_sample` uses. Both should be
added when there are two real callers to generalise from. They also write
`sp-ops:layout_id`, which is not in the `docs/extension.md` registry and nothing
reads; drop it on the way through.
