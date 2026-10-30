"""Print every speech segment with its confidence numbers, to tune the "Check" threshold.

Run on the GPU laptop:
    python scripts/show_scores.py samples/lecture_demo.mp4 [--size small|medium] [--offline]

Compare the numbers of lines that are wrong with lines that are right, then send the output.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from lessonlingo.setup_models import enable_offline_mode
from lessonlingo.video import DOUBTFUL_SCORE, extract_audio


def main() -> None:
    """Transcribe a file and print avg_logprob, no_speech_prob and compression_ratio per line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--size", default="small")
    parser.add_argument("--device", default=None)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.offline:
        enable_offline_mode()

    from faster_whisper import WhisperModel

    device = args.device or "cuda"
    model = WhisperModel(
        args.size, device=device, compute_type="float16" if device == "cuda" else "int8"
    )
    with tempfile.TemporaryDirectory() as work:
        wav = Path(work) / "audio.wav"
        extract_audio(args.video, wav)
        segments, _ = model.transcribe(str(wav), language="en", vad_filter=True)
        print(f"Current Check threshold: avg_logprob < {DOUBTFUL_SCORE}\n")
        for segment in segments:
            flag = "CHECK" if segment.avg_logprob < DOUBTFUL_SCORE else "     "
            print(
                f"{flag} logprob={segment.avg_logprob:6.2f} "
                f"no_speech={segment.no_speech_prob:4.2f} "
                f"compress={segment.compression_ratio:4.2f} | {segment.text.strip()}"
            )


if __name__ == "__main__":
    main()
