"""Gradio web interface for LessonLingo.

Set up once, then no internet needed: the app only uses models that
`lessonlingo setup` already downloaded.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lessonlingo.glossary import GlossaryTranslator, parse_terms
from lessonlingo.languages import SUPPORTED_LANGUAGES, validate_targets
from lessonlingo.markdown_io import Segment, rebuild
from lessonlingo.pipeline import translate_segments
from lessonlingo.translator import IndicTransTranslator, Mode, Translator
from lessonlingo.video import FasterWhisperTranscriber, Transcriber, translate_video

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


ReviewDocs = dict[str, tuple[list[Segment], list[str]]]


def run_translation(
    text: str | None,
    upload_path: str | None,
    targets: list[str],
    mode: Mode,
    translator: Translator,
    out_dir: Path | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> tuple[list[str], str, ReviewDocs]:
    """Translate the lesson; return (file paths, preview text, per-language review data)."""

    source, stem = read_source(text, upload_path)
    selected = validate_targets(targets)
    cache: dict[tuple[str, str], str] = {}
    docs: ReviewDocs = {}
    for done, code in enumerate(selected, start=1):
        docs[code] = translate_segments(source, code, translator, cache)
        if progress_cb is not None:
            progress_cb(done, len(selected), code)

    folder = out_dir or Path(tempfile.mkdtemp(prefix="lessonlingo_"))
    folder.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    preview: list[str] = []
    for code, (segments, translations) in docs.items():
        document = rebuild(segments, translations)
        path = folder / f"{stem}.{code}.md"
        path.write_text(document, encoding="utf-8")
        paths.append(str(path))
        preview.append(f"===== {SUPPORTED_LANGUAGES[code]} ({code}) =====\n{document}")
    return paths, "\n\n".join(preview), docs


def review_rows(segments: list[Segment], translations: list[str]) -> list[list[str]]:
    """Rows of [English, translation], one per translated sentence, for the review table."""

    sources = [segment.text for segment in segments if segment.translatable]
    return [[source, target] for source, target in zip(sources, translations, strict=True)]


def save_review(
    segments: list[Segment],
    rows: list[list[str]],
    stem: str,
    code: str,
    out_dir: Path | None = None,
) -> str:
    """Rebuild the document from the (possibly edited) translation column and save it."""

    document = rebuild(segments, [str(row[1]) for row in rows])
    folder = out_dir or Path(tempfile.mkdtemp(prefix="lessonlingo_edit_"))
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stem}.{code}.md"
    path.write_text(document, encoding="utf-8")
    return str(path)


def run_video_job(
    upload_path: str | None,
    targets: list[str],
    mode: Mode,
    translator: Translator,
    transcriber: Transcriber,
    out_dir: Path | None = None,
    status: Callable[[str], None] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Translate a lecture; return (all subtitle files, {language code: .vtt path})."""

    if not upload_path:
        raise ValueError("Upload a lecture video (or a .srt file) first.")
    folder = out_dir or Path(tempfile.mkdtemp(prefix="lessonlingo_video_"))
    written = translate_video(
        Path(upload_path),
        targets,
        mode,
        folder,
        transcriber=transcriber,
        translator=translator,
        status=status,
    )
    vtt = {p.name.split(".")[-2]: str(p) for p in written if p.suffix == ".vtt"}
    return [str(p) for p in written], vtt


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


def build_app(
    holder: ModelHolder | None = None,
    transcriber_factory: Callable[[], Transcriber] = FasterWhisperTranscriber,
) -> Any:
    """Build the Gradio Blocks app. Pass a holder with FakeTranslator for tests."""

    import gradio as gr

    models = holder or ModelHolder()

    def with_glossary(translator: Translator, keep: str | None) -> Translator:
        terms = parse_terms(keep)
        return GlossaryTranslator(translator, terms) if terms else translator

    def on_translate(
        text: str,
        upload: str | None,
        targets: list[str],
        mode: Mode,
        keep: str,
        progress: Any = None,
    ) -> tuple[Any, ...]:
        if not targets:
            raise gr.Error("Pick at least one language.")
        progress = progress or gr.Progress()

        def report(done: int, total: int, code: str) -> None:
            progress(done / total, desc=f"Translated {SUPPORTED_LANGUAGES[code]} ({done}/{total})")

        progress(0, desc="Loading the model (first run takes a little while)...")
        try:
            paths, preview, docs = run_translation(
                text,
                upload,
                targets,
                mode,
                with_glossary(models.get(mode), keep),
                progress_cb=report,
            )
            stem = read_source(text, upload)[1]
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            raise gr.Error(str(error)) from error
        first = next(iter(docs))
        review = {"stem": stem, "docs": docs}
        return (
            f"Done. {len(paths)} file(s) ready. Check each line below, fix any, then save.",
            paths,
            preview,
            review,
            gr.Dropdown(
                choices=[(SUPPORTED_LANGUAGES[c], c) for c in docs], value=first, visible=True
            ),
            gr.Dataframe(value=review_rows(*docs[first]), visible=True),
            gr.Button(visible=True),
        )

    def on_review_language(review: dict[str, Any], code: str) -> Any:
        if not review or code not in review["docs"]:
            return gr.Dataframe()
        return gr.Dataframe(value=review_rows(*review["docs"][code]), visible=True)

    def on_save_review(review: dict[str, Any], code: str, rows: Any) -> str:
        if not review or code not in review["docs"]:
            raise gr.Error("Translate a lesson first.")
        table = rows.values.tolist() if hasattr(rows, "values") else rows
        return save_review(review["docs"][code][0], table, review["stem"], code)

    language_choices = [(f"{name} ({code})", code) for code, name in SUPPORTED_LANGUAGES.items()]

    def on_video(
        upload: str | None, targets: list[str], mode: Mode, keep: str, progress: Any = None
    ) -> tuple[Any, ...]:
        if not targets:
            raise gr.Error("Pick at least one language.")
        progress = progress or gr.Progress()
        models.close()  # free the GPU before the speech model loads
        try:
            files, vtt = run_video_job(
                upload,
                targets,
                mode,
                with_glossary(models.get(mode), keep),
                transcriber_factory(),
                status=lambda message: progress(None, desc=message),
            )
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            raise gr.Error(str(error)) from error
        first = next(iter(vtt))
        return (
            f"Done. {len(files)} subtitle files ready.",
            files,
            vtt,
            gr.Dropdown(
                choices=[(SUPPORTED_LANGUAGES[c], c) for c in vtt], value=first, visible=True
            ),
            gr.Video(value=upload, subtitles=vtt[first])
            if not str(upload).endswith((".srt", ".vtt"))
            else gr.Video(),
        )

    def on_language(upload: str | None, vtt: dict[str, str], code: str) -> Any:
        if not upload or code not in vtt or str(upload).endswith((".srt", ".vtt")):
            return gr.Video()
        return gr.Video(value=upload, subtitles=vtt[code])

    with gr.Blocks(title="LessonLingo") as app:
        gr.Markdown("# LessonLingo", elem_id="title")
        gr.Markdown(
            "Free lectures in your language. Set up once, then no internet needed.",
            elem_id="subtitle",
        )
        with gr.Tab("Lecture video"):
            v_upload = gr.File(
                label="1. Add an English lecture (video, audio, or a .srt file)",
                file_types=[
                    ".mp4",
                    ".mkv",
                    ".mov",
                    ".webm",
                    ".mp3",
                    ".wav",
                    ".m4a",
                    ".srt",
                    ".vtt",
                ],
                type="filepath",
            )
            v_targets = gr.CheckboxGroup(
                label="2. Pick languages", choices=language_choices, value=["kan_Knda", "hin_Deva"]
            )
            v_mode = gr.Radio(label="3. How should it run?", choices=MODE_CHOICES, value="light")
            v_keep = gr.Textbox(
                label="Keep these words in English (optional, separated by commas)",
                placeholder="photosynthesis, Python",
            )
            v_go = gr.Button("Translate lecture", variant="primary", size="lg")
            v_status = gr.Markdown()
            v_state = gr.State({})
            v_lang = gr.Dropdown(label="Watch with subtitles in", choices=[], visible=False)
            v_player = gr.Video(label="Lecture", interactive=False)
            v_files = gr.File(
                label="Download subtitle files (.srt and .vtt)", file_count="multiple"
            )
            v_go.click(
                on_video,
                [v_upload, v_targets, v_mode, v_keep],
                [v_status, v_files, v_state, v_lang, v_player],
            )
            v_lang.change(on_language, [v_upload, v_state, v_lang], v_player)

        with gr.Tab("Text lesson"):
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
                label="2. Pick languages", choices=language_choices, value=["hin_Deva", "kan_Knda"]
            )
            mode = gr.Radio(label="3. How should it run?", choices=MODE_CHOICES, value="light")
            keep = gr.Textbox(
                label="Keep these words in English (optional, separated by commas)",
                placeholder="photosynthesis, Python",
            )
            go = gr.Button("Translate lesson", variant="primary", size="lg", elem_id="go")
            status = gr.Markdown()
            files = gr.File(label="Download one file per language", file_count="multiple")
            review_state = gr.State({})
            review_lang = gr.Dropdown(label="Review language", choices=[], visible=False)
            review_table = gr.Dataframe(
                headers=["English", "Translation (click a cell to edit)"],
                datatype=["str", "str"],
                static_columns=[0],
                interactive=True,
                wrap=True,
                visible=False,
                type="array",
            )
            save_btn = gr.Button("Save my edits", visible=False)
            edited = gr.File(label="Your edited file")
            preview = gr.Textbox(label="Preview", lines=12, interactive=False)
            go.click(
                on_translate,
                [text, upload, targets, mode, keep],
                [status, files, preview, review_state, review_lang, review_table, save_btn],
            )
            review_lang.change(on_review_language, [review_state, review_lang], review_table)
            save_btn.click(on_save_review, [review_state, review_lang, review_table], edited)
        gr.Markdown(NOTE)
    return app


def launch(port: int = 7860, share: bool = False) -> None:
    """Start the web interface on this computer."""

    app = build_app()
    app.launch(server_port=port, share=share, theme=make_theme(), css=GREEN_CSS)
