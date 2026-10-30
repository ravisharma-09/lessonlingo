"""LessonLingo command-line interface."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

from lessonlingo.glossary import GlossaryTranslator
from lessonlingo.languages import SUPPORTED_LANGUAGES
from lessonlingo.pipeline import translate_file, translate_folder
from lessonlingo.setup_models import enable_offline_mode, run_setup, run_verify
from lessonlingo.translator import IndicTransTranslator, Translator

OFFLINE_HELP = (
    "never contact the internet (also set by LESSONLINGO_OFFLINE=1); "
    "models must already be downloaded by `lessonlingo setup`"
)


KEEP_HELP = "words to keep in English, for example --keep photosynthesis Python"


def _offline_requested(flag: bool) -> bool:
    return flag or os.environ.get("LESSONLINGO_OFFLINE") == "1"


def build_parser() -> argparse.ArgumentParser:
    """Build the LessonLingo command-line parser."""

    parser = argparse.ArgumentParser(
        prog="lessonlingo",
        description="Free lessons in your language. Set up once, then no internet needed.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    translate_parser = subparsers.add_parser(
        "translate",
        help="translate a Markdown or text lesson after one-time setup",
    )
    translate_parser.add_argument(
        "file", type=Path, help="English .md or .txt lesson, or a folder of lessons"
    )
    translate_parser.add_argument(
        "--to",
        nargs="+",
        required=True,
        choices=SUPPORTED_LANGUAGES,
        metavar="LANG",
        help="one or more IndicTrans2 target language codes",
    )
    translate_parser.add_argument(
        "--mode",
        choices=("quality", "light"),
        default="light",
        help="quality uses the 1B GPU model; light uses the 200M model",
    )
    translate_parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs"),
        help="output directory (default: outputs)",
    )
    translate_parser.add_argument("--offline", action="store_true", help=OFFLINE_HELP)
    translate_parser.add_argument("--keep", nargs="+", default=[], metavar="TERM", help=KEEP_HELP)
    translate_parser.add_argument("--device", help="override automatic cuda/cpu selection")
    translate_parser.add_argument("--batch-size", type=int, help="override the mode batch size")

    video_parser = subparsers.add_parser(
        "video",
        help="turn a lecture video (or .srt/.vtt) into translated subtitles",
    )
    video_parser.add_argument("file", type=Path, help="English lecture video/audio or .srt/.vtt")
    video_parser.add_argument(
        "--to", nargs="+", required=True, choices=SUPPORTED_LANGUAGES, metavar="LANG"
    )
    video_parser.add_argument("--mode", choices=("quality", "light"), default="light")
    video_parser.add_argument(
        "--whisper", default="small", help="speech model size (default: small)"
    )
    video_parser.add_argument("--whisper-device", help="cuda or cpu for speech recognition")
    video_parser.add_argument("--out", type=Path, default=Path("outputs"))
    video_parser.add_argument("--offline", action="store_true", help=OFFLINE_HELP)
    video_parser.add_argument("--keep", nargs="+", default=[], metavar="TERM", help=KEEP_HELP)

    app_parser = subparsers.add_parser("app", help="open the web interface on this computer")
    app_parser.add_argument("--port", type=int, default=7860, help="port (default: 7860)")
    app_parser.add_argument("--offline", action="store_true", help=OFFLINE_HELP)

    setup_parser = subparsers.add_parser(
        "setup",
        help="download models once for later translation without internet",
    )
    setup_parser.add_argument(
        "--cache-dir",
        type=Path,
        help="use a specific Hugging Face cache directory",
    )

    verify_parser = subparsers.add_parser(
        "verify",
        help="verify that setup completed using only the local cache",
    )
    verify_parser.add_argument(
        "--cache-dir",
        type=Path,
        help="use a specific Hugging Face cache directory",
    )

    subparsers.add_parser("languages", help="list supported target language codes")
    return parser


def _progress(completed: int, total: int, target: str) -> None:
    print(f"Translated {target} ({completed}/{total})")


def _run_translate(args: argparse.Namespace, translator: Translator | None) -> int:
    inner = translator or IndicTransTranslator(
        args.mode,
        device=args.device,
        batch_size=args.batch_size,
    )
    backend = GlossaryTranslator(inner, args.keep) if args.keep else inner
    owns_backend = translator is None
    try:
        run = translate_folder if args.file.is_dir() else translate_file
        paths = run(
            args.file,
            args.to,
            args.mode,
            args.out,
            translator=backend,
            progress_cb=_progress,
        )
    finally:
        if owns_backend:
            backend.close()

    for output_path in paths:
        print(output_path)
    return 0


def _run_video(args: argparse.Namespace, translator: Translator | None) -> int:
    from lessonlingo.video import FasterWhisperTranscriber, translate_video

    inner = translator or IndicTransTranslator(args.mode)
    backend = GlossaryTranslator(inner, args.keep) if args.keep else inner
    try:
        paths = translate_video(
            args.file,
            args.to,
            args.mode,
            args.out,
            transcriber=FasterWhisperTranscriber(args.whisper, args.whisper_device),
            translator=backend,
            status=print,
        )
    finally:
        if translator is None:
            backend.close()
    for output_path in paths:
        print(output_path)
    return 0


def main(
    argv: Sequence[str] | None = None,
    translator: Translator | None = None,
) -> int:
    """Run LessonLingo, optionally injecting a fake translator for tests."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in {"translate", "app", "video"} and _offline_requested(args.offline):
            enable_offline_mode()
        if args.command == "app":
            from lessonlingo.app import launch

            launch(port=args.port)
            return 0
        if args.command == "video":
            return _run_video(args, translator)
        if args.command == "translate":
            return _run_translate(args, translator)
        if args.command == "setup":
            return run_setup(args.cache_dir)
        if args.command == "verify":
            return run_verify(args.cache_dir)
        for code, name in SUPPORTED_LANGUAGES.items():
            print(f"{code}\t{name}")
        return 0
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        parser.exit(2, f"lessonlingo: error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
