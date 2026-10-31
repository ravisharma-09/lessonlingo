"""Lecture video to translated subtitles, running on the user's own machine.

Pipeline: ffmpeg extracts audio, faster-whisper transcribes English, the speech model is
freed, then IndicTrans2 translates each subtitle. Models are downloaded once during setup.
After that, no internet connection is needed.
"""

from __future__ import annotations

import gc
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from lessonlingo.languages import validate_targets
from lessonlingo.subtitles import Cue, load_subtitles, to_srt, to_vtt, with_text
from lessonlingo.translator import IndicTransTranslator, Mode, Translator

StatusCallback = Callable[[str], None]

DEFAULT_WHISPER_SIZE = "small"
SUBTITLE_SUFFIXES = {".srt", ".vtt"}
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".mp3", ".wav", ".m4a"}


DOUBTFUL_SCORE = -1.0
WEAK_WORD_PROBABILITY = 0.5  # a starting guess; tune it with scripts/show_scores.py


def is_doubtful(cue: Cue) -> bool:
    """True when speech recognition was unsure: a weak word, or a low average log-probability."""

    return bool(cue.weak_words) or (cue.score is not None and cue.score < DOUBTFUL_SCORE)


def weak_words_of(words: list[tuple[str, float]]) -> tuple[str, ...]:
    """Words whose recognition probability is below the threshold, without punctuation."""

    found = (
        word.strip(" ,.;:!?\"'()")
        for word, probability in words
        if probability < WEAK_WORD_PROBABILITY
    )
    return tuple(w for w in found if w)


def whisper_repository(size: str) -> str:
    """Hugging Face repository that holds the faster-whisper weights for a model size."""

    return f"Systran/faster-whisper-{size}"


class Transcriber(Protocol):
    """Turns an audio file into timed English subtitles."""

    def transcribe(self, audio_path: Path) -> list[Cue]:
        """Transcribe English speech into cues."""

    def close(self) -> None:
        """Release resources held by the transcriber."""


class FakeTranscriber:
    """Deterministic transcriber for tests and Mac development."""

    def __init__(self, cues: list[Cue] | None = None, hotwords: list[str] | None = None) -> None:
        """Use the given cues, or three short example lecture lines (one marked doubtful)."""

        self.hotwords = hotwords
        self.cues = cues or [
            Cue(0.0, 2.5, "Welcome to today's lesson.", -0.2),
            Cue(
                2.5, 6.0, "Water moves between the land, oceans, and atmosphere.", -0.4, ("oceans",)
            ),
            Cue(6.0, 9.0, "This is called the water cycle.", -0.3),
        ]

    def transcribe(self, audio_path: Path) -> list[Cue]:
        """Return the fixed cues."""

        return list(self.cues)

    def close(self) -> None:
        """Release resources; the fake has none."""


class FasterWhisperTranscriber:
    """English speech recognition with faster-whisper, loaded on first use."""

    def __init__(
        self,
        size: str = DEFAULT_WHISPER_SIZE,
        device: str | None = None,
        hotwords: list[str] | None = None,
    ) -> None:
        """Configure a Whisper model; `device` is cuda or cpu, `hotwords` are course terms."""

        self.size = size
        self.requested_device = device
        self.hotwords = hotwords or []
        self.device: str | None = None
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise RuntimeError(
                "faster-whisper is not installed. Run: python -m pip install -r requirements.txt"
            ) from error

        device = self.requested_device or self._detect_device()
        compute_type = "float16" if device == "cuda" else "int8"
        try:
            self._model = WhisperModel(self.size, device=device, compute_type=compute_type)
        except Exception:
            if device == "cpu":
                raise
            device = "cpu"  # the GPU libraries are missing: fall back to the CPU
            self._model = WhisperModel(self.size, device=device, compute_type="int8")
        self.device = device

    @staticmethod
    def _detect_device() -> str:
        """CPU unless LESSONLINGO_WHISPER_DEVICE=cuda: the GPU path needs extra NVIDIA libraries
        and can hang on a machine that lacks them, while int8 on the CPU always works."""

        forced = os.environ.get("LESSONLINGO_WHISPER_DEVICE", "").strip().lower()
        return forced if forced in ("cpu", "cuda") else "cpu"

    def transcribe(self, audio_path: Path) -> list[Cue]:
        """Transcribe English audio into timed cues."""

        self._load()
        segments, _info = self._model.transcribe(
            str(audio_path),
            language="en",
            vad_filter=True,
            hotwords=", ".join(self.hotwords) or None,
            word_timestamps=True,
        )
        return [
            Cue(
                s.start,
                s.end,
                s.text.strip(),
                s.avg_logprob,
                weak_words_of([(w.word, w.probability) for w in (s.words or [])]),
            )
            for s in segments
            if s.text.strip()
        ]

    def close(self) -> None:
        """Free the speech model and its GPU memory before translation starts."""

        self._model = None
        self.device = None
        gc.collect()


def ffmpeg_extract_command(video: Path, wav: Path) -> list[str]:
    """Build the ffmpeg command that writes 16 kHz mono WAV audio."""

    return ["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)]


def extract_audio(video: Path, wav: Path) -> None:
    """Extract audio with ffmpeg, with a clear message if ffmpeg is missing."""

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg was not found. Install it once (Windows: `winget install ffmpeg`, "
            "macOS: `brew install ffmpeg`) and open a new terminal."
        )
    result = subprocess.run(
        ffmpeg_extract_command(video, wav), capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg could not read that file: {result.stderr.strip()[-300:]}")


def _iso_language(code: str) -> str:
    """IndicTrans2 code (kan_Knda) to the ISO 639-2 tag players expect (kan)."""

    return {"ory": "ori"}.get(code[:3], code[:3])


def ffmpeg_embed_command(video: Path, subtitles: dict[str, Path], out: Path) -> list[str]:
    """Build the ffmpeg command that adds each subtitle file as a selectable mp4 track."""

    command = ["ffmpeg", "-y", "-i", str(video)]
    for path in subtitles.values():
        command += ["-i", str(path)]
    command += ["-map", "0:v", "-map", "0:a?"]
    for index in range(len(subtitles)):
        command += ["-map", str(index + 1)]
    command += ["-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text"]
    for index, code in enumerate(subtitles):
        command += [f"-metadata:s:s:{index}", f"language={_iso_language(code)}"]
    return command + [str(out)]


def embed_subtitles(video: Path, subtitles: dict[str, Path], out: Path) -> Path:
    """Write a copy of the video with every translated subtitle as a selectable track."""

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg was not found. Install it once, then try again.")
    result = subprocess.run(
        ffmpeg_embed_command(video, subtitles, out), capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg could not add subtitles: {result.stderr.strip()[-300:]}")
    return out


def translate_cues(
    cues: list[Cue],
    targets: list[str],
    translator: Translator,
    status: StatusCallback | None = None,
) -> dict[str, list[Cue]]:
    """Translate every cue into each target language, keeping timestamps."""

    texts = [cue.text for cue in cues]
    results: dict[str, list[Cue]] = {}
    for target in targets:
        if status:
            status(f"Translating {target}")
        results[target] = with_text(cues, translator.translate(texts, target))
    return results


def transcribe_lecture(
    path: Path,
    transcriber: Transcriber | None = None,
    status: StatusCallback | None = None,
) -> list[Cue]:
    """Get English cues from a video/audio file (speech recognition) or a .srt/.vtt file."""

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Lecture file not found: {source}")
    suffix = source.suffix.lower()
    if suffix not in SUBTITLE_SUFFIXES | VIDEO_SUFFIXES:
        raise ValueError("Use a video or audio file (.mp4, .mkv, .mp3 ...) or a .srt/.vtt file.")
    if suffix in SUBTITLE_SUFFIXES:
        return load_subtitles(source)

    speech = transcriber or FasterWhisperTranscriber()
    try:
        with tempfile.TemporaryDirectory(prefix="lessonlingo_") as work:
            wav = Path(work) / "audio.wav"
            if status:
                status("Extracting audio")
            extract_audio(source, wav)
            if status:
                status("Listening to the lecture")
            cues = speech.transcribe(wav)
    finally:
        speech.close()
    if not cues:
        raise RuntimeError("No speech was found in that file.")
    return cues


def translate_lecture(
    cues: list[Cue],
    stem: str,
    targets: list[str],
    mode: Mode,
    out_dir: Path,
    translator: Translator | None = None,
    status: StatusCallback | None = None,
) -> list[Path]:
    """Translate English cues and write `<stem>.en.srt` plus `.srt` and `.vtt` per language."""

    selected = validate_targets(targets)
    backend = translator or IndicTransTranslator(mode)
    try:
        translated = translate_cues(cues, selected, backend, status)
    finally:
        if translator is None:
            backend.close()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    transcript = out_dir / f"{stem}.en.srt"
    transcript.write_text(to_srt(cues), encoding="utf-8")
    written: list[Path] = [transcript]
    for target, target_cues in translated.items():
        for extension, render in ((".srt", to_srt), (".vtt", to_vtt)):
            path_out = out_dir / f"{stem}.{target}{extension}"
            path_out.write_text(render(target_cues), encoding="utf-8")
            written.append(path_out)
    if status:
        status("Done")
    return written


def translate_video(
    path: Path,
    targets: list[str],
    mode: Mode,
    out_dir: Path,
    transcriber: Transcriber | None = None,
    translator: Translator | None = None,
    status: StatusCallback | None = None,
) -> list[Path]:
    """Turn a lecture (video, audio, or existing .srt/.vtt) into one subtitle file per language.

    The speech model is freed before the translation model loads, so they never share the GPU.
    """

    validate_targets(targets)
    cues = transcribe_lecture(path, transcriber, status)
    return translate_lecture(
        cues, Path(path).stem, targets, mode, out_dir, translator=translator, status=status
    )
