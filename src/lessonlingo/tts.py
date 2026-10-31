"""Optional spoken dubbing: turn translated subtitles into an audio track.

Two voice engines run locally. Indic Parler-TTS (AI4Bharat) sounds like a real person; it needs
the optional `parler-tts` package and its gated model. Meta MMS-TTS is the simpler fallback with
no extra package, but it sounds robotic and its licence (CC-BY-NC 4.0) is non-commercial only.
Dubbing is off by default and the voices are downloaded separately with `lessonlingo setup`.
"""

from __future__ import annotations

import importlib.util
import subprocess
import wave
from array import array
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from lessonlingo.subtitles import Cue, load_subtitles

# IndicTrans2 language code -> ISO 639-3 suffix of the facebook/mms-tts-<code> repository.
# Not every repository was checked; a missing one fails with a clear message.
VOICE_SUFFIX = {
    "hin_Deva": "hin",
    "kan_Knda": "kan",
    "tam_Taml": "tam",
    "tel_Telu": "tel",
    "mal_Mlym": "mal",
    "ben_Beng": "ben",
    "mar_Deva": "mar",
    "guj_Gujr": "guj",
    "pan_Guru": "pan",
    "ory_Orya": "ory",
}
# Languages whose voices we test and offer. The others are skipped with a note.
VOICE_LANGUAGES = ("hin_Deva", "kan_Knda")
VOICE_ENGINES = ("auto", "parler", "mms")
PARLER_REPOSITORY = "ai4bharat/indic-parler-tts"
# Default speakers from the model card (names to be confirmed on the card once access is granted).
PARLER_SPEAKERS = {"hin_Deva": "Divya", "kan_Knda": "Anu"}
PARLER_DESCRIPTION = (
    "{speaker}'s voice is clear and warm, speaking at a moderate pace with a calm tone. "
    "The recording is very clear, with no background noise."
)
MAX_SPEEDUP = 1.5
TAIL_SECONDS = 1.0
SILENCE_LEVEL = 400  # samples quieter than this (of 32767) count as silence at a clip's edges
EDGE_PAD_SECONDS = 0.04
EARLY_SECONDS = 0.3  # a clip that still will not fit may start this much before its cue
GAP_SECONDS = 0.15  # pause kept before the next cue when a clip borrows the gap after its cue


def voice_repository(language: str) -> str:
    """Hugging Face repository of the voice for an IndicTrans2 language code."""

    if language not in VOICE_SUFFIX:
        raise ValueError(f"No voice is known for {language}.")
    return f"facebook/mms-tts-{VOICE_SUFFIX[language]}"


class Synthesizer(Protocol):
    """Turns a sentence into speech samples."""

    def synthesize(self, text: str, language: str) -> tuple[list[float], int]:
        """Return (samples between -1 and 1, sample rate in Hz)."""

    def close(self) -> None:
        """Release resources held by the voice model."""


class FakeSynthesizer:
    """Deterministic stand-in for tests: a soft tone whose length follows the text length."""

    RATE = 16_000
    engine_name = "test voice"

    def synthesize(self, text: str, language: str) -> tuple[list[float], int]:
        """Return 0.05 seconds of tone per character."""

        count = int(self.RATE * 0.05 * len(text))
        return [0.2 if (i // 40) % 2 else -0.2 for i in range(count)], self.RATE

    def close(self) -> None:
        """Release resources; the fake has none."""


class MMSSynthesizer:
    """Meta MMS-TTS voices, loaded the first time each language is needed."""

    engine_name = "Meta MMS (robotic, non-commercial)"

    def __init__(self, device: str | None = None) -> None:
        """Use `device` (cuda or cpu), or cuda when available."""

        self.requested_device = device
        self._loaded: dict[str, tuple[object, object]] = {}
        self._torch = None
        self.device: str | None = None

    def _load(self, language: str) -> tuple[object, object]:
        if language in self._loaded:
            return self._loaded[language]
        try:
            import torch
            from transformers import AutoTokenizer, VitsModel
        except ImportError as error:
            raise RuntimeError(
                "Voices need torch and transformers. Run: python -m pip install -r requirements.txt"
            ) from error
        repository = voice_repository(language)
        self._torch = torch
        self.device = self.requested_device or ("cuda" if torch.cuda.is_available() else "cpu")
        try:
            tokenizer = AutoTokenizer.from_pretrained(repository)
            model = VitsModel.from_pretrained(repository).to(self.device)
        except OSError as error:
            raise RuntimeError(
                f"The voice {repository} is not downloaded. While online, run "
                f"`lessonlingo setup --voices {language}`."
            ) from error
        model.eval()
        self._loaded[language] = (tokenizer, model)
        return tokenizer, model

    def synthesize(self, text: str, language: str) -> tuple[list[float], int]:
        """Speak one sentence in the language's voice."""

        tokenizer, model = self._load(language)
        torch = self._torch
        inputs = tokenizer(text, return_tensors="pt").to(self.device)
        torch.manual_seed(0)  # the voice model is random; a fixed seed repeats the same audio
        with torch.no_grad():
            waveform = model(**inputs).waveform[0]
        return waveform.cpu().tolist(), int(model.config.sampling_rate)

    def close(self) -> None:
        """Free voice memory, including cached CUDA allocations."""

        self._loaded.clear()
        if self._torch is not None and self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()


def parler_installed() -> bool:
    """True when the optional `parler_tts` package can be imported."""

    return importlib.util.find_spec("parler_tts") is not None


class IndicParlerSynthesizer:
    """Indic Parler-TTS: natural human voices with named speakers, loaded on first use."""

    engine_name = "Indic Parler-TTS"

    def __init__(self, device: str | None = None, dtype: str = "float32") -> None:
        """Use `device` (cuda or cpu) and a torch dtype name such as float32 or bfloat16."""

        self.requested_device = device
        self.dtype_name = dtype
        self._model: object | None = None
        self._tokenizer: object | None = None
        self._description_tokenizer: object | None = None
        self._torch = None
        self.device: str | None = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from parler_tts import ParlerTTSForConditionalGeneration
            from transformers import AutoTokenizer
        except ImportError as error:
            raise RuntimeError(
                "The natural voice needs an extra package. While online, run: "
                "python -m pip install -r requirements-voice.txt"
            ) from error
        self._torch = torch
        self.device = self.requested_device or ("cuda" if torch.cuda.is_available() else "cpu")
        try:
            model = ParlerTTSForConditionalGeneration.from_pretrained(
                PARLER_REPOSITORY, torch_dtype=getattr(torch, self.dtype_name)
            ).to(self.device)
            self._tokenizer = AutoTokenizer.from_pretrained(PARLER_REPOSITORY)
            self._description_tokenizer = AutoTokenizer.from_pretrained(
                model.config.text_encoder._name_or_path
            )
        except OSError as error:
            raise RuntimeError(
                f"The voice {PARLER_REPOSITORY} is not available. While online, accept its "
                f"terms at https://huggingface.co/{PARLER_REPOSITORY}, log in with "
                "`hf auth login`, then run `lessonlingo setup --voices hin_Deva kan_Knda "
                "--voice-engine parler`."
            ) from error
        model.eval()
        self._model = model

    def synthesize(self, text: str, language: str) -> tuple[list[float], int]:
        """Speak one sentence with the language's default speaker."""

        if language not in PARLER_SPEAKERS:
            raise ValueError(f"No natural voice is set up for {language}.")
        self._load()
        torch, model = self._torch, self._model
        description = PARLER_DESCRIPTION.format(speaker=PARLER_SPEAKERS[language])
        desc = self._description_tokenizer(description, return_tensors="pt").to(self.device)
        prompt = self._tokenizer(text, return_tensors="pt").to(self.device)
        torch.manual_seed(0)  # the same line always sounds the same
        with torch.no_grad():
            try:
                audio = model.generate(
                    input_ids=desc.input_ids,
                    attention_mask=desc.attention_mask,
                    prompt_input_ids=prompt.input_ids,
                    prompt_attention_mask=prompt.attention_mask,
                )
            except TypeError:  # older call style without attention masks
                audio = model.generate(input_ids=desc.input_ids, prompt_input_ids=prompt.input_ids)
        return audio.cpu().float().numpy().squeeze().tolist(), int(model.config.sampling_rate)

    def close(self) -> None:
        """Free voice memory, including cached CUDA allocations."""

        self._model = self._tokenizer = self._description_tokenizer = None
        if self._torch is not None and self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()


class AutoSynthesizer:
    """Use the natural voice when it is installed and downloaded, otherwise the MMS voice."""

    def __init__(self) -> None:
        """Start with Parler when its package is installed, else MMS."""

        self._inner: Synthesizer = (
            IndicParlerSynthesizer() if parler_installed() else MMSSynthesizer()
        )
        self.engine_name = getattr(self._inner, "engine_name", "")

    def synthesize(self, text: str, language: str) -> tuple[list[float], int]:
        """Speak with Parler; if it cannot load, switch to MMS once and carry on."""

        try:
            return self._inner.synthesize(text, language)
        except RuntimeError:
            if isinstance(self._inner, MMSSynthesizer):
                raise
            self._inner.close()
            self._inner = MMSSynthesizer()
            self.engine_name = self._inner.engine_name
            return self._inner.synthesize(text, language)

    def close(self) -> None:
        """Close whichever voice is loaded."""

        self._inner.close()


def make_synthesizer(engine: str = "auto") -> Synthesizer:
    """Build the voice engine: auto, parler or mms."""

    if engine == "parler":
        return IndicParlerSynthesizer()
    if engine == "mms":
        return MMSSynthesizer()
    if engine == "auto":
        return AutoSynthesizer()
    raise ValueError(f"Unknown voice engine: {engine}")


def _to_pcm(samples: list[float]) -> array:
    return array("h", (int(max(-1.0, min(1.0, s)) * 32767) for s in samples))


def _speed_up(pcm: array, factor: float) -> array:
    """Play a clip `factor` times faster by resampling (the pitch rises slightly)."""

    length = int(len(pcm) / factor)
    out = array("h", bytes(2 * length))
    for i in range(length):
        position = i * factor
        low = int(position)
        high = min(low + 1, len(pcm) - 1)
        fraction = position - low
        out[i] = int(pcm[low] * (1 - fraction) + pcm[high] * fraction)
    return out


def _trim_silence(pcm: array, rate: int) -> array:
    """Cut the quiet stretch at both ends of a spoken clip (voice models pad their output)."""

    loud = [i for i, sample in enumerate(pcm) if abs(sample) > SILENCE_LEVEL]
    if not loud:
        return pcm
    pad = int(EDGE_PAD_SECONDS * rate)
    return pcm[max(loud[0] - pad, 0) : min(loud[-1] + pad, len(pcm))]


def _time_stretch(pcm: array, rate: int, factor: float) -> array:
    """Make a clip `factor` times faster without raising the pitch, using ffmpeg's atempo.

    atempo is a time-stretch filter that ships with ffmpeg, which the lecture pipeline needs
    anyway. If ffmpeg cannot do it, the plain resampling speed-up is used instead.
    """

    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "s16le", "-ar", str(rate),
        "-ac", "1", "-i", "pipe:0", "-filter:a", f"atempo={factor:.4f}",
        "-f", "s16le", "-ar", str(rate), "-ac", "1", "pipe:1",
    ]  # fmt: skip
    try:
        result = subprocess.run(
            command, input=pcm.tobytes(), capture_output=True, check=False, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return _speed_up(pcm, factor)
    if result.returncode != 0 or len(result.stdout) < 2:
        return _speed_up(pcm, factor)
    out = array("h")
    out.frombytes(result.stdout[: len(result.stdout) // 2 * 2])
    return out


def render_dub(
    cues: list[Cue],
    language: str,
    synthesizer: Synthesizer,
    out_path: Path,
    on_line: Callable[[int, int], None] | None = None,
) -> tuple[Path, float]:
    """Speak every cue at its start time and write one mono WAV file.

    Each clip is trimmed of its leading and trailing silence. A clip longer than its slot may
    use the pause before the next cue, then is time-stretched (pitch kept) by at most 1.5 times.
    If it still does not fit it starts up to 0.3 s early, and only after that do the next clips
    start later instead of overlapping, so the voice can fall slightly behind the picture.
    Returns (path, the largest delay in seconds).
    """

    spoken: list[tuple[Cue, array]] = []
    rate = 0
    speakable = [cue for cue in cues if cue.text.strip()]
    for done, cue in enumerate(speakable, start=1):
        samples, rate = synthesizer.synthesize(cue.text, language)
        if samples:
            spoken.append((cue, _trim_silence(_to_pcm(samples), rate)))
        if on_line:
            on_line(done, len(speakable))
    if not spoken:
        raise RuntimeError("There was nothing to speak.")

    placed: list[tuple[int, array]] = []
    cursor = 0
    largest_delay = 0.0
    for index, (cue, pcm) in enumerate(spoken):
        start = int(cue.start * rate)
        end = cue.end
        if index + 1 < len(spoken):
            end = max(end, min(spoken[index + 1][0].start - GAP_SECONDS, end + 1.5))
        slot = max(int((end - cue.start) * rate), 1)
        if len(pcm) > slot:
            pcm = _time_stretch(pcm, rate, min(len(pcm) / slot, MAX_SPEEDUP))
        position = max(start, cursor)
        if len(pcm) > slot:
            position = max(start - int(EARLY_SECONDS * rate), cursor)
        largest_delay = max(largest_delay, (position - start) / rate)
        placed.append((position, pcm))
        cursor = position + len(pcm)

    total = max(cursor, int(max(c.end for c in cues) * rate)) + int(TAIL_SECONDS * rate)
    track = array("h", bytes(2 * total))
    for position, pcm in placed:
        track[position : position + len(pcm)] = pcm

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(track.tobytes())
    return out_path, largest_delay


def ffmpeg_dub_command(
    video: Path,
    tracks: dict[str, Path],
    out: Path,
    has_audio: bool = True,
    subtitles: dict[str, Path] | None = None,
) -> list[str]:
    """Build the ffmpeg command that adds each spoken track to the video as an audio stream.

    With `subtitles`, every subtitle file is added too as a selectable mp4 text track.
    """

    subtitles = subtitles or {}
    command = ["ffmpeg", "-y", "-i", str(video)]
    for path in [*tracks.values(), *subtitles.values()]:
        command += ["-i", str(path)]
    command += ["-map", "0:v", "-map", "0:a?"]
    for index in range(len(tracks) + len(subtitles)):
        command += ["-map", str(index + 1)]
    command += ["-c:v", "copy", "-c:a", "aac"]
    if subtitles:
        from lessonlingo.video import _iso_language

        command += ["-c:s", "mov_text"]
        for index, code in enumerate(subtitles):
            command += [f"-metadata:s:s:{index}", f"language={_iso_language(code)}"]
    offset = 1 if has_audio else 0
    for index, code in enumerate(tracks):
        iso = {"ory": "ori"}.get(code[:3], code[:3])
        command += [f"-metadata:s:a:{index + offset}", f"language={iso}"]
        command += [f"-metadata:s:a:{index + offset}", f"title=Dubbed {code}"]
    return command + [str(out)]


def add_dubbed_audio(
    video: Path,
    tracks: dict[str, Path],
    out: Path,
    subtitles: dict[str, Path] | None = None,
) -> Path:
    """Write a copy of the video that keeps the original sound and adds the spoken tracks.

    Given `subtitles`, the same file also carries every subtitle language as a text track.
    """

    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(video)], capture_output=True, text=True, check=False
    )
    result = subprocess.run(
        ffmpeg_dub_command(
            video, tracks, out, has_audio="Audio:" in probe.stderr, subtitles=subtitles
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg could not add the dubbed audio: {result.stderr.strip()[-300:]}")
    return out


VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}


def add_voice_only(video: Path, wav: Path, out: Path) -> Path:
    """Write a copy of the video whose only sound is the dubbed voice (one file per language)."""

    command = [
        "ffmpeg", "-y", "-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-shortest", str(out),
    ]  # fmt: skip
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg could not make the dubbed video: {result.stderr.strip()[-300:]}"
        )
    return out


def dub_subtitles(
    srt_files: list[Path],
    source: Path | None,
    out_dir: Path,
    synthesizer: Synthesizer,
    note: Callable[[str], None] | None = None,
    subtitles_in_video: bool = False,
) -> list[Path]:
    """Speak translated subtitle files; also make dubbed videos when `source` is a video.

    Files named `<stem>.<language code>.srt` get a `<stem>.<language code>.wav`. Only the
    languages in VOICE_LANGUAGES are spoken; the English transcript and other languages are
    skipped. For a video you also get `<stem>.<code>.dubbed.mp4` (the voice only) per language
    and `<stem>.dubbed.mp4` (original sound plus every voice as extra tracks). The synthesizer
    is closed at the end. Returns the files written.
    """

    out_dir = Path(out_dir)
    tracks: dict[str, Path] = {}
    written: list[Path] = []
    try:
        for srt in srt_files:
            code = srt.name.split(".")[-2]
            if code not in VOICE_SUFFIX:
                continue
            if code not in VOICE_LANGUAGES:
                if note:
                    note(f"No tested voice for {code} yet, so it was not spoken.")
                continue
            wav, delay = render_dub(
                load_subtitles(srt),
                code,
                synthesizer,
                out_dir / f"{srt.stem}.wav",
                on_line=(lambda done, total, c=code: note(f"Speaking {c} {done}/{total}"))
                if note
                else None,
            )
            written.append(wav)
            tracks[code] = wav
            if delay > 1 and note:
                note(f"The {code} voice runs up to {delay:.1f}s behind the picture.")
    finally:
        synthesizer.close()
    if source is not None and source.suffix.lower() in VIDEO_SUFFIXES and tracks:
        for code, wav in tracks.items():
            written.append(
                add_voice_only(source, wav, out_dir / f"{source.stem}.{code}.dubbed.mp4")
            )
        subtitle_tracks = {}
        if subtitles_in_video:
            subtitle_tracks = {
                srt.name.split(".")[-2]: srt for srt in srt_files if srt.name.split(".")[-2] != "en"
            }
        written.append(
            add_dubbed_audio(
                source, tracks, out_dir / f"{source.stem}.dubbed.mp4", subtitles=subtitle_tracks
            )
        )
    return written
