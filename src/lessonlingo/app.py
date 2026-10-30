"""Gradio web interface for LessonLingo.

Set up once, then no internet needed: the app only uses models that
`lessonlingo setup` already downloaded.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lessonlingo.languages import SUPPORTED_LANGUAGES
from lessonlingo.pipeline import translate_text
from lessonlingo.translator import IndicTransTranslator, Mode, Translator

DEFAULT_TEXT = (
    "# Water Cycle\n\n"
    "Water moves continuously between the land, oceans, and atmosphere.\n\n"
    "1. Evaporation turns liquid water into water vapour.\n"
    "2. Condensation forms clouds.\n"
    "3. Precipitation returns water to Earth.\n"
)

MODE_CHOICES: list[tuple[str, str]] = [
    ("Quick and light (works on any laptop)", "light"),
    ("Best quality (needs an NVIDIA graphics card)", "quality"),
]

NOTE = (
    "**Set up once, then no internet needed.** Models are downloaded one time with "
    "`lessonlingo setup`. After that, translating lessons needs no internet connection. "
    "Machine translation can be wrong, so ask a speaker to check important material."
)

GREEN_CSS = """
.gradio-container { max-width: 880px !important; margin: 0 auto !important; }
#title h1 { color: #166534; font-size: 2rem; margin-bottom: 0; }
#subtitle { color: #4b5563; margin-top: 4px; }
#go button, button#go { font-size: 1.1rem; padding: 14px; }
"""


def make_theme() -> Any:
    """Return the clean green Gradio theme."""

    import gradio as gr

    return gr.themes.Soft(
        primary_hue="green",
        neutral_hue="slate",
        radius_size="lg",
        font=[gr.themes.GoogleFont("Nunito"), "system-ui", "sans-serif"],
    )


def read_source(text: str | None, upload_path: str | None) -> tuple[str, str]:
    """Return (lesson text, file stem). An uploaded file wins over pasted text."""

    if upload_path:
        path = Path(upload_path)
        if path.suffix.lower() not in {".md", ".markdown", ".txt"}:
            raise ValueError("Upload a Markdown (.md) or text (.txt) file.")
        return path.read_text(encoding="utf-8"), path.stem
    if text and text.strip():
        return text, "lesson"
    raise ValueError("Paste a lesson or upload a .md or .txt file first.")


def run_translation(
    text: str | None,
    upload_path: str | None,
    targets: list[str],
    mode: Mode,
    translator: Translator,
    out_dir: Path | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> tuple[list[str], str]:
    """Translate the lesson; return (written file paths, preview text)."""

    source, stem = read_source(text, upload_path)
    results = translate_text(source, targets, mode, translator=translator, progress_cb=progress_cb)
    folder = out_dir or Path(tempfile.mkdtemp(prefix="lessonlingo_"))
    folder.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    preview: list[str] = []
    for code, document in results.items():
        path = folder / f"{stem}.{code}.md"
        path.write_text(document, encoding="utf-8")
        paths.append(str(path))
        preview.append(f"===== {SUPPORTED_LANGUAGES[code]} ({code}) =====\n{document}")
    return paths, "\n\n".join(preview)


class ModelHolder:
    """Keeps one real translator alive and frees it when the mode changes."""

    def __init__(self, factory: Callable[[Mode], Translator] = IndicTransTranslator) -> None:
        """Create an empty holder; models load on first use."""

        self._factory = factory
        self._mode: Mode | None = None
        self._translator: Translator | None = None

    def get(self, mode: Mode) -> Translator:
        """Return a translator for the mode, closing the previous one first."""

        if self._translator is None or self._mode != mode:
            if self._translator is not None:
                self._translator.close()
            self._translator = self._factory(mode)
            self._mode = mode
        return self._translator

    def close(self) -> None:
        """Free model memory."""

        if self._translator is not None:
            self._translator.close()
        self._translator = None
        self._mode = None


def build_app(holder: ModelHolder | None = None) -> Any:
    """Build the Gradio Blocks app. Pass a holder with FakeTranslator for tests."""

    import gradio as gr

    models = holder or ModelHolder()

    def on_translate(
        text: str,
        upload: str | None,
        targets: list[str],
        mode: Mode,
        progress: Any = None,
    ) -> tuple[str, list[str], str]:
        if not targets:
            raise gr.Error("Pick at least one language.")
        progress = progress or gr.Progress()

        def report(done: int, total: int, code: str) -> None:
            progress(done / total, desc=f"Translated {SUPPORTED_LANGUAGES[code]} ({done}/{total})")

        progress(0, desc="Loading the model (first run takes a little while)...")
        try:
            paths, preview = run_translation(
                text, upload, targets, mode, models.get(mode), progress_cb=report
            )
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            raise gr.Error(str(error)) from error
        return f"Done. {len(paths)} file(s) ready to download.", paths, preview

    with gr.Blocks(title="LessonLingo") as app:
        gr.Markdown("# LessonLingo", elem_id="title")
        gr.Markdown(
            "Free lessons in your language. Set up once, then no internet needed.",
            elem_id="subtitle",
        )
        with gr.Group():
            text = gr.Textbox(
                label="1. Paste your lesson",
                value=DEFAULT_TEXT,
                lines=9,
                placeholder="Paste English lesson text here",
            )
            upload = gr.File(
                label="or upload a .md or .txt file",
                file_types=[".md", ".markdown", ".txt"],
                type="filepath",
            )
        targets = gr.CheckboxGroup(
            label="2. Pick languages",
            choices=[(f"{name} ({code})", code) for code, name in SUPPORTED_LANGUAGES.items()],
            value=["hin_Deva", "kan_Knda"],
        )
        mode = gr.Radio(label="3. How should it run?", choices=MODE_CHOICES, value="light")
        go = gr.Button("Translate lesson", variant="primary", size="lg", elem_id="go")
        status = gr.Markdown()
        files = gr.File(label="Download one file per language", file_count="multiple")
        preview = gr.Textbox(label="Preview", lines=12, interactive=False)
        gr.Markdown(NOTE)
        go.click(on_translate, [text, upload, targets, mode], [status, files, preview])
    return app


def launch(port: int = 7860, share: bool = False) -> None:
    """Start the web interface on this computer."""

    app = build_app()
    app.launch(server_port=port, share=share, theme=make_theme(), css=GREEN_CSS)
