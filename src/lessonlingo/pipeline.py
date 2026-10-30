"""File and text translation orchestration."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from lessonlingo.languages import validate_targets
from lessonlingo.markdown_io import Segment, rebuild, split_markdown
from lessonlingo.translator import IndicTransTranslator, Mode, Translator

ProgressCallback = Callable[[int, int, str], None]


def translate_segments(
    text: str,
    target: str,
    translator: Translator,
    cache: dict[tuple[str, str], str] | None = None,
) -> tuple[list[Segment], list[str]]:
    """Translate one language; return the segments and one translation per translatable one."""

    cache = {} if cache is None else cache
    segments = split_markdown(text)
    source_sentences = [segment.text for segment in segments if segment.translatable]
    missing = list(
        dict.fromkeys(sentence for sentence in source_sentences if (target, sentence) not in cache)
    )
    if missing:
        outputs = translator.translate(missing, target)
        if len(outputs) != len(missing):
            raise RuntimeError("The translator returned an unexpected output count.")
        cache.update(
            ((target, sentence), output) for sentence, output in zip(missing, outputs, strict=True)
        )
    return segments, [cache[(target, sentence)] for sentence in source_sentences]


def _translate_for_target(
    text: str,
    target: str,
    translator: Translator,
    cache: dict[tuple[str, str], str],
) -> str:
    segments, translations = translate_segments(text, target, translator, cache)
    return rebuild(segments, translations)


def translate_text(
    text: str,
    targets: list[str],
    mode: Mode,
    translator: Translator | None = None,
    progress_cb: ProgressCallback | None = None,
) -> dict[str, str]:
    """Translate Markdown or plain text into every requested target language."""

    selected_targets = validate_targets(targets)
    backend = translator or IndicTransTranslator(mode)
    owns_backend = translator is None
    cache: dict[tuple[str, str], str] = {}
    results: dict[str, str] = {}

    try:
        for completed, target in enumerate(selected_targets, start=1):
            results[target] = _translate_for_target(text, target, backend, cache)
            if progress_cb is not None:
                progress_cb(completed, len(selected_targets), target)
    finally:
        if owns_backend:
            backend.close()

    return results


def translate_file(
    path: Path,
    targets: list[str],
    mode: Mode,
    out_dir: Path,
    translator: Translator | None = None,
    progress_cb: ProgressCallback | None = None,
) -> list[Path]:
    """Translate a UTF-8 Markdown or text file and write one Markdown file per target."""

    input_path = Path(path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Lesson file not found: {input_path}")
    if input_path.suffix.lower() not in {".md", ".markdown", ".txt"}:
        raise ValueError("Lesson input must be a Markdown (.md) or text (.txt) file.")

    translated = translate_text(
        input_path.read_text(encoding="utf-8"),
        targets,
        mode,
        translator=translator,
        progress_cb=progress_cb,
    )
    output_directory = Path(out_dir)
    output_directory.mkdir(parents=True, exist_ok=True)

    output_paths: list[Path] = []
    for target, document in translated.items():
        output_path = output_directory / f"{input_path.stem}.{target}.md"
        output_path.write_text(document, encoding="utf-8")
        output_paths.append(output_path)
    return output_paths
