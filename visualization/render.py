"""Render a graph built by store_graph.py as Graphviz DOT/SVG and as a self-contained,
interactive HTML page (vis-network, loaded from a CDN -- no bundling, no build step).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import networkx as nx

from store_graph import COORDINATE_SYSTEM, DANGLING

_KIND_COLOR = {
    "collection": "#2F3E4E",
    "multiscale": "#174F8C",
    "sp-ops:table": "#1A5C35",
    "sp-ops:shapes": "#5C2D91",
    "sp-ops:points": "#5C2D91",
    COORDINATE_SYSTEM: "#A84300",
    DANGLING: "#B3261E",
}
_DEFAULT_COLOR = "#555555"

_STATUS_STYLE = {"suggested": "dashed"}  # everything else (e.g. "computed") is solid


def _node_label(g: nx.DiGraph, path: str) -> str:
    data = g.nodes[path]
    if data.get("kind") == COORDINATE_SYSTEM:
        return f"[{data.get('label', path)}]"
    return data.get("label") or path or "(screen root)"


def _edge_label(data: dict[str, Any]) -> str:
    parts = []
    if data.get("method"):
        parts.append(data["method"])
    if data.get("cardinality"):
        parts.append(data["cardinality"])
    if data.get("type"):
        parts.append(data["type"])
    if data.get("status") and data["status"] != "computed":
        parts.append(f"({data['status']})")
    return "\n".join(parts)


def _dot_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def to_dot(g: nx.DiGraph, *, direction: str = "LR") -> str:
    lines = [
        "digraph G {",
        f"  rankdir={direction};",
        '  node [shape=box, style=filled, fontname="Helvetica", fontsize=10, fontcolor=white];',
        '  edge [fontname="Helvetica", fontsize=9];',
    ]
    for path, data in g.nodes(data=True):
        kind = data.get("kind", "")
        shape = "diamond" if kind == COORDINATE_SYSTEM else "box"
        color = _KIND_COLOR.get(kind, _DEFAULT_COLOR)
        label = _dot_escape(_node_label(g, path))
        lines.append(f'  "{path}" [label="{label}", shape={shape}, fillcolor="{color}"];')
    for u, v, data in g.edges(data=True):
        label = _dot_escape(_edge_label(data))
        style = _STATUS_STYLE.get(data.get("status"), "solid")
        lines.append(f'  "{u}" -> "{v}" [label="{label}", style={style}];')
    lines.append("}")
    return "\n".join(lines)


def render_svg(g: nx.DiGraph, out_path: Path, *, direction: str = "LR") -> Path | None:
    """Render via the system `dot` binary. Returns None (and warns) if it isn't installed."""
    dot_bin = shutil.which("dot")
    if dot_bin is None:
        print(f"  (skipping {out_path.name}: the Graphviz `dot` binary is not on PATH)")
        return None
    dot_source = to_dot(g, direction=direction)
    result = subprocess.run([dot_bin, "-Tsvg"], input=dot_source, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"dot failed rendering {out_path}:\n{result.stderr}")
    out_path.write_text(result.stdout)
    return out_path


_HTML_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  html, body {{ margin: 0; height: 100%; font-family: -apple-system, Helvetica, Arial, sans-serif; }}
  #graph {{ width: 100vw; height: 100vh; }}
  #title {{ position: absolute; top: 8px; left: 12px; font-size: 14px; color: #333;
            background: rgba(255,255,255,0.85); padding: 4px 10px; border-radius: 4px; z-index: 1; }}
</style>
</head>
<body>
<div id="title">{title} &mdash; {n_nodes} nodes, {n_edges} edges</div>
<div id="graph"></div>
<script>
  const nodes = new vis.DataSet({nodes_json});
  const edges = new vis.DataSet({edges_json});
  const container = document.getElementById("graph");
  const data = {{ nodes, edges }};
  const options = {{
    layout: {{ hierarchical: {{ direction: "{direction}", sortMethod: "directed", nodeSpacing: 160, levelSeparation: 220 }} }},
    nodes: {{ shape: "box", font: {{ color: "#ffffff", multi: false }}, margin: 8 }},
    edges: {{ arrows: "to", font: {{ align: "top", size: 11 }}, smooth: {{ type: "cubicBezier" }} }},
    physics: false,
    interaction: {{ hover: true, tooltipDelay: 100 }},
  }};
  new vis.Network(container, data, options);
</script>
</body>
</html>
"""

_VIS_DIRECTION = {"LR": "LR", "TB": "UD"}


def render_html(g: nx.DiGraph, out_path: Path, *, title: str, direction: str = "LR") -> Path:
    vis_nodes = []
    for path, data in g.nodes(data=True):
        kind = data.get("kind", "")
        vis_nodes.append(
            {
                "id": path,
                "label": _node_label(g, path),
                "shape": "diamond" if kind == COORDINATE_SYSTEM else "box",
                "color": _KIND_COLOR.get(kind, _DEFAULT_COLOR),
                "title": f"{kind}: {path or '(screen root)'}",
            }
        )
    vis_edges = []
    for u, v, data in g.edges(data=True):
        vis_edges.append(
            {
                "from": u,
                "to": v,
                "label": _edge_label(data),
                "dashes": data.get("status") in _STATUS_STYLE,
                "title": _dot_escape(json.dumps({k: val for k, val in data.items() if k != "params"}, default=str)),
            }
        )
    html = _HTML_TEMPLATE.format(
        title=title,
        n_nodes=len(vis_nodes),
        n_edges=len(vis_edges),
        nodes_json=json.dumps(vis_nodes),
        edges_json=json.dumps(vis_edges),
        direction=_VIS_DIRECTION.get(direction, "LR"),
    )
    out_path.write_text(html)
    return out_path
