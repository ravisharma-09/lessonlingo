from pathlib import Path

import pytest

from lessonlingo.pipeline import translate_file, translate_text
from lessonlingo.translator import FakeTranslator


class RecordingFakeTranslator(FakeTranslator):
    """Fake translator that records batches for cache assertions."""

    def __init__(self) -> None:
        """Create an empty call log."""

        self.calls: list[tuple[list[str], str]] = []

    def translate(self, sentences: list[str], tgt_lang: str) -> list[str]:
        """Record the call before applying deterministic fake translation."""

        self.calls.append((sentences, tgt_lang))
        return super().translate(sentences, tgt_lang)


def test_translate_text_caches_duplicate_sentences_per_language() -> None:
    """Repeated source sentences are sent to the backend once per target."""

    translator = RecordingFakeTranslator()

    translated = translate_text(
        "Repeat. Repeat.",
        ["hin_Deva", "kan_Knda"],
        "light",
        translator=translator,
    )

    assert translator.calls == [
        (["Repeat."], "hin_Deva"),
        (["Repeat."], "kan_Knda"),
    ]
    assert translated["hin_Deva"] == "[hin_Deva] Repeat. [hin_Deva] Repeat."
    assert translated["kan_Knda"] == "[kan_Knda] Repeat. [kan_Knda] Repeat."


def test_translate_text_reports_progress() -> None:
    """The pipeline reports completion once for each target language."""

    updates: list[tuple[int, int, str]] = []

    translate_text(
        "Hello.",
        ["hin_Deva", "tam_Taml"],
        "light",
        translator=FakeTranslator(),
        progress_cb=lambda completed, total, target: updates.append(
            (completed, total, target)
        ),
    )

    assert updates == [(1, 2, "hin_Deva"), (2, 2, "tam_Taml")]


def test_translate_file_writes_one_markdown_file_per_target(tmp_path: Path) -> None:
    """File translation uses stable names and preserves protected Markdown."""

    lesson = tmp_path / "lesson.txt"
    lesson.write_text("# Hello\n\nUse `x = 1`.\n", encoding="utf-8")

    paths = translate_file(
        lesson,
        ["hin_Deva", "kan_Knda"],
        "light",
        tmp_path / "outputs",
        translator=FakeTranslator(),
    )

    assert [path.name for path in paths] == [
        "lesson.hin_Deva.md",
        "lesson.kan_Knda.md",
    ]
    assert paths[0].read_text(encoding="utf-8") == (
        "# [hin_Deva] Hello\n\n[hin_Deva] Use `x = 1`.\n"
    )


def test_translate_file_rejects_missing_or_unsupported_input(tmp_path: Path) -> None:
    """Input errors are reported before a model can be loaded."""

    with pytest.raises(FileNotFoundError, match="not found"):
        translate_file(
            tmp_path / "missing.md",
            ["hin_Deva"],
            "light",
            tmp_path,
            translator=FakeTranslator(),
        )

    unsupported = tmp_path / "lesson.pdf"
    unsupported.write_text("not really a PDF", encoding="utf-8")
    with pytest.raises(ValueError, match="Markdown"):
        translate_file(
            unsupported,
            ["hin_Deva"],
            "light",
            tmp_path,
            translator=FakeTranslator(),
        )
