from pathlib import Path
from typing import Any

import huggingface_hub

from lessonlingo import cli


def test_download_models_fetches_both_safetensors_snapshots() -> None:
    calls: list[dict[str, object]] = []

    def fake_snapshot_download(**kwargs: Any) -> str:
        calls.append(kwargs)
        return "/fake/model"

    cli.download_models(fake_snapshot_download, Path("models"))

    assert [call["repo_id"] for call in calls] == [
        "ai4bharat/indictrans2-en-indic-1B",
        "ai4bharat/indictrans2-en-indic-dist-200M",
    ]
    assert all(call["cache_dir"] == "models" for call in calls)
    assert all(call["ignore_patterns"] == ["*.bin"] for call in calls)


def test_verify_models_uses_local_files_only() -> None:
    calls: list[dict[str, object]] = []

    def fake_snapshot_download(**kwargs: Any) -> str:
        calls.append(kwargs)
        return "/fake/model"

    cli.verify_models(fake_snapshot_download)

    assert len(calls) == 2
    assert all(call["local_files_only"] is True for call in calls)


def test_enable_offline_mode_sets_library_guards(monkeypatch: Any) -> None:
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)

    cli.enable_offline_mode()

    assert cli.os.environ["HF_HUB_OFFLINE"] == "1"
    assert cli.os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_online_setup_clears_offline_guards(monkeypatch: Any) -> None:
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    cli.enable_online_setup()

    assert "HF_HUB_OFFLINE" not in cli.os.environ
    assert "TRANSFORMERS_OFFLINE" not in cli.os.environ


def test_setup_logs_in_and_downloads_all_models(monkeypatch: Any) -> None:
    login_calls: list[bool] = []
    download_calls: list[dict[str, object]] = []

    monkeypatch.setattr(huggingface_hub, "get_token", lambda: None)
    monkeypatch.setattr(huggingface_hub, "login", lambda: login_calls.append(True))
    monkeypatch.setattr(
        huggingface_hub,
        "snapshot_download",
        lambda **kwargs: download_calls.append(kwargs) or "/fake/model",
    )

    assert cli.run_setup() == 0
    assert login_calls == [True]
    assert len(download_calls) == 2
