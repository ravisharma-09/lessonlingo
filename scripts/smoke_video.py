"""Run the lecture-video pipeline on a real clip with real models and time each stage.

Run on the GPU laptop after `lessonlingo setup`:
    python scripts/smoke_video.py lecture.mp4 [--offline] [--whisper-device cpu]
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from lessonlingo.setup_models import enable_offline_mode
from lessonlingo.video import FasterWhisperTranscriber, translate_video


def main() -> None:
    """Translate a clip into Kannada, Hindi and Tamil subtitles and print timings."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--mode", choices=("light", "quality"), default="light")
    parser.add_argument("--whisper", default="small")
    parser.add_argument("--whisper-device")
    parser.add_argument("--out", type=Path, default=Path("outputs"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.offline:
        enable_offline_mode()

    started = time.perf_counter()
    last = [started]

    def status(message: str) -> None:
        now = time.perf_counter()
        print(f"[{now - started:6.1f}s] (+{now - last[0]:5.1f}s) {message}")
        last[0] = now

    paths = translate_video(
        args.video,
        ["kan_Knda", "hin_Deva", "tam_Taml"],
        args.mode,
        args.out,
        transcriber=FasterWhisperTranscriber(args.whisper, args.whisper_device),
        status=status,
    )
    print(f"\nTotal: {time.perf_counter() - started:.1f}s")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
