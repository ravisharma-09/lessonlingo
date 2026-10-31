"""A stop signal for long steps: listening, translating and speaking check it between pieces."""

from __future__ import annotations

import threading


class Cancelled(RuntimeError):
    """Raised inside a long step when the user pressed Cancel."""


_flag = threading.Event()


def request() -> None:
    """Ask the running step to stop at its next safe point."""

    _flag.set()


def reset() -> None:
    """Clear the signal before a new step starts."""

    _flag.clear()


def check() -> None:
    """Stop with `Cancelled` if Cancel was pressed."""

    if _flag.is_set():
        raise Cancelled("Stopped. Nothing was changed.")
