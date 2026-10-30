"""LessonLingo command-line interface."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Sequence
from pathlib import Path

from lessonlingo.glossary import GlossaryTranslator, load_glossary
from lessonlingo.languages import SUPPORTED_LANGUAGES
from lessonlingo.pack import make_class_pack
from lessonlingo.pipeline import translate_file, translate_folder
from lessonlingo.setup_models import enable_offline_mode, run_setup, run_verify
from lessonlingo.translator import IndicTransTranslator, Translator
from lessonlingo.tts import VOICE_ENGINES, Synthesizer, dub_subtitles, make_synthesizer
from lessonlingo.video import FasterWhisperTranscriber, Transcriber
from lessonlingo.workspace import DEFAULT_TARGETS, Workspace

OFFLINE_HELP = (
    "never contact the internet (also set by LESSONLINGO_OFFLINE=1); "
    "models must already be downloaded by `lessonlingo setup`"
)


KEEP_HELP = "words to keep in English, for example --keep photosynthesis Python"
GLOSSARY_HELP = "course glossary CSV: term, then one column per language with the exact word to use"
ZIP_HELP = "also write a .classpack.zip that is easy to share on a pen drive"


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
    translate_parser.add_argument("--glossary", type=Path, help=GLOSSARY_HELP)
    translate_parser.add_argument("--zip", action="store_true", help=ZIP_HELP)
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
    video_parser.add_argument(
        "--embed",
        action="store_true",
        help="also write <name>.subtitled.mp4 with every language as a selectable subtitle track",
    )
    video_parser.add_argument(
        "--dub",
        action="store_true",
        help="also speak the translation in Hindi and Kannada (see the README voice setup)",
    )
    video_parser.add_argument(
        "--voice-engine",
        choices=VOICE_ENGINES,
        default="auto",
        help="auto uses the natural Indic Parler-TTS voice when installed, else Meta MMS",
    )
    video_parser.add_argument("--offline", action="store_true", help=OFFLINE_HELP)
    video_parser.add_argument("--keep", nargs="+", default=[], metavar="TERM", help=KEEP_HELP)
    video_parser.add_argument("--glossary", type=Path, help=GLOSSARY_HELP)
    video_parser.add_argument("--zip", action="store_true", help=ZIP_HELP)

    app_parser = subparsers.add_parser("app", help="open the web interface on this computer")
    app_parser.add_argument("--port", type=int, default=7860, help="port (default: 7860)")
    app_parser.add_argument(
        "--warm",
        choices=("light", "quality"),
        help="load this model at start so the first translation is fast",
    )
    app_parser.add_argument(
        "--workspace",
        type=Path,
        help="folder that holds your courses (default: ~/LessonLingo or $LESSONLINGO_HOME)",
    )
    app_parser.add_argument(
        "--lan",
        action="store_true",
        help="let devices on the same Wi-Fi or hotspot open the app (trusted networks only)",
    )
    app_parser.add_argument("--offline", action="store_true", help=OFFLINE_HELP)

    setup_parser = subparsers.add_parser(
        "setup",
        help="download models once for later translation without internet",
    )
    setup_parser.add_argument(
        "--voices",
        nargs="+",
        choices=SUPPORTED_LANGUAGES,
        metavar="LANG",
        help="also download the optional spoken voices for these languages",
    )
    setup_parser.add_argument(
        "--voice-engine",
        choices=("mms", "parler"),
        default="mms",
        help="which voices --voices downloads: mms (small, robotic) or parler (natural, 3.8 GB)",
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

    course_parser = subparsers.add_parser(
        "course",
        help="keep lectures and lessons in course folders and translate them all together",
    )
    course_commands = course_parser.add_subparsers(dest="course_command", required=True)

    def workspace_option(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--workspace",
            type=Path,
            help="folder that holds your courses (default: ~/LessonLingo or $LESSONLINGO_HOME)",
        )

    course_new = course_commands.add_parser("new", help="create a course")
    course_new.add_argument("name")
    course_new.add_argument(
        "--to", nargs="+", default=DEFAULT_TARGETS, choices=SUPPORTED_LANGUAGES, metavar="LANG"
    )
    course_new.add_argument("--mode", choices=("quality", "light"), default="light")
    workspace_option(course_new)

    course_list = course_commands.add_parser("list", help="list your courses")
    workspace_option(course_list)

    course_add = course_commands.add_parser("add", help="add videos, audio, .srt files or lessons")
    course_add.add_argument("name")
    course_add.add_argument("files", nargs="+", type=Path)
    workspace_option(course_add)

    course_status = course_commands.add_parser("status", help="show each file and its languages")
    course_status.add_argument("name")
    workspace_option(course_status)

    course_translate = course_commands.add_parser(
        "translate", help="translate every pending file in the course"
    )
    course_translate.add_argument("name")
    course_translate.add_argument(
        "--force", action="store_true", help="translate finished files again"
    )
    course_translate.add_argument("--whisper-device", help="cuda or cpu for speech recognition")
    course_translate.add_argument("--offline", action="store_true", help=OFFLINE_HELP)
    workspace_option(course_translate)

    subparsers.add_parser("languages", help="list supported target language codes")
    return parser


def _progress(completed: int, total: int, target: str) -> None:
    print(f"Translated {target} ({completed}/{total})")


def _glossary(args: argparse.Namespace) -> tuple[list[str], dict[str, dict[str, str]]]:
    """Terms to protect (from --keep and --glossary) and the preferred words per language."""

    terms = list(args.keep)
    preferred: dict[str, dict[str, str]] = {}
    if args.glossary:
        sheet_terms, preferred = load_glossary(args.glossary)
        terms += sheet_terms
    return list(dict.fromkeys(terms)), preferred


def _wrap(inner: Translator, args: argparse.Namespace) -> Translator:
    terms, preferred = _glossary(args)
    return GlossaryTranslator(inner, terms, preferred) if terms else inner


def _maybe_zip(args: argparse.Namespace, paths: list[Path]) -> None:
    if args.zip:
        stem = args.file.name if args.file.is_dir() else args.file.stem
        print(make_class_pack(paths, args.out / f"{stem}.classpack.zip"))


def _run_translate(args: argparse.Namespace, translator: Translator | None) -> int:
    inner = translator or IndicTransTranslator(
        args.mode,
        device=args.device,
        batch_size=args.batch_size,
    )
    backend = _wrap(inner, args)
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
    _maybe_zip(args, paths)
    return 0


def _dub(
    args: argparse.Namespace, paths: list[Path], synthesizer_factory: Callable[[], Synthesizer]
) -> None:
    """Speak each translated subtitle file; add the voices to the video when it is a video."""

    for path in dub_subtitles(
        [p for p in paths if p.suffix == ".srt"],
        args.file,
        args.out,
        synthesizer_factory(),
        note=lambda message: print(f"Note: {message}"),
    ):
        print(path)


def _run_video(
    args: argparse.Namespace,
    translator: Translator | None,
    synthesizer_factory: Callable[[], Synthesizer],
) -> int:
    from lessonlingo.video import FasterWhisperTranscriber, translate_video

    inner = translator or IndicTransTranslator(args.mode)
    backend = _wrap(inner, args)
    try:
        paths = translate_video(
            args.file,
            args.to,
            args.mode,
            args.out,
            transcriber=FasterWhisperTranscriber(
                args.whisper, args.whisper_device, hotwords=_glossary(args)[0]
            ),
            translator=backend,
            status=print,
        )
    finally:
        if translator is None:
            backend.close()
    for output_path in paths:
        print(output_path)
    if args.dub:
        _dub(args, paths, synthesizer_factory)
    if args.embed:
        from lessonlingo.video import embed_subtitles

        tracks = {p.name.split(".")[-2]: p for p in paths if p.suffix == ".srt"}
        tracks.pop("en", None)
        print(embed_subtitles(args.file, tracks, args.out / f"{args.file.stem}.subtitled.mp4"))
    _maybe_zip(args, paths)
    return 0


def _run_course(
    args: argparse.Namespace,
    translator: Translator | None,
    transcriber_factory: Callable[..., Transcriber],
) -> int:
    from lessonlingo.app import default_workspace_root

    home = Workspace(args.workspace or default_workspace_root())
    command = args.course_command
    if command == "new":
        print(home.create_course(args.name, args.to, args.mode))
    elif command == "list":
        for name in home.list_courses():
            print(name)
    elif command == "add":
        for file in args.files:
            print(home.add_file(args.name, file))
    elif command == "status":
        for item in home.list_items(args.name):
            done = ", ".join(SUPPORTED_LANGUAGES[c] for c in item.done) or "not yet"
            print(f"{item.name}\t{item.kind}\t{done}")
    else:
        mode = home.settings(args.name)["mode"]
        backend = translator or IndicTransTranslator(mode)  # type: ignore[arg-type]
        try:
            written = home.translate_course(
                args.name,
                backend,
                lambda **kwargs: transcriber_factory(
                    **kwargs, **({"device": args.whisper_device} if args.whisper_device else {})
                ),
                status=print,
                force=args.force,
            )
        finally:
            if translator is None:
                backend.close()
        print(f"Done. {len(written)} file(s) written.")
        pack = home.course_pack(args.name)
        if pack:
            print(pack)
    return 0


def main(
    argv: Sequence[str] | None = None,
    translator: Translator | None = None,
    transcriber_factory: Callable[..., Transcriber] = FasterWhisperTranscriber,
    synthesizer_factory: Callable[[], Synthesizer] | None = None,
) -> int:
    """Run LessonLingo, optionally injecting fake backends for tests."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        wants_offline = args.command in {"translate", "app", "video"} or (
            args.command == "course" and args.course_command == "translate"
        )
        if wants_offline and _offline_requested(args.offline):
            enable_offline_mode()
        if args.command == "course":
            return _run_course(args, translator, transcriber_factory)
        if args.command == "app":
            from lessonlingo.app import launch

            launch(port=args.port, warm=args.warm, lan=args.lan, workspace_root=args.workspace)
            return 0
        if args.command == "video":
            return _run_video(
                args,
                translator,
                synthesizer_factory or (lambda: make_synthesizer(args.voice_engine)),
            )
        if args.command == "translate":
            return _run_translate(args, translator)
        if args.command == "setup":
            return run_setup(args.cache_dir, args.voices, args.voice_engine)
        if args.command == "verify":
            return run_verify(args.cache_dir)
        for code, name in SUPPORTED_LANGUAGES.items():
            print(f"{code}\t{name}")
        return 0
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        parser.exit(2, f"lessonlingo: error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
