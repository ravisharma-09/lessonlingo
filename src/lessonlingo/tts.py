"""Optional spoken dubbing: turn translated subtitles into an audio track.

Voices are Meta MMS-TTS models, run locally through the `transformers` library that is already
installed. Their licence (CC-BY-NC 4.0) allows non-commercial use only, so dubbing is off by
default and the voices are downloaded separately with `lessonlingo setup --voices`.
"""

from __future__ import annotations

import subprocess
import wave
from array import array
from pathlib import Path
from typing import Protocol

from lessonlingo.subtitles import Cue

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
MAX_SPEEDUP = 1.3
TAIL_SECONDS = 1.0


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

    def synthesize(self, text: str, language: str) -> tuple[list[float], int]:
        """Return 0.05 seconds of tone per character."""

        count = int(self.RATE * 0.05 * len(text))
        return [0.2 if (i // 40) % 2 else -0.2 for i in range(count)], self.RATE

    def close(self) -> None:
        """Release resources; the fake has none."""


class MMSSynthesizer:
    """Meta MMS-TTS voices, loaded the first time each language is needed."""

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


def render_dub(
    cues: list[Cue], language: str, synthesizer: Synthesizer, out_path: Path
) -> tuple[Path, float]:
    """Speak every cue at its start time and write one mono WAV file.

    A clip longer than its slot is sped up by at most 1.3 times. If it is still too long, the
    next clips start later instead of overlapping, so the voice can fall slightly behind the
    picture. Returns (path, the largest delay in seconds).
    """

    clips: list[tuple[float, float, array]] = []
    rate = 0
    for cue in cues:
        if not cue.text.strip():
            continue
        samples, rate = synthesizer.synthesize(cue.text, language)
        if samples:
            clips.append((cue.start, cue.end, _to_pcm(samples)))
    if not clips:
        raise RuntimeError("There was nothing to speak.")

    placed: list[tuple[int, array]] = []
    cursor = 0
    largest_delay = 0.0
    for start, end, pcm in clips:
        slot = max(int((end - start) * rate), 1)
        if len(pcm) > slot:
            pcm = _speed_up(pcm, min(len(pcm) / slot, MAX_SPEEDUP))
        position = max(int(start * rate), cursor)
        largest_delay = max(largest_delay, (position - int(start * rate)) / rate)
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
    video: Path, tracks: dict[str, Path], out: Path, has_audio: bool = True
) -> list[str]:
    """Build the ffmpeg command that adds each spoken track to the video as an audio stream."""

    command = ["ffmpeg", "-y", "-i", str(video)]
    for path in tracks.values():
        command += ["-i", str(path)]
    command += ["-map", "0:v", "-map", "0:a?"]
    for index in range(len(tracks)):
        command += ["-map", str(index + 1)]
    command += ["-c:v", "copy", "-c:a", "aac"]
    offset = 1 if has_audio else 0
    for index, code in enumerate(tracks):
        iso = {"ory": "ori"}.get(code[:3], code[:3])
        command += [f"-metadata:s:a:{index + offset}", f"language={iso}"]
        command += [f"-metadata:s:a:{index + offset}", f"title=Dubbed {code}"]
    return command + [str(out)]


def add_dubbed_audio(video: Path, tracks: dict[str, Path], out: Path) -> Path:
    """Write a copy of the video that keeps the original sound and adds the spoken tracks."""

    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(video)], capture_output=True, text=True, check=False
    )
    result = subprocess.run(
        ffmpeg_dub_command(video, tracks, out, has_audio="Audio:" in probe.stderr),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg could not add the dubbed audio: {result.stderr.strip()[-300:]}")
    return out
