from pathlib import Path

import pytest

from lessonlingo import cli
from lessonlingo.app import ModelHolder, read_source, run_translation
from lessonlingo.translator import FakeTranslator


def test_run_translation_writes_one_file_per_language(tmp_path: Path) -> None:
    paths, preview = run_translation(
        "# Hi\n\nHello world.", None, ["hin_Deva", "kan_Knda"], "light", FakeTranslator(), tmp_path
    )

    assert [Path(p).name for p in paths] == ["lesson.hin_Deva.md", "lesson.kan_Knda.md"]
    assert "[hin_Deva] Hello world." in Path(paths[0]).read_text(encoding="utf-8")
    assert "Hindi (hin_Deva)" in preview


def test_upload_wins_over_pasted_text(tmp_path: Path) -> None:
    upload = tmp_path / "unit1.md"
    upload.write_text("From file.", encoding="utf-8")

    assert read_source("pasted", str(upload)) == ("From file.", "unit1")


def test_empty_input_and_bad_extension_are_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "lesson.pdf"
    bad.write_text("x")

    with pytest.raises(ValueError):
        read_source("  ", None)
    with pytest.raises(ValueError):
        read_source(None, str(bad))


def test_model_holder_closes_previous_mode() -> None:
    created: list[FakeTranslator] = []
    closed: list[int] = []

    class Tracked(FakeTranslator):
        def close(self) -> None:
            closed.append(len(created))

    def factory(mode: str) -> FakeTranslator:
        created.append(Tracked())
        return created[-1]

    holder = ModelHolder(factory)
    first = holder.get("light")
    assert holder.get("light") is first
    holder.get("quality")

    assert len(created) == 2 and closed == [1]


def test_build_app_creates_blocks() -> None:
    pytest.importorskip("gradio")
    from lessonlingo.app import build_app

    assert build_app(ModelHolder(lambda mode: FakeTranslator())) is not None


def test_offline_env_var_enables_offline_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.setenv("LESSONLINGO_OFFLINE", "1")
    lesson = tmp_path / "a.md"
    lesson.write_text("Hello.", encoding="utf-8")

    cli.main(
        ["translate", str(lesson), "--to", "hin_Deva", "--out", str(tmp_path)], FakeTranslator()
    )

    import os

    assert os.environ["HF_HUB_OFFLINE"] == "1"
