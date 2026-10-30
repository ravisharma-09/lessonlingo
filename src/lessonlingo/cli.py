"""LessonLingo command-line interface."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from lessonlingo.setup_models import run_setup, run_verify


def build_parser() -> argparse.ArgumentParser:
    """Build the LessonLingo command-line parser."""

    parser = argparse.ArgumentParser(
        prog="lessonlingo",
        description="Free lessons in your language. Set up once, then no internet needed.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command, help_text in (
        ("setup", "download models once for later translation without internet"),
        ("verify", "verify that setup completed using only the local cache"),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument(
            "--cache-dir",
            type=Path,
            help="use a specific Hugging Face cache directory",
        )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the LessonLingo command-line interface."""

    args = build_parser().parse_args(argv)
    if args.command == "setup":
        return run_setup(args.cache_dir)
    return run_verify(args.cache_dir)


if __name__ == "__main__":
    raise SystemExit(main())
