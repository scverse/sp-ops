#!/usr/bin/env python3
"""Render the relationships graph and the transformations graph of an sp-ops-conformant
OME-Zarr store.

    uv run --group viz python visualization/render_graphs.py --store /path/to/store.zarr \\
        --out-dir visualization/output

Writes, per requested graph, a static `<name>.svg` (skipped if Graphviz's `dot` is not on
PATH) and an interactive, self-contained `<name>.html` (open it in any browser; drag nodes,
hover an edge for its full `sp-ops:relationships`/transform payload).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from render import render_html, render_svg
from store_graph import build_relationships_graph, build_transformations_graph, drop_isolated_nodes, walk_store


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--store", required=True, type=Path, help="path to a *.zarr sp-ops store root")
    parser.add_argument("--out-dir", required=True, type=Path, help="directory to write the graphs into")
    parser.add_argument(
        "--graphs",
        default="relationships,transformations",
        help="comma-separated subset of: relationships, transformations (default: both)",
    )
    parser.add_argument("--direction", default="LR", choices=["LR", "TB"], help="layout direction (default: LR)")
    parser.add_argument(
        "--include-isolated",
        action="store_true",
        help="keep elements with no edge at all (dropped by default -- most of a store has "
        "nothing declared about it, and rendering those nodes only drowns out what does)",
    )
    args = parser.parse_args()

    if not args.store.exists():
        parser.error(f"store not found: {args.store}")
    wanted = {g.strip() for g in args.graphs.split(",") if g.strip()}
    unknown = wanted - {"relationships", "transformations"}
    if unknown:
        parser.error(f"unknown graph(s): {', '.join(sorted(unknown))}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"walking {args.store} ...")
    tree = walk_store(args.store)
    print(f"  {len(tree.nodes)} RFC-8 nodes found")

    def prepare(g):
        if args.include_isolated:
            return g, 0
        filtered = drop_isolated_nodes(g)
        return filtered, g.number_of_nodes() - filtered.number_of_nodes()

    if "relationships" in wanted:
        g, n_dropped = prepare(build_relationships_graph(tree))
        dropped_note = f" ({n_dropped} edgeless nodes dropped)" if n_dropped else ""
        print(f"relationships graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges{dropped_note}")
        render_svg(g, args.out_dir / "relationships.svg", direction=args.direction)
        html_path = render_html(g, args.out_dir / "relationships.html", title=f"{args.store.name} — relationships", direction=args.direction)
        print(f"  wrote {html_path}")

    if "transformations" in wanted:
        g, n_dropped = prepare(build_transformations_graph(tree))
        dropped_note = f" ({n_dropped} edgeless nodes dropped)" if n_dropped else ""
        print(f"transformations graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges{dropped_note}")
        render_svg(g, args.out_dir / "transformations.svg", direction=args.direction)
        html_path = render_html(g, args.out_dir / "transformations.html", title=f"{args.store.name} — transformations", direction=args.direction)
        print(f"  wrote {html_path}")


if __name__ == "__main__":
    main()
