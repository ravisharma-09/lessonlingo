"""Translate four fixed sentences with a real model and report device and speed.

Run on the GPU laptop after `lessonlingo setup`:
    python scripts/smoke.py [--mode light|quality] [--offline]
"""

from __future__ import annotations

import argparse
import time

from lessonlingo.setup_models import enable_offline_mode
from lessonlingo.translator import IndicTransTranslator, Mode

SENTENCES = [
    "Water moves between the land, oceans, and atmosphere.",
    "Plants make their own food using sunlight.",
    "Please open your textbooks to page ten.",
    "Is the experiment finished?",
]
TARGETS = ["hin_Deva", "kan_Knda", "tam_Taml"]


def measure(mode: Mode, show: bool = False) -> dict[str, float | str]:
    """Load the model, translate the fixed sentences, and return timings."""

    translator = IndicTransTranslator(mode)
    try:
        start = time.perf_counter()
        translator.translate(SENTENCES[:1], TARGETS[0])
        load_seconds = time.perf_counter() - start

        start = time.perf_counter()
        for target in TARGETS:
            outputs = translator.translate(SENTENCES, target)
            if show:
                print(f"\n{target}")
                for source, output in zip(SENTENCES, outputs, strict=True):
                    print(f"  {source}\n  -> {output}")
        elapsed = time.perf_counter() - start
        return {
            "device": translator.device or "unknown",
            "load_seconds": load_seconds,
            "seconds_per_sentence": elapsed / (len(SENTENCES) * len(TARGETS)),
        }
    finally:
        translator.close()


def main() -> None:
    """Print a smoke-test report."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("light", "quality"), default="light")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.offline:
        enable_offline_mode()

    result = measure(args.mode, show=True)
    print(f"\nmode={args.mode} device={result['device']}")
    print(f"load+first sentence: {result['load_seconds']:.1f}s")
    print(f"seconds per sentence: {result['seconds_per_sentence']:.2f}s")


if __name__ == "__main__":
    main()
