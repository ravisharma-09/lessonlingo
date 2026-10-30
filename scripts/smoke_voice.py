"""Listen-test the voices: speak the same sentences with each engine and time them.

Run on the GPU laptop, after the voice setup in the README:
    python scripts/smoke_voice.py --engine both [--dtype bfloat16] [--offline]

Writes WAV files to outputs/voice_test/ so you can listen and choose the better engine.
"""

from __future__ import annotations

import argparse
import time
import wave
from array import array
from pathlib import Path

from lessonlingo.setup_models import enable_offline_mode
from lessonlingo.tts import IndicParlerSynthesizer, MMSSynthesizer, Synthesizer

SENTENCES = {
    "hin_Deva": [
        "जल भूमि, महासागरों और वायुमंडल के बीच घूमता है।",
        "पौधे सूर्य के प्रकाश का उपयोग करके अपना भोजन खुद बनाते हैं।",
        "कृपया अपनी पाठ्यपुस्तकों को पृष्ठ दस पर खोलें।",
    ],
    "kan_Knda": [
        "ನೀರು ಭೂಮಿ, ಸಾಗರಗಳು ಮತ್ತು ವಾತಾವರಣದ ನಡುವೆ ಚಲಿಸುತ್ತದೆ.",
        "ಸಸ್ಯಗಳು ಸೂರ್ಯನ ಬೆಳಕನ್ನು ಬಳಸಿಕೊಂಡು ತಮ್ಮದೇ ಆದ ಆಹಾರವನ್ನು ತಯಾರಿಸುತ್ತವೆ.",
        "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪಠ್ಯಪುಸ್ತಕಗಳನ್ನು ಪುಟ ಹತ್ತಕ್ಕೆ ತೆರೆಯಿರಿ.",
    ],
}


def write_wav(path: Path, samples: list[float], rate: int) -> None:
    """Write mono 16-bit speech samples to a WAV file."""

    pcm = array("h", (int(max(-1.0, min(1.0, s)) * 32767) for s in samples))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())


def run(name: str, synthesizer: Synthesizer, out: Path) -> None:
    """Speak every test sentence and print timing."""

    print(f"\n== {name}")
    for language, lines in SENTENCES.items():
        for number, text in enumerate(lines, start=1):
            started = time.perf_counter()
            samples, rate = synthesizer.synthesize(text, language)
            took = time.perf_counter() - started
            seconds = len(samples) / rate
            path = out / f"{name}_{language}_{number}.wav"
            write_wav(path, samples, rate)
            print(
                f"{language} line {number}: {seconds:4.1f}s of audio in {took:4.1f}s "
                f"(x{took / max(seconds, 0.01):.1f} real time) -> {path}"
            )
    try:
        import torch

        if torch.cuda.is_available():
            peak = torch.cuda.max_memory_allocated() / 1e9
            print(f"Peak GPU memory used by torch: {peak:.1f} GB")
    except ImportError:
        pass


def main() -> None:
    """Command-line entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("parler", "mms", "both"), default="both")
    parser.add_argument("--dtype", default="float32", help="float32, bfloat16 or float16")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("outputs/voice_test"))
    args = parser.parse_args()
    if args.offline:
        enable_offline_mode()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.engine in ("mms", "both"):
        voice = MMSSynthesizer()
        run("mms", voice, args.out)
        voice.close()
    if args.engine in ("parler", "both"):
        voice = IndicParlerSynthesizer(dtype=args.dtype)
        run("parler", voice, args.out)
        voice.close()
    print(f"\nListen to the files in {args.out} and tell me which sounds more like a person.")


if __name__ == "__main__":
    main()
