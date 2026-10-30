"""Command-line setup and offline verification for LessonLingo."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelSpec:
    """A model snapshot required for a LessonLingo runtime mode."""

    mode: str
    repository: str
    approximate_size: str


MODELS = (
    ModelSpec(
        mode="quality",
        repository="ai4bharat/indictrans2-en-indic-1B",
        approximate_size="4.5 GB",
    ),
    ModelSpec(
        mode="light",
        repository="ai4bharat/indictrans2-en-indic-dist-200M",
        approximate_size="1.1 GB",
    ),
)


SnapshotDownload = Callable[..., str]


def enable_offline_mode() -> None:
    """Prevent Hugging Face model libraries from making HTTP requests."""

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


def enable_online_setup() -> None:
    """Allow the one-time setup command to contact the model Hub."""

    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)


def download_models(
    snapshot_download: SnapshotDownload,
    cache_dir: Path | None = None,
) -> None:
    """Download the safetensors snapshot for every supported runtime mode."""

    for model in MODELS:
        print(
            f"Downloading {model.mode} model ({model.approximate_size}): "
            f"{model.repository}"
        )
        snapshot_download(
            repo_id=model.repository,
            cache_dir=str(cache_dir) if cache_dir else None,
            ignore_patterns=["*.bin"],
        )


def verify_models(
    snapshot_download: SnapshotDownload,
    cache_dir: Path | None = None,
) -> None:
    """Verify that all required model snapshots exist without network access."""

    for model in MODELS:
        snapshot_download(
            repo_id=model.repository,
            cache_dir=str(cache_dir) if cache_dir else None,
            ignore_patterns=["*.bin"],
            local_files_only=True,
        )
        print(f"Found {model.mode} model in the local cache.")


def run_setup(cache_dir: Path | None = None) -> int:
    """Authenticate when needed and download all required models."""

    enable_online_setup()
    from huggingface_hub import get_token, login, snapshot_download
    from huggingface_hub.errors import GatedRepoError

    if get_token() is None:
        print("Hugging Face login is required for the gated IndicTrans2 models.")
        login()

    try:
        download_models(snapshot_download, cache_dir)
    except GatedRepoError as error:
        repositories = "\n".join(
            f"  - https://huggingface.co/{model.repository}" for model in MODELS
        )
        raise SystemExit(
            "Model access has not been granted. Sign in, accept the access "
            f"terms at both URLs, then run lessonlingo setup again:\n{repositories}"
        ) from error

    print("Setup complete. Both models are ready for offline use.")
    print("Turn off Wi-Fi and run: HF_HUB_OFFLINE=1 lessonlingo verify")
    return 0


def run_verify(cache_dir: Path | None = None) -> int:
    """Check the local model cache with all Hub network access disabled."""

    enable_offline_mode()
    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import LocalEntryNotFoundError

    try:
        verify_models(snapshot_download, cache_dir)
    except LocalEntryNotFoundError as error:
        raise SystemExit(
            "Offline verification failed because a model snapshot is missing or "
            "incomplete. Reconnect to the internet and run lessonlingo setup."
        ) from error

    print("Offline verification passed. No Hub network access was used.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the LessonLingo command-line parser."""

    parser = argparse.ArgumentParser(prog="lessonlingo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command, help_text in (
        ("setup", "log in and download all models for offline use"),
        ("verify", "verify all models are available without network access"),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument(
            "--cache-dir",
            type=Path,
            help="use a specific Hugging Face cache directory",
        )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the LessonLingo command line interface."""

    args = build_parser().parse_args(argv)
    if args.command == "setup":
        return run_setup(args.cache_dir)
    return run_verify(args.cache_dir)


if __name__ == "__main__":
    raise SystemExit(main())
