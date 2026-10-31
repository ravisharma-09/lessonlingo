"""Gradio web interface for LessonLingo.

Set up once, then no internet needed: the app only uses models that
`lessonlingo setup` already downloaded.
"""

from __future__ import annotations

import base64
import os
import socket
import subprocess
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
from lessonlingo.tts import Synthesizer, dub_subtitles, make_synthesizer
from lessonlingo.ui_assets import (
    HERO_HTML,
    LESSON_STEPS,
    SCROLL_TOP_JS,
    stepper_html,
)
from lessonlingo.ui_assets import STYLE_CSS as GREEN_CSS
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

# The app writes its results here, and only this folder (plus the courses folder) may be served.
APP_TEMP = Path(tempfile.gettempdir()) / "lessonlingo_output"


def new_output_folder(prefix: str) -> Path:
    """A fresh folder for one job's files, inside the folder the web server is allowed to serve."""

    APP_TEMP.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=APP_TEMP))


FORCE_LIGHT_JS = """() => {
  const url = new URL(window.location);
  if (url.searchParams.get('__theme') !== 'light') {
    url.searchParams.set('__theme', 'light');
    window.location.href = url.href;
  }
}"""


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
  window.llPick = (kind, value) => {
    const root = document.querySelector('#lecture-player');
    const video = root && root.querySelector('video');
    if (kind === 'sub' && value === 'off' && video) {
      video.querySelectorAll('track').forEach((el) => {
        if (el.track) el.track.mode = 'disabled';
      });
      return;
    }
    if (kind === 'sub' && video) {
      video.querySelectorAll('track').forEach((el) => {
        if (el.track) el.track.mode = el.dataset.code === value ? 'showing' : 'disabled';
      });
    }
    const box = document.querySelector(kind === 'sub' ? '#lecture-lang' : '#lecture-voice');
    const input = box && box.querySelector('input[type=radio][value="' + value + '"]');
    if (input) input.click();
  };
  window.llMenu = (kind, button) => {
    const root = document.querySelector('#lecture-player');
    const video = root.querySelector('video');
    const pops = root.querySelectorAll('.ll-pop');
    const pop = button.parentElement.querySelector('.ll-pop');
    const open = pop.hidden;
    pops.forEach((el) => { el.hidden = true; });
    if (!open) return;
    let active = kind === 'audio' ? (window.__voice || 'original') : 'off';
    if (kind === 'sub') {
      video.querySelectorAll('track').forEach((el) => {
        if (el.track && el.track.mode === 'showing') active = el.dataset.code;
      });
    }
    pop.querySelectorAll('button').forEach((b) => {
      b.classList.toggle('on', b.dataset.value === active);
    });
    pop.hidden = false;
  };
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


def _voice_data_url(path: str) -> str:
    """The voice as a small embedded audio file, so playing it needs no file route.

    The WAV is squeezed to AAC (about 0.5 MB a minute) by ffmpeg. If ffmpeg cannot, the WAV
    itself is embedded.
    """

    wav = Path(path)
    packed = wav.with_suffix(".m4a")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "64k", str(packed)],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0 and packed.exists() and packed.stat().st_size > 0:
        kind, source = "audio/mp4", packed
    else:
        kind, source = "audio/wav", wav
    return f"data:{kind};base64,{base64.b64encode(source.read_bytes()).decode('ascii')}"


VOICE_WARNING = (
    "The voice could not play in this browser. Download the dubbed video from the files below, "
    "or press play again."
)

VOICE_JS = """(voice) => {
  const root = document.querySelector('#lecture-player');
  const video = root && root.querySelector('video');
  if (!video) return;
  const audios = () => Array.from(root.querySelectorAll('audio'));
  const current = () => audios().find((a) => a.dataset.code === window.__voice);
  const align = () => {
    const a = current();
    if (a && Math.abs(a.currentTime - video.currentTime) > 0.3) a.currentTime = video.currentTime;
  };
  const warn = () => {
    const el = root.querySelector('.ll-warn');
    if (el) el.hidden = false;
  };
  const start = () => {
    const a = current();
    if (a) { align(); a.play().catch(warn); }
  };
  if (!video.__voiceBound) {
    video.__voiceBound = true;
    video.addEventListener('play', start);
    video.addEventListener('playing', start);
    video.addEventListener('pause', () => audios().forEach((a) => a.pause()));
    video.addEventListener('waiting', () => audios().forEach((a) => a.pause()));
    video.addEventListener('seeked', align);
    video.addEventListener('timeupdate', align);
    video.addEventListener('ratechange', () => {
      const a = current();
      if (a) a.playbackRate = video.playbackRate;
    });
  }
  window.__voice = voice;
  audios().forEach((a) => a.pause());
  video.muted = voice !== 'original';
  const a = current();
  if (a) {
    a.currentTime = video.currentTime;
    a.playbackRate = video.playbackRate;
    if (a.error) warn();
    if (!video.paused) a.play().catch(warn);
  }
}"""


def player_html(
    video: str,
    subtitles: dict[str, str],
    selected: str,
    voices: dict[str, str] | None = None,
) -> str:
    """A standard browser video player with every language as a subtitle track.

    Dubbed voices (one hidden audio element each) are kept in step by VOICE_JS. Subtitles are
    embedded in the page. The chosen language is switched on by default and by
    SWITCH_TRACK_JS; viewers can also pick one in the player's own captions menu.
    """

    tracks = "".join(
        f'<track kind="subtitles" src="{_subtitle_data_url(path)}" data-code="{code}"'
        f' srclang="{SUBTITLE_LANGUAGE.get(code, code)}" label="{SUPPORTED_LANGUAGES[code]}"'
        f"{' default' if code == selected else ''}>"
        for code, path in subtitles.items()
    )
    voice_tags = "".join(
        f'<audio preload="auto" data-code="{code}" src="{_voice_data_url(path)}"'
        " onerror=\"this.parentElement.querySelector('.ll-warn').hidden=false\"></audio>"
        for code, path in (voices or {}).items()
    )
    sub_items = [("off", "Off")] + [(code, SUPPORTED_LANGUAGES[code]) for code in subtitles]
    audio_items = [("original", "Original")] + [
        (code, SUPPORTED_LANGUAGES[code]) for code in voices or {}
    ]
    menus = _menu("sub", "CC", "Subtitles", sub_items)
    if voices:
        menus += _menu("audio", "Audio", "Audio track", audio_items)
    return (
        '<div class="ll-player">'
        f'<video controls preload="metadata" src="{_file_url(video)}" '
        f'style="width:100%;border-radius:14px;background:#000;display:block">{tracks}</video>'
        f'<div class="ll-menus">{menus}</div>{voice_tags}'
        f'<p class="ll-warn" hidden>{VOICE_WARNING}</p></div>'
    )


def _menu(kind: str, short: str, title: str, items: list[tuple[str, str]]) -> str:
    """One pop-up menu button in the player: pick a subtitle language or an audio track."""

    options = "".join(
        f'<button type="button" data-value="{value}" onclick="llPick(\'{kind}\',\'{value}\');'
        f'this.parentElement.hidden=true">{label}</button>'
        for value, label in items
    )
    return (
        f'<div class="ll-menu"><button type="button" class="ll-btn" title="{title}" '
        f"onclick=\"llMenu('{kind}',this)\">{short}</button>"
        f'<div class="ll-pop" hidden>{options}</div></div>'
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
    synthesizer_factory: Callable[[], Synthesizer] = make_synthesizer,
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
            gr.File(value=[*paths, str(pack)]),
            review,
            gr.Radio(choices=[(SUPPORTED_LANGUAGES[c], c) for c in docs], value=first),
            gr.Dataframe(value=review_rows(*docs[first])),
            gr.Column(visible=False),
            gr.Column(visible=True),
            stepper_html(2, LESSON_STEPS),
        )

    def on_lesson_again() -> tuple[Any, ...]:
        return (
            gr.Column(visible=True),
            gr.Column(visible=False),
            stepper_html(1, LESSON_STEPS),
            gr.File(visible=False),
        )

    def on_review_language(review: dict[str, Any], code: str) -> Any:
        if not review or code not in review["docs"]:
            return gr.Dataframe()
        return gr.Dataframe(value=review_rows(*review["docs"][code]))

    def on_save_review(review: dict[str, Any], code: str, rows: Any) -> Any:
        if not review or code not in review["docs"]:
            raise gr.Error("Translate a lesson first.")
        table = rows.values.tolist() if hasattr(rows, "values") else rows
        path = save_review(review["docs"][code][0], table, review["stem"], code)
        return gr.File(value=path, visible=True)

    language_choices = [
        (f"{name} \u00b7 {NATIVE_NAMES[code]}", code) for code, name in SUPPORTED_LANGUAGES.items()
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
        note = f"Heard {len(cues)} lines."
        if doubtful:
            note += f" **{doubtful} may be wrong** (marked Check, with the doubtful words)."
        return (
            note,
            {"cues": cues},
            gr.Dataframe(value=transcript_rows(cues)),
            gr.Column(visible=False),
            gr.Column(visible=True),
            stepper_html(2),
        )

    def on_back_to_add() -> tuple[Any, ...]:
        return gr.Column(visible=True), gr.Column(visible=False), stepper_html(1)

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
            folder = new_output_folder("video_")
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
            voice_notes: list[str] = []
            engine = ""
            if dub:
                models.close()  # free the GPU before the voice model loads
                synth = synthesizer_factory()

                def speak_note(message: str) -> None:
                    progress(None, desc=message)
                    if not message.startswith("Speaking"):
                        voice_notes.append(message)

                spoken = dub_subtitles(
                    [p for p in written if p.suffix == ".srt"],
                    Path(upload),
                    folder,
                    synth,
                    note=speak_note,
                )
                engine = getattr(synth, "engine_name", "")
            pack = make_class_pack(
                [*written, *[p for p in spoken if p.suffix == ".wav"]],
                folder / f"{stem}.classpack.zip",
            )
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            raise gr.Error(friendly_error(error)) from error
        vtt = {p.name.split(".")[-2]: str(p) for p in written if p.suffix == ".vtt"}
        wavs = {p.name.split(".")[-2]: str(p) for p in spoken if p.suffix == ".wav"}
        first = next(iter(vtt))
        has_video = not str(upload).endswith((".srt", ".vtt"))
        player = (
            player_html(upload, vtt, first, wavs)
            if has_video
            else "<p>Your subtitle files are ready to download below.</p>"
        )
        help_text = (
            "Subtitles are on in the player. Use the language buttons or the player's CC button."
            if has_video
            else "Download the translated subtitle files below."
        )
        if wavs and has_video:
            help_text += f" Choose a Voice to hear the lecture in that language ({engine})."
        elif dub and not wavs:
            help_text += " No voice was made. " + " ".join(voice_notes)
        elif voice_notes:
            help_text += " " + " ".join(voice_notes)
        voice_choices = [
            ("Original voice", "original"),
            *[(SUPPORTED_LANGUAGES[c], c) for c in wavs],
        ]
        return (
            gr.File(value=[*map(str, written), *map(str, spoken), str(pack)]),
            vtt,
            gr.Radio(choices=[(SUPPORTED_LANGUAGES[c], c) for c in vtt], value=first),
            gr.HTML(value=player),
            gr.Radio(choices=voice_choices, value="original", visible=bool(wavs) and has_video),
            f"### Your lecture is ready\n{help_text}",
            gr.Column(visible=False),
            gr.Column(visible=True),
            stepper_html(3),
        )

    def on_new_lecture() -> tuple[Any, ...]:
        return (
            None,
            {},
            {},
            gr.HTML(value=""),
            gr.Column(visible=True),
            gr.Column(visible=False),
            gr.Column(visible=False),
            stepper_html(1),
        )

    def targets_box(default: list[str]) -> Any:
        gr.Markdown("### Translate into", elem_classes="step")
        return gr.CheckboxGroup(show_label=False, choices=language_choices, value=default)

    with gr.Blocks(title="LessonLingo") as app:
        gr.HTML(HERO_HTML, padding=False)
        with gr.Tabs() as tabs:
            with gr.Tab("Lecture", id="lecture"):
                v_steps = gr.HTML(stepper_html(1), padding=False)
                with gr.Column(elem_classes="step-body") as lec_add:
                    with gr.Row(elem_classes="split"):
                        with gr.Column(scale=1, min_width=320):
                            gr.Markdown(
                                "### Add your lecture\nA video, audio or `.srt` file in English.",
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
                            if SAMPLE_LECTURE.is_file():
                                v_sample = gr.Button(
                                    "No file? Try the sample lecture",
                                    size="sm",
                                    elem_classes="link-button",
                                )
                                v_sample.click(lambda: str(SAMPLE_LECTURE), None, v_upload)

                        with gr.Column(scale=1, min_width=320):
                            v_targets = targets_box(["kan_Knda", "hin_Deva"])
                            with gr.Accordion("Options", open=False):
                                v_mode = gr.Radio(
                                    label="How should it run?", choices=MODE_CHOICES, value="light"
                                )
                                v_keep = gr.Textbox(
                                    label="Keep these words in English (separated by commas)",
                                    placeholder="photosynthesis, Python",
                                )
                                v_sheet = gr.File(
                                    label="Course glossary (.csv, see the README)",
                                    file_types=[".csv"],
                                    type="filepath",
                                )
                                v_dub = gr.Checkbox(
                                    label="Also speak it (Hindi and Kannada, needs voice setup)",
                                    value=False,
                                )
                    with gr.Column(elem_classes="sticky-cta"):
                        v_listen = gr.Button("Continue", variant="primary", size="lg")
                with gr.Column(visible=False, elem_classes="step-body") as lec_check:
                    gr.Markdown(
                        "### Check what was heard\nFix any mistakes in the English before it is "
                        "translated. Click a cell to edit.",
                        elem_classes="step",
                    )
                    v_note = gr.Markdown(elem_classes="hint")
                    v_table = gr.Dataframe(
                        headers=["Time", "Heard", "Check"],
                        datatype=["str", "str", "str"],
                        column_widths=["12%", "60%", "28%"],
                        static_columns=[0, 2],
                        interactive=True,
                        wrap=True,
                        type="array",
                    )
                    with gr.Row(elem_classes="row-buttons"):
                        v_back = gr.Button("Back", variant="secondary")
                        v_go = gr.Button("Translate", variant="primary")
                with gr.Column(visible=False, elem_classes="step-body") as lec_watch:
                    v_done = gr.Markdown("### Your lecture is ready", elem_classes="step")
                    with gr.Row(elem_classes="split"):
                        with gr.Column(scale=3, min_width=320):
                            v_player = gr.HTML(padding=False, elem_id="lecture-player")
                        with gr.Column(scale=2, min_width=300):
                            v_lang = gr.Radio(
                                label="Subtitles",
                                choices=[],
                                elem_classes="lang-chips",
                                elem_id="lecture-lang",
                            )
                            v_voice = gr.Radio(
                                label="Voice",
                                choices=[("Original voice", "original")],
                                value="original",
                                elem_classes="lang-chips",
                                elem_id="lecture-voice",
                                visible=False,
                            )
                            v_files = gr.File(
                                label="Download subtitles (.srt, .vtt), voices and the class pack",
                                file_count="multiple",
                            )
                            v_again = gr.Button("Translate another lecture", variant="secondary")
                v_heard = gr.State({})
                v_state = gr.State({})

                v_listen.click(
                    on_listen,
                    [v_upload, v_keep, v_sheet],
                    [v_note, v_heard, v_table, lec_add, lec_check, v_steps],
                ).then(None, None, None, js=SCROLL_TOP_JS)
                v_back.click(on_back_to_add, None, [lec_add, lec_check, v_steps]).then(
                    None, None, None, js=SCROLL_TOP_JS
                )
                v_go.click(
                    on_translate_video,
                    [v_upload, v_heard, v_table, v_targets, v_mode, v_keep, v_sheet, v_dub],
                    [
                        v_files,
                        v_state,
                        v_lang,
                        v_player,
                        v_voice,
                        v_done,
                        lec_check,
                        lec_watch,
                        v_steps,
                    ],
                ).then(None, v_lang, None, js=SWITCH_TRACK_JS).then(
                    None, v_voice, None, js=VOICE_JS
                ).then(None, None, None, js=SCROLL_TOP_JS)
                v_lang.change(None, v_lang, None, js=SWITCH_TRACK_JS)
                v_voice.change(None, v_voice, None, js=VOICE_JS)
                v_again.click(
                    on_new_lecture,
                    None,
                    [v_upload, v_heard, v_state, v_player, lec_add, lec_check, lec_watch, v_steps],
                ).then(None, None, None, js=SCROLL_TOP_JS)

            with gr.Tab("Lesson", id="lesson"):
                les_steps = gr.HTML(stepper_html(1, LESSON_STEPS), padding=False)
                with gr.Column(elem_classes="step-body") as les_add:
                    with gr.Row(elem_classes="split"):
                        with gr.Column(scale=1, min_width=320):
                            gr.Markdown(
                                "### Add your lesson\nPaste English text or upload a file.",
                                elem_classes="step",
                            )
                            text = gr.Textbox(
                                show_label=False,
                                value=DEFAULT_TEXT,
                                lines=8,
                                placeholder="Paste English lesson text here",
                            )
                            upload = gr.File(
                                label="or upload a file",
                                height=130,
                                file_types=[".md", ".markdown", ".txt"],
                                type="filepath",
                            )
                        with gr.Column(scale=1, min_width=320):
                            targets = targets_box(["hin_Deva", "kan_Knda"])
                            with gr.Accordion("Options", open=False):
                                mode = gr.Radio(
                                    label="How should it run?",
                                    choices=MODE_CHOICES,
                                    value="light",
                                )
                                keep = gr.Textbox(
                                    label="Keep these words in English (separated by commas)",
                                    placeholder="photosynthesis, Python",
                                )
                                sheet = gr.File(
                                    label="Course glossary (.csv, see the README)",
                                    file_types=[".csv"],
                                    type="filepath",
                                )
                    with gr.Column(elem_classes="sticky-cta"):
                        go = gr.Button("Translate lesson", variant="primary", size="lg")
                with gr.Column(visible=False, elem_classes="step-body") as les_review:
                    gr.Markdown(
                        "### Your lesson is ready\nCheck each line, fix any, then save your edits.",
                        elem_classes="step",
                    )
                    review_lang = gr.Radio(show_label=False, choices=[], elem_classes="lang-chips")
                    review_table = gr.Dataframe(
                        headers=["English", "Translation"],
                        datatype=["str", "str"],
                        column_widths=["45%", "55%"],
                        static_columns=[0],
                        interactive=True,
                        wrap=True,
                        type="array",
                    )
                    save_btn = gr.Button("Save my edits", variant="secondary")
                    edited = gr.File(label="Your edited file", visible=False)
                    files = gr.File(
                        label="Download one file per language, and the class pack (.zip)",
                        file_count="multiple",
                    )
                    again = gr.Button("Translate another lesson", variant="secondary")
                review_state = gr.State({})
                go.click(
                    on_translate,
                    [text, upload, targets, mode, keep, sheet],
                    [
                        files,
                        review_state,
                        review_lang,
                        review_table,
                        les_add,
                        les_review,
                        les_steps,
                    ],
                ).then(None, None, None, js=SCROLL_TOP_JS)
                review_lang.change(on_review_language, [review_state, review_lang], review_table)
                save_btn.click(on_save_review, [review_state, review_lang, review_table], edited)
                again.click(on_lesson_again, None, [les_add, les_review, les_steps, edited]).then(
                    None, None, None, js=SCROLL_TOP_JS
                )

            with gr.Tab("Courses", id="courses"):
                with gr.Column(elem_classes="step-body"):
                    library = build_library_tab(
                        gr,
                        courses_home,
                        models,
                        transcriber_factory,
                        friendly_error,
                        language_choices,
                        MODE_CHOICES,
                    )
        app.load(library.on_load, None, [library.course, *library.view])
        library.send.click(
            lambda course, name: (
                (
                    str(courses_home.course_path(course) / "lectures" / name),
                    gr.Tabs(selected="lecture"),
                    gr.Column(visible=True),
                    gr.Column(visible=False),
                    gr.Column(visible=False),
                    stepper_html(1),
                )
                if course and name
                else (None, gr.Tabs(), gr.Column(), gr.Column(), gr.Column(), stepper_html(1))
            ),
            [library.course, library.item],
            [v_upload, tabs, lec_add, lec_check, lec_watch, v_steps],
        )
        gr.Markdown(NOTE, elem_classes="hint")
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
        allowed_paths=[str(courses_home.root), str(APP_TEMP)],
        footer_links=[],
    )
