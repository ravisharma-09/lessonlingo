"""One-time model download and offline cache verification."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lessonlingo.translator import MODEL_REPOSITORIES


@dataclass(frozen=True)
class ModelSpec:
    """A model snapshot required for a LessonLingo runtime mode."""

    mode: str
    repository: str
    approximate_size: str


MODELS = (
    ModelSpec("quality", MODEL_REPOSITORIES["quality"], "4.5 GB"),
    ModelSpec("light", MODEL_REPOSITORIES["light"], "1.1 GB"),
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
    """Download safetensors snapshots for all runtime modes."""

    for model in MODELS:
        print(f"Downloading {model.mode} model ({model.approximate_size}): {model.repository}")
        snapshot_download(
            repo_id=model.repository,
            cache_dir=str(cache_dir) if cache_dir else None,
            ignore_patterns=["*.bin"],
        )


def verify_models(
    snapshot_download: SnapshotDownload,
    cache_dir: Path | None = None,
) -> None:
    """Verify all required snapshots using only the local cache."""

    for model in MODELS:
        snapshot_download(
            repo_id=model.repository,
            cache_dir=str(cache_dir) if cache_dir else None,
            ignore_patterns=["*.bin"],
            local_files_only=True,
        )
        print(f"Found {model.mode} model in the local cache.")


def download_whisper(
    snapshot_download: SnapshotDownload,
    cache_dir: Path | None = None,
    local_only: bool = False,
) -> None:
    """Download (or verify in the local cache) the public speech model for video."""

    from lessonlingo.video import DEFAULT_WHISPER_SIZE, whisper_repository

    snapshot_download(
        repo_id=whisper_repository(DEFAULT_WHISPER_SIZE),
        cache_dir=str(cache_dir) if cache_dir else None,
        local_files_only=local_only,
    )


def run_setup(cache_dir: Path | None = None) -> int:
    """Authenticate when needed and download all required models once."""

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
            "Model access was denied (gated model or HTTP 401). Run `hf auth "
            "login`, accept both model agreements, then run `lessonlingo setup` "
            f"again:\n{repositories}"
        ) from error

    print("Downloading speech model for lecture videos (about 0.5 GB)")
    download_whisper(snapshot_download, cache_dir)
    print("Setup complete. Models and dependencies are now available on this device.")
    print("After setup, translating lessons needs no internet connection.")
    return 0


def run_verify(cache_dir: Path | None = None) -> int:
    """Check the local cache while Hub network access is disabled."""

    enable_offline_mode()
    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import LocalEntryNotFoundError

    try:
        verify_models(snapshot_download, cache_dir)
        download_whisper(snapshot_download, cache_dir, local_only=True)
        print("Found speech model in the local cache.")
    except LocalEntryNotFoundError as error:
        raise SystemExit(
            "Offline verification failed because a model snapshot is missing or "
            "incomplete. Reconnect and run `lessonlingo setup`."
        ) from error

    print("Offline verification passed. No Hugging Face network access was used.")
    return 0
