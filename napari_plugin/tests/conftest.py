import os
from pathlib import Path

import pytest
from spops_store import SyntheticScreen, build_synthetic_screen


@pytest.fixture(scope="session")
def synthetic_screen(tmp_path_factory: pytest.TempPathFactory) -> SyntheticScreen:
    return build_synthetic_screen(tmp_path_factory.mktemp("screen") / "screen.zarr")


def _example_store(variable: str) -> Path:
    value = os.environ.get(variable)
    if not value:
        pytest.skip(f"{variable} is not set")
    store = Path(value)
    if not (store / "zarr.json").is_file():
        pytest.skip(f"{variable}={store} has no zarr.json")
    return store


@pytest.fixture(scope="session")
def processed_example() -> Path:
    """Root of the conformant processed example store (Biohub portal subset)."""
    return _example_store("SP_OPS_PROCESSED_EXAMPLE")


@pytest.fixture(scope="session")
def raw_example() -> Path:
    """Root of the conformant raw example store (two-well nd2 subset)."""
    return _example_store("SP_OPS_RAW_EXAMPLE")
