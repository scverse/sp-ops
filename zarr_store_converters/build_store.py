#!/usr/bin/env python3
r"""Build an sp-ops conformant OME-Zarr store from one of the example datasets.

    python zarr_store_converters/build_store.py biohub_example
    python zarr_store_converters/build_store.py experimentC_scallops
    python zarr_store_converters/build_store.py cpg0021_sample
    python zarr_store_converters/build_store.py biohub_example --out /tmp/x.zarr --levels 3

Paths are relative to the repository root. Each store lands in its own folder
under ../stores, with the build log beside it. Verify one with:

    python zarr_store_converters/check_sp_ops_zarr.py \
        ../stores/<name>/<name>.zarr --<flag> <source>

`experimentC` is not ported to this entry point yet; it still has its own
build_experimentC_zarr.py script.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from spops.datasets.biohub import BiohubConverter
from spops.datasets.cpg0021 import Cpg0021Converter
from spops.datasets.scallops import ScallopsConverter

HERE = Path(__file__).resolve().parent
DATASETS = HERE / ".." / ".." / "datasets"
STORES = HERE / ".." / ".." / "stores"

# dataset name -> converter, and the source roots its `load` expects
REGISTRY = {
    "biohub_example": (BiohubConverter, {"dataset": "biohub_example"}),
    "cpg0021_sample": (Cpg0021Converter, {"dataset": "cpg0021_sample"}),
    "experimentC_scallops": (ScallopsConverter, {"scallops": "experimentC_scallops",
                                                 "raw": "experimentC_raw"}),
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dataset", choices=sorted(REGISTRY))
    p.add_argument("--source", type=Path, action="append", default=[], metavar="[ROLE=]PATH",
                   help="override a source root; repeat for a dataset with several")
    p.add_argument("--out", type=Path, help="store path (default stores/<name>/<name>.zarr)")
    p.add_argument("--levels", type=int, help="pyramid levels, overriding the default")
    p.add_argument("--overwrite", action="store_true",
                   help="required to replace an existing store")
    args = p.parse_args(argv)

    cls, roles = REGISTRY[args.dataset]
    sources = {role: (DATASETS / d).resolve() for role, d in roles.items()}
    for override in args.source:
        role, _, path = str(override).partition("=")
        if not path:                      # a bare path, only unambiguous for one role
            if len(sources) != 1:
                p.error(f"{args.dataset} has several sources {sorted(sources)}; "
                        f"use --source ROLE=PATH")
            role, path = next(iter(sources)), role
        if role not in sources:
            p.error(f"unknown source role {role!r}; expected one of {sorted(sources)}")
        sources[role] = Path(path).expanduser().resolve()

    for role, path in sources.items():
        if not path.exists():
            p.error(f"source {role!r} does not exist: {path}")

    out = args.out.expanduser() if args.out else \
        (STORES / args.dataset / f"{args.dataset}.zarr").resolve()
    if out.exists() and not args.overwrite:
        p.error(f"{out} exists; pass --overwrite to replace it")
    out.parent.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger("spops")
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler())
    handler = logging.FileHandler(out.parent / "build.log", mode="w")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    log.addHandler(handler)

    log.info("building %s from %s", args.dataset,
             ", ".join(f"{r}={s}" for r, s in sorted(sources.items())))
    converter = cls(sources, out)
    if args.levels is not None:
        converter.pyramid_levels = args.levels
    converter.build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
