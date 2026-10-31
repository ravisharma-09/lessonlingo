"""Gradio web interface for LessonLingo.

Set up once, then no internet needed: the app only uses models that
`lessonlingo setup` already downloaded.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
import socket
import subprocess
import tempfile
import threading
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import quote

from lessonlingo import cancel
from lessonlingo.glossary import GlossaryTranslator, load_glossary, parse_terms
from lessonlingo.languages import NATIVE_NAMES, SUPPORTED_LANGUAGES, validate_targets
from lessonlingo.library import build_library_tab
from lessonlingo.markdown_io import Segment, rebuild
from lessonlingo.pack import make_class_pack
from lessonlingo.pipeline import translate_segments
from lessonlingo.subtitles import Cue, format_timestamp
from lessonlingo.translator import IndicTransTranslator, Mode, Translator
from lessonlingo.tts import VOICE_LANGUAGES, Synthesizer, dub_subtitles, make_synthesizer
from lessonlingo.ui_assets import (
    HERO_HTML,
    LIGHT_HEAD,
    LOADING_DONE_JS,
    LOADING_LISTEN_JS,
    LOADING_TRANSLATE_JS,
    LOADING_VIDEO_JS,
    SCROLL_TOP_JS,
)
from lessonlingo.ui_assets import STYLE_CSS as GREEN_CSS
from lessonlingo.video import (
    FasterWhisperTranscriber,
    Transcriber,
    embed_subtitles,
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
    ("Fast: 200M model (any laptop)", "light"),
    ("Best quality: 1B model (NVIDIA GPU)", "quality"),
]

VIDEO_FILES = {".mp4", ".mkv", ".mov", ".webm", ".m4v", ".avi"}
AUDIO_FILES = {".mp3", ".wav", ".m4a"}
SUBTITLE_FILES = {".srt", ".vtt"}
KIND_FILES = {"video": VIDEO_FILES, "audio": AUDIO_FILES, "subs": SUBTITLE_FILES}
KIND_NAMES = {"video": "a video", "audio": "an audio file", "subs": "a .srt or .vtt file"}
DUB_PER_LANGUAGE = re.compile(r"^.*\.([a-z]{3}_[A-Za-z]{4})\.dubbed\.mp4$")
TIME_NATURAL = "Natural voice takes about 8 to 9 minutes for each minute of video."
TIME_QUICK = "Quick voice takes about 1 minute for each minute of video."
KIND_CHOICES: list[tuple[str, str]] = [
    ("Text", "text"),
    ("Video", "video"),
    ("Audio", "audio"),
    ("Subtitle file", "subs"),
]
WANT_VIDEO: list[tuple[str, str]] = [
    ("Subtitle files", "subs"),
    ("Video with subtitles inside", "embed"),
    ("Video with subtitles and dubbed audio", "dub"),
]
WANT_OTHER: list[tuple[str, str]] = [
    ("Subtitle files", "subs"),
    ("Subtitle files and voice", "voice"),
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


def make_theme() -> Any:
    """Return the Gradio theme: slate and orange, restyled by the page CSS."""

    import gradio as gr

    return gr.themes.Soft(
        primary_hue="orange",
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

    if isinstance(error, cancel.Cancelled):
        return str(error)
    text = str(error)
    lowered = text.lower()
    if "out of memory" in lowered:
        return (
            "The graphics card ran out of memory. Choose 'Fast: 200M model', "
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
  const player = () => document.querySelector('#lecture-player .ll-player');
  const DEFAULTS = { size: '5', pos: 'bottom', bg: 'dark', width: 'full' };
  const readSub = () => {
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem('ll-sub') || '{}'); } catch (e) { saved = {}; }
    return Object.assign({}, DEFAULTS, saved);
  };
  const paintSub = () => {
    const box = player();
    if (!box) return;
    const s = readSub();
    box.style.setProperty('--ll-sub-size', s.size);
    box.dataset.subPos = s.pos;
    box.dataset.subBg = s.bg;
    box.dataset.subWidth = s.width;
  };
  const showCues = (track) => {
    const box = player();
    const out = box && box.querySelector('.ll-sub');
    if (!out) return;
    const cues = track && track.activeCues ? Array.from(track.activeCues) : [];
    out.textContent = cues.map((c) => c.text).join('\\n');
    out.hidden = !out.textContent;
  };
  const select = (value) => {
    const video = document.querySelector('#lecture-player video');
    if (!video) return;
    video.querySelectorAll('track').forEach((el) => {
      const track = el.track;
      if (!track) return;
      track.oncuechange = null;
      if (el.dataset.code === value) {
        track.mode = 'hidden';
        track.oncuechange = () => showCues(track);
        showCues(track);
      } else {
        track.mode = 'disabled';
      }
    });
    if (value === 'off') showCues(null);
  };
  window.llPick = (kind, value) => {
    if (kind === 'sub') select(value);
    if (kind === 'sub' && value === 'off') return;
    const box = document.querySelector(kind === 'sub' ? '#lecture-lang' : '#lecture-voice');
    const input = box && box.querySelector('input[type=radio][value="' + value + '"]');
    if (input) input.click();
  };
  window.llSet = (key, value) => {
    const s = readSub();
    s[key] = value;
    try { localStorage.setItem('ll-sub', JSON.stringify(s)); } catch (e) { /* private window */ }
    paintSub();
    document.querySelectorAll('#lecture-player .ll-set button').forEach((b) => {
      b.classList.toggle('on', readSub()[b.dataset.key] === b.dataset.value);
    });
  };
  window.llFullscreen = () => {
    const box = player();
    if (document.fullscreenElement) document.exitFullscreen();
    else if (box && box.requestFullscreen) box.requestFullscreen();
  };
  window.llMenu = (kind, button) => {
    const root = document.querySelector('#lecture-player');
    const video = root.querySelector('video');
    const pops = root.querySelectorAll('.ll-pop');
    const pop = button.parentElement.querySelector('.ll-pop');
    const open = pop.hidden;
    pops.forEach((el) => { el.hidden = true; });
    if (!open) return;
    if (kind === 'set') {
      const s = readSub();
      pop.querySelectorAll('button').forEach((b) => {
        b.classList.toggle('on', s[b.dataset.key] === b.dataset.value);
      });
    } else {
      let active = kind === 'audio' ? (window.__voice || 'original') : 'off';
      if (kind === 'sub') {
        video.querySelectorAll('track').forEach((el) => {
          if (el.track && el.track.mode === 'hidden') active = el.dataset.code;
        });
      }
      pop.querySelectorAll('button').forEach((b) => {
        b.classList.toggle('on', b.dataset.value === active);
      });
    }
    pop.hidden = false;
  };
  const apply = (tries) => {
    const video = document.querySelector('#lecture-player video');
    const tracks = video ? video.querySelectorAll('track') : [];
    if (!tracks.length) { if (tries > 0) setTimeout(() => apply(tries - 1), 200); return; }
    paintSub();
    select(code);
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
  const run = (tries) => {
    const root = document.querySelector('#lecture-player');
    const video = root && root.querySelector('video');
    if (!video) {
      if (tries > 0) setTimeout(() => run(tries - 1), 200);
      return;
    }
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
    // A load that interrupts a play request is not a failure.
    const fail = (error) => {
      if (!error || error.name !== 'AbortError') warn();
    };
    const start = () => {
      const a = current();
      if (a) { align(); a.play().catch(fail); }
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
    const dubs = JSON.parse(video.dataset.dubs || '{}');
    const target = voice === 'original' ? video.dataset.original : dubs[voice];
    if (target) {
      // The dubbed video carries its own voice, so it needs no separate audio.
      video.muted = false;
      if (video.dataset.current !== target) {
        const time = video.currentTime;
        const playing = !video.paused;
        const rate = video.playbackRate;
        video.dataset.current = target;
        video.src = target;
        video.addEventListener('loadedmetadata', () => {
          video.currentTime = time;
          video.playbackRate = rate;
          if (playing) video.play().catch(fail);
        }, { once: true });
        video.addEventListener('error', () => {
          // Could not load the dubbed video: fall back to the separate voice track.
          video.dataset.current = video.dataset.original;
          video.src = video.dataset.original;
          warn();
        }, { once: true });
      }
      return;
    }
    video.muted = voice !== 'original';
    const a = current();
    if (a) {
      a.currentTime = video.currentTime;
      a.playbackRate = video.playbackRate;
      if (a.error) warn();
      if (!video.paused) a.play().catch(fail);
    }
  };
  run(15);
}"""


AFTER_TRANSLATE_JS = (
    "(lang, voice) => { (" + SWITCH_TRACK_JS + ")(lang); (" + VOICE_JS + ")(voice); "
    "window.llDone(); window.scrollTo({ top: 0, behavior: 'smooth' }); }"
)


def player_html(
    video: str,
    subtitles: dict[str, str],
    selected: str,
    voices: dict[str, str] | None = None,
    dubbed_videos: dict[str, str] | None = None,
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
    menus += _settings_menu()
    if voices:
        menus += _menu("audio", "Audio", "Audio track", audio_items)
    menus += (
        '<div class="ll-menu"><button type="button" class="ll-btn" title="Fullscreen" '
        'onclick="llFullscreen()">Full</button></div>'
    )
    dubs = {code: _file_url(path) for code, path in (dubbed_videos or {}).items()}
    return (
        '<div class="ll-player">'
        f'<video controls playsinline preload="auto" src="{_file_url(video)}" '
        f'data-original="{_file_url(video)}" data-dubs="{html.escape(json.dumps(dubs))}" '
        f'style="width:100%;border-radius:14px;background:#000;display:block">{tracks}</video>'
        '<div class="ll-sub" hidden></div>'
        f'<div class="ll-menus">{menus}</div>{voice_tags}'
        f'<p class="ll-warn" hidden>{VOICE_WARNING}</p></div>'
    )


SUBTITLE_SETTINGS = (
    ("size", "Size", (("3", "Small"), ("4", "Medium"), ("5", "Large"), ("6", "Extra large"))),
    ("pos", "Position", (("bottom", "Bottom"), ("middle", "Middle"), ("top", "Top"))),
    ("bg", "Background", (("dark", "Dark box"), ("light", "Light box"), ("none", "None"))),
    ("width", "Width", (("full", "Full width"), ("centered", "Centred"))),
)


def _settings_menu() -> str:
    """The subtitle settings pop-up: size, position, background and width."""

    groups = "".join(
        f'<p class="grp">{title}</p><div class="row">'
        + "".join(
            f'<button type="button" data-key="{key}" data-value="{value}" '
            f"onclick=\"llSet('{key}','{value}')\">{label}</button>"
            for value, label in options
        )
        + "</div>"
        for key, title, options in SUBTITLE_SETTINGS
    )
    return (
        '<div class="ll-menu"><button type="button" class="ll-btn" title="Subtitle settings" '
        "onclick=\"llMenu('set',this)\">Aa</button>"
        f'<div class="ll-pop ll-set" hidden>{groups}</div></div>'
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
    synthesizer_factory: Callable[..., Synthesizer] = make_synthesizer,
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
        cancel.reset()
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
            gr.Tabs(selected="result"),
            gr.Tab(interactive=True),
            gr.Column(visible=False),
            gr.Column(visible=True),
            "",
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
    voice_choices = [
        (label + (" \u00b7 voice" if code in VOICE_LANGUAGES else ""), code)
        for label, code in language_choices
    ]

    def on_listen(
        upload: str | None, keep: str, sheet: str | None, progress: Any = None
    ) -> tuple[Any, ...]:
        if not upload:
            raise gr.Error("Add a lecture video, audio file or .srt first.")
        cancel.reset()
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
            gr.Tabs(selected="check"),
            gr.Tab(interactive=True),
            "",
        )

    def on_translate_video(
        upload: str | None,
        heard: dict[str, Any],
        rows: Any,
        targets: list[str],
        mode: Mode,
        keep: str,
        sheet: str | None,
        want: str,
        voice_quality: str = "natural",
        progress: Any = None,
    ) -> tuple[Any, ...]:
        dub = want in ("voice", "dub")
        if not targets:
            raise gr.Error("Pick at least one language.")
        if not heard or not upload:
            raise gr.Error("Listen to the lecture first.")
        cancel.reset()
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
                engine_choice = "mms" if voice_quality == "quick" else "auto"
                try:
                    synth = synthesizer_factory(engine_choice)
                except TypeError:  # a stand-in voice that takes no choice
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
                    subtitles_in_video=want == "dub",
                )
                engine = getattr(synth, "engine_name", "")
            if want == "embed" and Path(upload).suffix.lower() in VIDEO_FILES:
                tracks = {p.name.split(".")[-2]: p for p in written if p.suffix == ".srt"}
                tracks.pop("en", None)
                if tracks:
                    spoken.append(
                        embed_subtitles(Path(upload), tracks, folder / f"{stem}.subtitled.mp4")
                    )
            pack = make_class_pack(
                [*written, *[p for p in spoken if p.suffix == ".wav"]],
                folder / f"{stem}.classpack.zip",
            )
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            raise gr.Error(friendly_error(error)) from error
        vtt = {p.name.split(".")[-2]: str(p) for p in written if p.suffix == ".vtt"}
        wavs = {p.name.split(".")[-2]: str(p) for p in spoken if p.suffix == ".wav"}
        per_language = {m.group(1): str(p) for p in spoken if (m := DUB_PER_LANGUAGE.match(p.name))}
        first = next(iter(vtt))
        has_video = not str(upload).endswith((".srt", ".vtt"))
        player = (
            player_html(upload, vtt, first, wavs, per_language)
            if has_video
            else "<p>Your subtitle files are ready to download below.</p>"
        )
        help_text = (
            "Switch subtitles with CC and the voice with Audio in the player."
            if has_video
            else "Your subtitle files are below."
        )
        if want == "embed" and has_video:
            help_text += " The video with subtitles inside is in Downloads."
        if want == "dub" and has_video:
            help_text += " The video with subtitles and dubbed audio is in Downloads."
        if wavs and has_video:
            help_text += f" Voice: {engine}." if engine else ""
        elif dub and not wavs:
            help_text += " No voice was made. " + " ".join(voice_notes)
        elif voice_notes:
            help_text += " " + " ".join(voice_notes)
        final_files = [
            str(p)
            for p in spoken
            if p.name.endswith((".dubbed.mp4", ".subtitled.mp4"))
            and not DUB_PER_LANGUAGE.match(p.name)
        ]
        voice_options = [
            ("Original voice", "original"),
            *[(SUPPORTED_LANGUAGES[c], c) for c in wavs],
        ]
        # Start with a dubbed voice on, in the subtitle language when it has one.
        start_voice = first if first in wavs else next(iter(wavs), "original")
        return (
            gr.File(value=[*map(str, written), *map(str, spoken), str(pack)]),
            vtt,
            gr.Radio(choices=[(SUPPORTED_LANGUAGES[c], c) for c in vtt], value=first),
            gr.HTML(value=player),
            gr.Radio(choices=voice_options, value=start_voice, visible=bool(wavs) and has_video),
            f"{help_text}",
            gr.Tabs(selected="result"),
            gr.Tab(interactive=True),
            gr.Column(visible=True),
            gr.Column(visible=False),
            "",
            gr.File(value=final_files, visible=bool(final_files)),
        )

    def check_add(kind: str, text: str, doc: str | None, media: str | None) -> Any:
        """Stop on the Add page with a clear message when nothing usable was added."""

        if kind == "text":
            if not (text or "").strip() and not doc:
                raise gr.Error("Type or paste some text, or upload a .md or .txt file.")
        else:
            if not media:
                raise gr.Error(f"Add {KIND_NAMES[kind]} first.")
            if Path(media).suffix.lower() not in KIND_FILES[kind]:
                allowed = ", ".join(sorted(KIND_FILES[kind]))
                raise gr.Error(f"That is not {KIND_NAMES[kind]}. Use {allowed}.")
        return gr.Tabs(selected="lang")

    def check_languages(targets: list[str]) -> Any:
        if not targets:
            raise gr.Error("Pick at least one language.")
        return gr.Tabs(selected="opts")

    def check_options(
        kind: str,
        text: str,
        doc: str | None,
        media: str | None,
        targets: list[str],
        want: str,
    ) -> None:
        """Catch every problem before the slow part starts."""

        check_add(kind, text, doc, media)
        check_languages(targets)
        if kind != "text" and want in ("voice", "dub"):
            voiced = [code for code in targets if code in VOICE_LANGUAGES]
            if not voiced:
                raise gr.Error(
                    "Voice is only available for Hindi and Kannada. Tick one of them on "
                    "Languages, or choose Subtitle files."
                )
            if len(voiced) < len(targets):
                names = " and ".join(SUPPORTED_LANGUAGES[code] for code in voiced)
                gr.Warning(f"Voice will be made for {names} only. Other languages get subtitles.")

    def voice_note(kind: str, targets: list[str], want: str, quality: str) -> str:
        """Say which languages get a voice, and how long this choice will take."""

        if kind == "text":
            return "A text lesson takes a few seconds."
        if want not in ("voice", "dub"):
            return "**About 20 seconds** for each minute of video."
        voiced = [SUPPORTED_LANGUAGES[code] for code in targets if code in VOICE_LANGUAGES]
        if not voiced:
            return "No voice yet. Tick Hindi or Kannada on Languages."
        pace = TIME_QUICK if quality == "quick" else TIME_NATURAL
        return f"Voice will be made in: **{', '.join(voiced)}**. {pace}"

    def on_want(kind: str, want: str) -> Any:
        return gr.Radio(visible=kind != "text" and want in ("voice", "dub"))

    def on_cancel() -> None:
        cancel.request()

    def page_head(title: str, why: str = "") -> None:
        gr.Markdown(f"## {title}\n{why}" if why else f"## {title}", elem_classes="page-head")

    def go_to(tab_id: str) -> Any:
        return gr.Tabs(selected=tab_id)

    def want_update(kind: str, targets: list[str], want: str) -> Any:
        """The "You get" choices: voice is offered only when a chosen language can be spoken."""

        voiced = any(code in VOICE_LANGUAGES for code in targets)
        if kind == "video":
            choices = WANT_VIDEO if voiced else WANT_VIDEO[:2]
            fallback = "dub" if voiced else "embed"
        else:
            choices = WANT_OTHER if voiced else WANT_OTHER[:1]
            fallback = "voice" if voiced else "subs"
        value = want if want in [v for _, v in choices] else fallback
        return gr.Radio(choices=choices, value=value, visible=kind != "text")

    def refresh_want(kind: str, targets: list[str], want: str) -> tuple[Any, Any]:
        update = want_update(kind, targets, want)
        value = update.value if hasattr(update, "value") else want
        return update, gr.Radio(visible=kind != "text" and value in ("voice", "dub"))

    def on_kind(kind: str, targets: list[str]) -> tuple[Any, ...]:
        text_in = kind == "text"
        label = {"video": "Video file", "audio": "Audio file", "subs": "Subtitle file"}.get(
            kind, "File"
        )
        return (
            gr.Column(visible=text_in),
            gr.Column(visible=not text_in),
            gr.File(label=label),
            want_update(kind, targets, "dub" if kind == "video" else "voice"),
            gr.Button(visible=not text_in),
            gr.Button(visible=text_in),
        )

    def on_start_over() -> tuple[Any, ...]:
        return (
            None,
            {},
            {},
            gr.HTML(value=""),
            gr.File(visible=False),
            gr.Tabs(selected="add"),
            gr.Tab(interactive=False),
            gr.Tab(interactive=False),
        )

    with gr.Blocks(title="LessonLingo") as app:
        gr.HTML(HERO_HTML, padding=False)
        status = gr.Markdown(elem_id="ll-status")
        with gr.Tabs(elem_id="shell") as tabs:
            with gr.Tab("1 Add", id="add"):
                with gr.Column(elem_classes="page"):
                    page_head("Add")
                    kind = gr.Radio(
                        label="What do you want to translate?",
                        choices=KIND_CHOICES,
                        value="video",
                        elem_classes="lang-chips",
                    )
                    with gr.Column(visible=False) as text_col:
                        text = gr.Textbox(
                            label="Text",
                            value=DEFAULT_TEXT,
                            lines=9,
                            placeholder="Paste English text here",
                        )
                        upload = gr.File(
                            label="or a file (.md, .txt)",
                            file_types=[".md", ".markdown", ".txt"],
                            type="filepath",
                        )
                    with gr.Column() as file_col:
                        v_upload = gr.File(
                            label="Video file",
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
                                "Try the sample lecture", size="sm", elem_classes="link-button"
                            )
                            v_sample.click(lambda: str(SAMPLE_LECTURE), None, v_upload)
                    with gr.Row(elem_classes="nav-bar"):
                        add_next = gr.Button("Next", variant="primary", size="lg")

            with gr.Tab("2 Languages", id="lang"):
                with gr.Column(elem_classes="page"):
                    page_head("Languages")
                    targets = gr.CheckboxGroup(
                        label="Translate into",
                        info="Languages marked voice can also be spoken.",
                        choices=voice_choices,
                        value=["kan_Knda", "hin_Deva"],
                    )
                    with gr.Row(elem_classes="nav-bar"):
                        lang_back = gr.Button("Back", variant="secondary", size="lg")
                        lang_next = gr.Button("Next", variant="primary", size="lg")

            with gr.Tab("3 Options", id="opts"):
                with gr.Column(elem_classes="page"):
                    page_head("Options")
                    mode = gr.Radio(
                        label="Translation model",
                        info="200M is fast and runs anywhere. 1B is more accurate and needs an "
                        "NVIDIA graphics card.",
                        choices=MODE_CHOICES,
                        value="light",
                        elem_classes="lang-chips",
                    )
                    want = gr.Radio(
                        label="You get",
                        info="Voice is Hindi and Kannada only, and takes a few minutes longer.",
                        choices=[*WANT_VIDEO, WANT_OTHER[1]],
                        value="dub",
                        elem_classes="lang-chips",
                    )
                    voice_quality = gr.Radio(
                        label="Voice quality",
                        info="Natural sounds like a person. Quick is robotic but much faster.",
                        choices=[
                            ("Natural voice (slower)", "natural"),
                            ("Quick voice (robotic)", "quick"),
                        ],
                        value="natural",
                        elem_classes="lang-chips",
                    )
                    want_note = gr.Markdown(elem_classes="hint")
                    with gr.Accordion("Keep words in English", open=False):
                        keep = gr.Textbox(
                            show_label=False,
                            info="These words are never translated. Separate with commas.",
                            placeholder="photosynthesis, Python",
                        )
                        sheet = gr.File(
                            label="Glossary file (.csv)",
                            file_types=[".csv"],
                            type="filepath",
                        )
                    with gr.Row(elem_classes="nav-bar"):
                        opts_back = gr.Button("Back", variant="secondary", size="lg")
                        v_listen = gr.Button("Next", variant="primary", size="lg")
                        go = gr.Button("Translate", variant="primary", size="lg", visible=False)

            with gr.Tab("4 Check text", id="check", interactive=False) as t_check:
                with gr.Column(elem_classes="page"):
                    page_head("Check text", "Fix any mistake before it is translated.")
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
                    with gr.Row(elem_classes="nav-bar"):
                        check_back = gr.Button("Back", variant="secondary", size="lg")
                        v_go = gr.Button("Translate", variant="primary", size="lg")

            with gr.Tab("5 Result", id="result", interactive=False) as t_result:
                with gr.Column(elem_classes="page"):
                    page_head("Result")
                    with gr.Column(visible=True) as res_media:
                        v_done = gr.Markdown(elem_classes="hint")
                        with gr.Row(elem_classes="split"):
                            with gr.Column(scale=3, min_width=320):
                                v_player = gr.HTML(padding=False, elem_id="lecture-player")
                            with gr.Column(scale=2, min_width=300, elem_classes="side-card"):
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
                        v_final = gr.File(label="Your video, ready to share", visible=False)
                        v_files = gr.File(label="All files", file_count="multiple")
                    with gr.Column(visible=False) as res_text:
                        review_lang = gr.Radio(
                            label="Language", choices=[], elem_classes="lang-chips"
                        )
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
                        files = gr.File(label="Downloads", file_count="multiple")
                    with gr.Row(elem_classes="nav-bar"):
                        res_back = gr.Button("Back", variant="secondary", size="lg")
                        again = gr.Button("Start over", variant="primary", size="lg")
            v_heard = gr.State({})
            v_state = gr.State({})
            review_state = gr.State({})

            with gr.Tab("Courses", id="courses"):
                with gr.Column(elem_classes="page"):
                    page_head("Courses", "One folder per class, translated in one go.")
                    library = build_library_tab(
                        gr,
                        courses_home,
                        models,
                        transcriber_factory,
                        friendly_error,
                        language_choices,
                        MODE_CHOICES,
                    )

        top = SCROLL_TOP_JS
        for trigger in (kind.change, targets.change, want.change, voice_quality.change):
            trigger(voice_note, [kind, targets, want, voice_quality], want_note)
        for trigger in (kind.change, want.change):
            trigger(on_want, [kind, want], voice_quality)
        kind.change(on_kind, [kind, targets], [text_col, file_col, v_upload, want, v_listen, go])
        targets.change(refresh_want, [kind, targets, want], [want, voice_quality])
        add_next.click(check_add, [kind, text, upload, v_upload], tabs).then(
            None, None, None, js=top
        )
        lang_back.click(lambda: go_to("add"), None, tabs)
        lang_next.click(check_languages, [targets], tabs).then(None, None, None, js=top)
        opts_back.click(lambda: go_to("lang"), None, tabs)
        check_back.click(lambda: go_to("opts"), None, tabs)
        res_back.click(lambda: go_to("opts"), None, tabs)
        checked = [kind, text, upload, v_upload, targets, want]
        e_check = v_listen.click(check_options, checked, None, js=LOADING_LISTEN_JS)
        e_listen = e_check.success(
            on_listen,
            [v_upload, keep, sheet],
            [v_note, v_heard, v_table, tabs, t_check, status],
        )
        e_listen.then(None, None, None, js=LOADING_DONE_JS)
        e_video = v_go.click(
            on_translate_video,
            [v_upload, v_heard, v_table, targets, mode, keep, sheet, want, voice_quality],
            [
                v_files,
                v_state,
                v_lang,
                v_player,
                v_voice,
                v_done,
                tabs,
                t_result,
                res_media,
                res_text,
                status,
                v_final,
            ],
            js=LOADING_VIDEO_JS,
        )
        e_video.then(None, [v_lang, v_voice], None, js=AFTER_TRANSLATE_JS)
        v_lang.change(None, v_lang, None, js=SWITCH_TRACK_JS)
        v_voice.change(None, v_voice, None, js=VOICE_JS)
        e_text_check = go.click(check_options, checked, None, js=LOADING_TRANSLATE_JS)
        e_text = e_text_check.success(
            on_translate,
            [text, upload, targets, mode, keep, sheet],
            [
                files,
                review_state,
                review_lang,
                review_table,
                tabs,
                t_result,
                res_media,
                res_text,
                status,
            ],
        )
        e_text.then(None, None, None, js=LOADING_DONE_JS)
        cancel_button = gr.Button("cancel", elem_id="ll-cancel")
        cancel_button.click(
            on_cancel,
            None,
            None,
            cancels=[e_check, e_listen, e_video, e_text_check, e_text, library.translate_event],
        )
        review_lang.change(on_review_language, [review_state, review_lang], review_table)
        save_btn.click(on_save_review, [review_state, review_lang, review_table], edited)
        again.click(
            on_start_over,
            None,
            [v_upload, v_heard, v_state, v_player, edited, tabs, t_check, t_result],
        ).then(None, None, None, js=top)
        app.load(library.on_load, None, [library.course, *library.view])
        app.load(lambda: gr.Radio(choices=WANT_VIDEO, value="dub"), None, want)
        app.load(voice_note, [kind, targets, want, voice_quality], want_note)
        library.send.click(
            lambda course, name: (
                (
                    str(courses_home.course_path(course) / "lectures" / name),
                    gr.Radio(value="video"),
                    gr.Tabs(selected="lang"),
                    gr.Tab(interactive=False),
                    gr.Tab(interactive=False),
                )
                if course and name
                else (None, gr.Radio(), gr.Tabs(), gr.Tab(), gr.Tab())
            ),
            [library.course, library.item],
            [v_upload, kind, tabs, t_check, t_result],
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
        allowed_paths=[str(courses_home.root), str(APP_TEMP)],
        footer_links=[],
        head=LIGHT_HEAD,
    )
