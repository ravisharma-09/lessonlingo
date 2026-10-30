"""Gradio web interface for LessonLingo.

Set up once, then no internet needed: the app only uses models that
`lessonlingo setup` already downloaded.
"""

from __future__ import annotations

import base64
import os
import socket
import tempfile
import threading
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import quote

from lessonlingo.glossary import GlossaryTranslator, load_glossary, parse_terms
from lessonlingo.languages import NATIVE_NAMES, SUPPORTED_LANGUAGES, validate_targets
from lessonlingo.library import build_library_tab
from lessonlingo.markdown_io import Segment, rebuild
from lessonlingo.pack import make_class_pack
from lessonlingo.pipeline import translate_segments
from lessonlingo.subtitles import Cue, format_timestamp
from lessonlingo.translator import IndicTransTranslator, Mode, Translator
from lessonlingo.tts import MMSSynthesizer, Synthesizer, dub_subtitles
from lessonlingo.ui_assets import HERO_HTML
from lessonlingo.video import (
    FasterWhisperTranscriber,
    Transcriber,
    is_doubtful,
    transcribe_lecture,
    translate_lecture,
    translate_video,
)
from lessonlingo.workspace import Workspace

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

FORCE_LIGHT_JS = """() => {
  const url = new URL(window.location);
  if (url.searchParams.get('__theme') !== 'light') {
    url.searchParams.set('__theme', 'light');
    window.location.href = url.href;
  }
}"""

GREEN_CSS = """
.gradio-container { max-width: 760px !important; margin: 0 auto !important;
  padding-left: 18px !important; padding-right: 18px !important; }
.tabitem, .tab-wrapper { padding-left: 0 !important; padding-right: 0 !important; }
.form { background: transparent !important; border: 0 !important; box-shadow: none !important;
  gap: 0 !important; }
fieldset.block { padding: 0 !important; border: 0 !important; background: transparent !important; }
#hero { display: flex; flex-wrap: wrap; gap: 20px; align-items: center;
  justify-content: space-between; padding: 8px 0 12px; }
#hero .text { flex: 1 1 380px; min-width: 0; }
#hero .eyebrow { font-family: "Space Mono", monospace; font-weight: 700; font-size: 13px;
  letter-spacing: .12em; color: #b45309; }
#hero h1 { margin: 6px 0; font-size: 2.3rem; line-height: 1.1;
  color: var(--body-text-color); letter-spacing: -.02em; }
#hero p { margin: 0; font-size: 1.1rem; color: #3f5648; }
#hero .tile { background: #2d4540; border-radius: 20px; padding: 14px 20px; display: flex;
  gap: 14px; align-items: flex-end; }
#hero .tile svg { image-rendering: pixelated; }
#strip { height: 14px; margin-bottom: 14px; background: repeating-linear-gradient(90deg,
  #8fb4e3 0 28px, #f5b524 28px 56px, #ea7b78 56px 84px, #e2461f 84px 112px); }
.step h3 { margin: 30px 0 2px; font-size: 1.25rem; font-weight: 800; }
.step p { margin: 0 0 6px; color: #3f5648; }
footer { display: none !important; }
.html-container { padding: 0 !important; }
button.upload-container { border: 2px dashed #16803c !important; background: #f1faf4 !important;
  border-radius: 16px !important; color: #0f5a2b !important; min-height: 150px; }
button.upload-container:hover { background: #e8f7ed !important; }

/* Choice buttons: big, clear tiles with a visible selected state. */
[data-testid="checkbox-group"] { display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
[data-testid="checkbox-group"] label, label[data-testid$="-radio-label"] {
  display: flex !important; align-items: center; gap: 10px; min-height: 56px;
  padding: 12px 16px !important; font-size: 1.05rem; cursor: pointer;
  border-radius: 14px !important;
  border: 2px solid #d3e4d9 !important; background: #ffffff !important; box-shadow: none !important;
  color: #12261b !important; }
[data-testid="checkbox-group"] label:hover, label[data-testid$="-radio-label"]:hover {
  border-color: #16803c !important; }
[data-testid="checkbox-group"] label.selected, label[data-testid$="-radio-label"].selected {
  border-color: #16803c !important; background: #e8f7ed !important; color: #0f3d22 !important;
  font-weight: 700; }
[data-testid="checkbox-group"] label.selected::after,
label[data-testid$="-radio-label"].selected::after {
  content: "\\2713"; margin-left: auto; color: #16803c; font-weight: 800; }
[data-testid="checkbox-group"] input, label[data-testid$="-radio-label"] input {
  position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
[data-testid="checkbox-group"] label span,
label[data-testid$="-radio-label"] span { margin: 0 !important; }
div:has(> label[data-testid$="-radio-label"]) { display: grid !important; gap: 10px; }
#go button, button#go { font-size: 1.15rem; padding: 14px; }
video::cue { font-size: 1.3em; background: rgba(0, 0, 0, 0.78); color: #ffffff; }
"""


def make_theme() -> Any:
    """Return the clean green Gradio theme."""

    import gradio as gr

    return gr.themes.Soft(
        primary_hue="green",
        neutral_hue="slate",
        radius_size="lg",
        font=[gr.themes.GoogleFont("Figtree"), "system-ui", "sans-serif"],
    ).set(
        block_border_width="0px",
        block_shadow="none",
        block_background_fill="transparent",
        panel_background_fill="transparent",
        block_label_background_fill="transparent",
        block_label_border_width="0px",
        block_label_shadow="none",
        block_label_text_color="*body_text_color_subdued",
        block_title_text_weight="600",
        input_background_fill="*neutral_100",
        input_border_color="transparent",
        input_shadow="none",
        checkbox_label_shadow="none",
        accordion_text_color="*body_text_color",
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


SAMPLE_LECTURE = Path(__file__).resolve().parents[2] / "samples" / "lecture_en.srt"


def lan_address(port: int) -> str | None:
    """This computer's address on the local network, for students on the same hotspot."""

    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))  # no packet is sent; this only picks a network
        return f"http://{probe.getsockname()[0]}:{port}"
    except OSError:
        return None
    finally:
        probe.close()


def friendly_error(error: Exception) -> str:
    """Turn a raw model or download error into a short message that says what to do."""

    text = str(error)
    lowered = text.lower()
    if "out of memory" in lowered:
        return (
            "The graphics card ran out of memory. Choose 'Quick and light', "
            "close other programs, and try again."
        )
    if "gated" in lowered or "401" in lowered:
        return (
            "The model needs access. While online, accept both model pages on Hugging Face, "
            "run `hf auth login`, then `lessonlingo setup`."
        )
    if "local_files_only" in lowered or "offline" in lowered or "couldn't connect" in lowered:
        return "A model is not downloaded yet. While online, run `lessonlingo setup` once."
    return text


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


def glossary_from(
    keep: str | None, sheet_path: str | None
) -> tuple[list[str], dict[str, dict[str, str]]]:
    """Terms to protect (typed words plus the glossary sheet) and preferred words per language."""

    terms = parse_terms(keep)
    preferred: dict[str, dict[str, str]] = {}
    if sheet_path:
        sheet_terms, preferred = load_glossary(Path(sheet_path))
        terms += sheet_terms
    return list(dict.fromkeys(terms)), preferred


SUBTITLE_LANGUAGE = {
    "hin_Deva": "hi",
    "kan_Knda": "kn",
    "tam_Taml": "ta",
    "tel_Telu": "te",
    "mal_Mlym": "ml",
    "ben_Beng": "bn",
    "mar_Deva": "mr",
    "guj_Gujr": "gu",
    "pan_Guru": "pa",
    "ory_Orya": "or",
}


def _file_url(path: str) -> str:
    """Address Gradio serves a local file at. Windows backslashes become slashes first."""

    return "/gradio_api/file=" + quote(str(path).replace("\\", "/"), safe="/:")


SWITCH_TRACK_JS = """(code) => {
  const apply = (tries) => {
    const video = document.querySelector('#lecture-player video');
    const tracks = video ? video.querySelectorAll('track') : [];
    if (!tracks.length) { if (tries > 0) setTimeout(() => apply(tries - 1), 200); return; }
    tracks.forEach((el) => {
      if (el.track) el.track.mode = el.dataset.code === code ? 'showing' : 'disabled';
    });
  };
  apply(15);
}"""


def _subtitle_data_url(path: str) -> str:
    """The subtitle file as a data address, so the player needs no file path or file route."""

    encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:text/vtt;charset=utf-8;base64,{encoded}"


def player_html(video: str, subtitles: dict[str, str], selected: str) -> str:
    """A standard browser video player with every language as a subtitle track.

    Subtitles are embedded in the page. The chosen language is switched on by default and by
    SWITCH_TRACK_JS; viewers can also pick one in the player's own captions menu.
    """

    tracks = "".join(
        f'<track kind="subtitles" src="{_subtitle_data_url(path)}" data-code="{code}"'
        f' srclang="{SUBTITLE_LANGUAGE.get(code, code)}" label="{SUPPORTED_LANGUAGES[code]}"'
        f"{' default' if code == selected else ''}>"
        for code, path in subtitles.items()
    )
    return (
        f'<video controls preload="metadata" src="{_file_url(video)}" '
        f'style="width:100%;border-radius:14px;background:#000">{tracks}</video>'
    )


def check_note(cue: Cue) -> str:
    """What the Check column shows: the doubtful words, or just "Check" for a doubtful line."""

    if cue.weak_words:
        return "Check: " + ", ".join(cue.weak_words)
    return "Check" if is_doubtful(cue) else ""


def transcript_rows(cues: list[Cue]) -> list[list[str]]:
    """Rows of [time, heard text, "Check" when recognition was unsure] for the review table."""

    return [[format_timestamp(cue.start)[3:8], cue.text, check_note(cue)] for cue in cues]


def cues_from_rows(cues: list[Cue], rows: list[list[str]]) -> list[Cue]:
    """Apply the teacher's corrections to the heard text; timing never changes."""

    if len(rows) != len(cues):
        raise ValueError("Please do not add or delete rows in the transcript. Edit the text only.")
    return [replace(cue, text=str(row[1]).strip() or cue.text) for cue, row in zip(cues, rows)]


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


def default_workspace_root() -> Path:
    """Where courses live: $LESSONLINGO_HOME, else ~/LessonLingo."""

    return Path(os.environ.get("LESSONLINGO_HOME") or Path.home() / "LessonLingo")


def build_app(
    holder: ModelHolder | None = None,
    transcriber_factory: Callable[..., Transcriber] = FasterWhisperTranscriber,
    workspace: Workspace | None = None,
    synthesizer_factory: Callable[[], Synthesizer] = MMSSynthesizer,
) -> Any:
    """Build the Gradio Blocks app. Pass a holder with FakeTranslator for tests."""

    import gradio as gr

    models = holder or ModelHolder()
    courses_home = workspace or Workspace(default_workspace_root())

    def with_glossary(
        translator: Translator, keep: str | None, sheet: str | None = None
    ) -> Translator:
        terms, preferred = glossary_from(keep, sheet)
        return GlossaryTranslator(translator, terms, preferred) if terms else translator

    def on_translate(
        text: str,
        upload: str | None,
        targets: list[str],
        mode: Mode,
        keep: str,
        sheet: str | None,
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
                with_glossary(models.get(mode), keep, sheet),
                progress_cb=report,
            )
            stem = read_source(text, upload)[1]
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            raise gr.Error(friendly_error(error)) from error
        first = next(iter(docs))
        review = {"stem": stem, "docs": docs}
        pack = make_class_pack([Path(p) for p in paths], Path(paths[0]).parent / f"{stem}.zip")
        return (
            f"Done. {len(paths)} file(s) ready. Check each line below, fix any, then save.",
            gr.File(value=[*paths, str(pack)], visible=True),
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

    def on_save_review(review: dict[str, Any], code: str, rows: Any) -> Any:
        if not review or code not in review["docs"]:
            raise gr.Error("Translate a lesson first.")
        table = rows.values.tolist() if hasattr(rows, "values") else rows
        path = save_review(review["docs"][code][0], table, review["stem"], code)
        return gr.File(value=path, visible=True)

    language_choices = [
        (f"{name} · {NATIVE_NAMES[code]}", code) for code, name in SUPPORTED_LANGUAGES.items()
    ]

    def on_listen(
        upload: str | None, keep: str, sheet: str | None, progress: Any = None
    ) -> tuple[Any, ...]:
        if not upload:
            raise gr.Error("Add a lecture video, audio file or .srt first.")
        progress = progress or gr.Progress()
        models.close()  # free the GPU before the speech model loads
        try:
            terms, _ = glossary_from(keep, sheet)
            cues = transcribe_lecture(
                Path(upload),
                transcriber_factory(hotwords=terms),
                status=lambda message: progress(None, desc=message),
            )
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            raise gr.Error(friendly_error(error)) from error
        doubtful = sum(is_doubtful(cue) for cue in cues)
        note = f" {doubtful} line(s) marked Check may be wrong." if doubtful else ""
        return (
            f"Heard {len(cues)} lines.{note} Fix any mistakes in the English, then translate.",
            {"cues": cues},
            gr.Dataframe(value=transcript_rows(cues), visible=True),
            gr.Button(visible=True),
        )

    def on_translate_video(
        upload: str | None,
        heard: dict[str, Any],
        rows: Any,
        targets: list[str],
        mode: Mode,
        keep: str,
        sheet: str | None,
        dub: bool,
        progress: Any = None,
    ) -> tuple[Any, ...]:
        if not targets:
            raise gr.Error("Pick at least one language.")
        if not heard or not upload:
            raise gr.Error("Listen to the lecture first.")
        progress = progress or gr.Progress()
        table = rows.values.tolist() if hasattr(rows, "values") else rows
        try:
            cues = cues_from_rows(heard["cues"], table)
            folder = Path(tempfile.mkdtemp(prefix="lessonlingo_video_"))
            stem = Path(upload).stem
            written = translate_lecture(
                cues,
                stem,
                targets,
                mode,
                folder,
                with_glossary(models.get(mode), keep, sheet),
                status=lambda message: progress(None, desc=message),
            )
            spoken: list[Path] = []
            if dub:
                models.close()  # free the GPU before the voice model loads
                progress(None, desc="Speaking the translation")
                spoken = dub_subtitles(
                    [p for p in written if p.suffix == ".srt"],
                    Path(upload),
                    folder,
                    synthesizer_factory(),
                )
            pack = make_class_pack(
                [*written, *[p for p in spoken if p.suffix == ".wav"]],
                folder / f"{stem}.classpack.zip",
            )
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            raise gr.Error(friendly_error(error)) from error
        vtt = {p.name.split(".")[-2]: str(p) for p in written if p.suffix == ".vtt"}
        wavs = {p.name.split(".")[-2]: str(p) for p in spoken if p.suffix == ".wav"}
        first = next(iter(vtt))
        return (
            f"Done. {len(written) + len(spoken)} files and a class pack are ready. "
            "Subtitles are on in the player; use its CC button to turn them off or change language.",
            gr.File(value=[*map(str, written), *map(str, spoken), str(pack)], visible=True),
            vtt,
            gr.Dropdown(
                choices=[(SUPPORTED_LANGUAGES[c], c) for c in vtt], value=first, visible=True
            ),
            gr.HTML(value=player_html(upload, vtt, first), visible=True)
            if not str(upload).endswith((".srt", ".vtt"))
            else gr.HTML(visible=False),
            wavs,
            gr.Audio(value=wavs[first], visible=True) if first in wavs else gr.Audio(visible=False),
        )

    def on_language_audio(wavs: dict[str, str], code: str) -> Any:
        """Only the voice follows the language here; the browser switches the subtitles itself."""

        if code in wavs:
            return gr.Audio(value=wavs[code], visible=True)
        return gr.Audio(visible=False)

    with gr.Blocks(title="LessonLingo") as app:
        gr.HTML(HERO_HTML, padding=False)
        with gr.Tabs() as tabs:
            with gr.Tab("Translate a lecture", id="lecture"):
                gr.Markdown(
                    "### 1. Add your lecture\nA video, audio or `.srt` file in English.",
                    elem_classes="step",
                )
                v_upload = gr.File(
                    show_label=False,
                    height=170,
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
                gr.Markdown("### 2. Pick the languages", elem_classes="step")
                v_targets = gr.CheckboxGroup(
                    show_label=False,
                    choices=language_choices,
                    value=["kan_Knda", "hin_Deva"],
                )
                gr.Markdown("### 3. Choose how it runs", elem_classes="step")
                v_mode = gr.Radio(show_label=False, choices=MODE_CHOICES, value="light")
                with gr.Accordion("Optional: keep or fix technical words", open=False):
                    v_keep = gr.Textbox(
                        label="Keep these words in English (separated by commas)",
                        placeholder="photosynthesis, Python",
                    )
                    v_sheet = gr.File(
                        label="Course glossary (.csv: term, then the exact word per language)",
                        file_types=[".csv"],
                        type="filepath",
                    )
                if SAMPLE_LECTURE.is_file():
                    v_sample = gr.Button("Try the sample lecture (no video needed)", size="sm")
                    v_sample.click(lambda: str(SAMPLE_LECTURE), None, v_upload)
                v_dub = gr.Checkbox(
                    label="Also speak the translation (optional, non-commercial voices; run "
                    "`lessonlingo setup --voices` first)",
                    value=False,
                )
                v_listen = gr.Button("1. Listen to the lecture", variant="primary", size="lg")
                v_status = gr.Markdown()
                v_heard = gr.State({})
                v_table = gr.Dataframe(
                    headers=["Time", "Heard (click a cell to fix mistakes)", "Check"],
                    datatype=["str", "str", "str"],
                    static_columns=[0, 2],
                    interactive=True,
                    wrap=True,
                    visible=False,
                    type="array",
                )
                v_go = gr.Button("2. Translate", variant="primary", size="lg", visible=False)
                v_state = gr.State({})
                v_wavs = gr.State({})
                v_lang = gr.Dropdown(label="Watch with subtitles in", choices=[], visible=False)
                v_player = gr.HTML(visible=False, padding=False, elem_id="lecture-player")
                v_audio = gr.Audio(label="Hear the translation", visible=False)
                v_files = gr.File(
                    label="Download subtitles (.srt, .vtt) and the class pack (.zip)",
                    file_count="multiple",
                    visible=False,
                )
                v_listen.click(
                    on_listen,
                    [v_upload, v_keep, v_sheet],
                    [v_status, v_heard, v_table, v_go],
                )
                v_go.click(
                    on_translate_video,
                    [v_upload, v_heard, v_table, v_targets, v_mode, v_keep, v_sheet, v_dub],
                    [v_status, v_files, v_state, v_lang, v_player, v_wavs, v_audio],
                ).then(None, v_lang, None, js=SWITCH_TRACK_JS)
                v_lang.change(on_language_audio, [v_wavs, v_lang], v_audio)
                v_lang.change(None, v_lang, None, js=SWITCH_TRACK_JS)

            with gr.Tab("My courses", id="courses"):
                library = build_library_tab(
                    gr,
                    courses_home,
                    models,
                    transcriber_factory,
                    friendly_error,
                    language_choices,
                    MODE_CHOICES,
                )
            with gr.Tab("Translate a lesson"):
                with gr.Group():
                    gr.Markdown("### 1. Add your lesson", elem_classes="step")
                    text = gr.Textbox(
                        show_label=False,
                        value=DEFAULT_TEXT,
                        lines=9,
                        placeholder="Paste English lesson text here",
                    )
                    upload = gr.File(
                        label="or upload a .md or .txt file",
                        height=130,
                        file_types=[".md", ".markdown", ".txt"],
                        type="filepath",
                    )
                gr.Markdown("### 2. Pick the languages", elem_classes="step")
                targets = gr.CheckboxGroup(
                    show_label=False,
                    choices=language_choices,
                    value=["hin_Deva", "kan_Knda"],
                )
                gr.Markdown("### 3. Choose how it runs", elem_classes="step")
                mode = gr.Radio(show_label=False, choices=MODE_CHOICES, value="light")
                with gr.Accordion("Optional: keep or fix technical words", open=False):
                    keep = gr.Textbox(
                        label="Keep these words in English (separated by commas)",
                        placeholder="photosynthesis, Python",
                    )
                    sheet = gr.File(
                        label="Course glossary (.csv: term, then the exact word per language)",
                        file_types=[".csv"],
                        type="filepath",
                    )
                go = gr.Button("Translate lesson", variant="primary", size="lg", elem_id="go")
                status = gr.Markdown()
                files = gr.File(
                    label="Download one file per language, and the class pack (.zip)",
                    file_count="multiple",
                    visible=False,
                )
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
                edited = gr.File(label="Your edited file", visible=False)
                go.click(
                    on_translate,
                    [text, upload, targets, mode, keep, sheet],
                    [status, files, review_state, review_lang, review_table, save_btn],
                )
                review_lang.change(on_review_language, [review_state, review_lang], review_table)
                save_btn.click(on_save_review, [review_state, review_lang, review_table], edited)
        app.load(library.on_load, None, [library.course, *library.view])
        library.send.click(
            lambda course, name: (
                (
                    str(courses_home.course_path(course) / "lectures" / name),
                    gr.Tabs(selected="lecture"),
                )
                if course and name
                else (None, gr.Tabs())
            ),
            [library.course, library.item],
            [v_upload, tabs],
        )
        gr.Markdown(NOTE)
    return app


def warm_up(holder: ModelHolder, mode: Mode) -> None:
    """Load a model in the background so the first translation on stage is fast."""

    def load() -> None:
        try:
            holder.get(mode).translate(["Hello."], "hin_Deva")
        except Exception as error:  # warm-up is best effort; the real click reports errors
            print(f"Warm-up skipped: {friendly_error(error)}")

    threading.Thread(target=load, daemon=True).start()


def launch(
    port: int = 7860,
    share: bool = False,
    warm: Mode | None = None,
    lan: bool = False,
    workspace_root: Path | None = None,
) -> None:
    """Start the web interface on this computer, optionally preloading a model.

    With `lan`, other devices on the same Wi-Fi or hotspot can open it, with no internet.
    """

    holder = ModelHolder()
    if warm:
        warm_up(holder, warm)
    if lan:
        address = lan_address(port)
        print(f"Students on this network can open: {address or 'your computer address'}")
        print("Only use this on a network you trust: anyone on it can use the app.")
    courses_home = Workspace(workspace_root or default_workspace_root())
    build_app(holder, workspace=courses_home).launch(
        server_name="0.0.0.0" if lan else None,
        server_port=port,
        share=share,
        theme=make_theme(),
        css=GREEN_CSS,
        js=FORCE_LIGHT_JS,
        allowed_paths=[str(courses_home.root)],
        footer_links=[],
    )
