from __future__ import annotations

from typing import Any

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the explicit real-model test switch for the Windows GPU laptop."""

    parser.addoption(
        "--run-gpu",
        action="store_true",
        default=False,
        help="run tests that load the real light model",
    )


def _cuda_available() -> bool:
    try:
        import torch
    except ImportError:
        return False
    return bool(torch.cuda.is_available())


def pytest_collection_modifyitems(config: pytest.Config, items: list[Any]) -> None:
    """Skip real-model tests unless requested or CUDA is available."""

    if config.getoption("--run-gpu") or _cuda_available():
        return
    skip = pytest.mark.skip(reason="requires --run-gpu or a CUDA-capable laptop")
    for item in items:
        if "gpu" in item.keywords:
            item.add_marker(skip)
