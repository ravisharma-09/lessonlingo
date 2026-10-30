from pathlib import Path
from typing import Any

import pytest

from lessonlingo import cli, setup_models
from lessonlingo.translator import FakeTranslator


def test_download_models_fetches_both_safetensors_snapshots() -> None:
    calls: list[dict[str, object]] = []

    def fake_snapshot_download(**kwargs: Any) -> str:
        calls.append(kwargs)
        return "/fake/model"

    setup_models.download_models(fake_snapshot_download, Path("models"))

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

    setup_models.verify_models(fake_snapshot_download)

    assert len(calls) == 2
    assert all(call["local_files_only"] is True for call in calls)


def test_enable_offline_mode_sets_library_guards(monkeypatch: Any) -> None:
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)

    setup_models.enable_offline_mode()

    assert setup_models.os.environ["HF_HUB_OFFLINE"] == "1"
    assert setup_models.os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_online_setup_clears_offline_guards(monkeypatch: Any) -> None:
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    setup_models.enable_online_setup()

    assert "HF_HUB_OFFLINE" not in setup_models.os.environ
    assert "TRANSFORMERS_OFFLINE" not in setup_models.os.environ


def test_cli_help_uses_approved_offline_wording(capsys: Any) -> None:
    """Public CLI copy describes the required one-time setup."""

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])

    assert exit_info.value.code == 0
    assert "Set up once, then no internet needed" in capsys.readouterr().out


def test_languages_command_lists_codes_and_names(capsys: Any) -> None:
    """Users can discover every supported CLI language code."""

    assert cli.main(["languages"]) == 0

    output = capsys.readouterr().out
    assert "hin_Deva\tHindi" in output
    assert "ory_Orya\tOdia" in output


def test_translate_command_writes_outputs_with_fake_backend(
    tmp_path: Path,
    capsys: Any,
) -> None:
    """The complete CLI flow works on the Mac without importing model code."""

    lesson = tmp_path / "lesson.md"
    lesson.write_text("# Hello\n", encoding="utf-8")
    output_dir = tmp_path / "translated"

    result = cli.main(
        [
            "translate",
            str(lesson),
            "--to",
            "hin_Deva",
            "kan_Knda",
            "--mode",
            "light",
            "--out",
            str(output_dir),
        ],
        translator=FakeTranslator(),
    )

    assert result == 0
    assert (output_dir / "lesson.hin_Deva.md").read_text(encoding="utf-8") == (
        "# [hin_Deva] Hello\n"
    )
    output = capsys.readouterr().out
    assert "Translated hin_Deva (1/2)" in output
    assert "lesson.kan_Knda.md" in output


def test_translate_command_reports_missing_file(capsys: Any) -> None:
    """CLI input failures are concise and do not trigger model loading."""

    with pytest.raises(SystemExit) as exit_info:
        cli.main(
            ["translate", "missing.md", "--to", "hin_Deva"],
            translator=FakeTranslator(),
        )

    assert exit_info.value.code == 2
    assert "Lesson file not found" in capsys.readouterr().err


def test_video_command_translates_an_srt_file(tmp_path: Path) -> None:
    lecture = tmp_path / "talk.srt"
    lecture.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello class.\n", encoding="utf-8")

    code = cli.main(
        ["video", str(lecture), "--to", "hin_Deva", "--out", str(tmp_path / "o")],
        FakeTranslator(),
    )

    assert code == 0
    assert "[hin_Deva] Hello class." in (tmp_path / "o" / "talk.hin_Deva.srt").read_text(
        encoding="utf-8"
    )


def test_download_whisper_uses_public_repo_and_local_flag() -> None:
    calls: list[dict[str, object]] = []

    setup_models.download_whisper(lambda **kw: calls.append(kw) or "x", None, local_only=True)

    assert calls[0]["repo_id"] == "Systran/faster-whisper-small"
    assert calls[0]["local_files_only"] is True


def test_keep_flag_protects_terms_in_translation(tmp_path: Path) -> None:
    lesson = tmp_path / "a.md"
    lesson.write_text("Learn Python today.", encoding="utf-8")

    cli.main(
        ["translate", str(lesson), "--to", "hin_Deva", "--keep", "Python", "--out", str(tmp_path)],
        FakeTranslator(),
    )

    assert "Python" in (tmp_path / "a.hin_Deva.md").read_text(encoding="utf-8")


def test_glossary_file_and_zip_flags(tmp_path: Path) -> None:
    import zipfile

    lesson = tmp_path / "unit.md"
    lesson.write_text("Apply a force today.", encoding="utf-8")
    sheet = tmp_path / "course.csv"
    sheet.write_text("term,hin_Deva\nforce,बल\n", encoding="utf-8")

    cli.main(
        [
            "translate",
            str(lesson),
            "--to",
            "hin_Deva",
            "--glossary",
            str(sheet),
            "--zip",
            "--out",
            str(tmp_path / "o"),
        ],
        FakeTranslator(),
    )

    assert "बल" in (tmp_path / "o" / "unit.hin_Deva.md").read_text(encoding="utf-8")
    assert "START_HERE.txt" in zipfile.ZipFile(tmp_path / "o" / "unit.classpack.zip").namelist()
