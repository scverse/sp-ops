"""The synthetic screen opens over HTTP: detection walks URL parents and parquet goes through fsspec."""

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from napari.components import ViewerModel
from npe2 import PluginManager


@pytest.fixture(scope="module", autouse=True)
def discover_plugins():
    PluginManager.instance().discover()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        return


@pytest.fixture(scope="module")
def served_screen(synthetic_screen):
    handler = functools.partial(QuietHandler, directory=str(synthetic_screen.root.parent))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/{synthetic_screen.root.name}"
    server.shutdown()


def test_merged_collection_opens_over_http(served_screen):
    layers = ViewerModel().open(f"{served_screen}/plate1_processed/A/1/pheno/merged", plugin="napari-sp-ops")
    assert [layer.name for layer in layers] == ["GFP", "nuclei_prediction", "cells", "overlay"]
    assert tuple(layers[0].translate) == (15600.0, 15600.0)
    assert layers[2].features["index"].tolist() == [1, 2, 3, 4]


def test_points_and_layout_open_over_http(served_screen):
    layers = ViewerModel().open(f"{served_screen}/plate1_processed/A/1/iss/merged", plugin="napari-sp-ops")
    assert [type(layer).__name__ for layer in layers] == ["Image", "Image", "Points"]
    layers = ViewerModel().open(f"{served_screen}/plate1_raw/A/1/iss/tiles", plugin="napari-sp-ops")
    assert type(layers[0]).__name__ == "Shapes" and len(layers) == 5
