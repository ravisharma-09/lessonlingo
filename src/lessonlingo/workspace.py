"""Courses on disk: folders for lectures and lessons, saved settings, batch translation.

The filesystem is the database. Each course is a folder under the workspace root. Nothing is
deleted permanently: removed items move to a `.trash` folder inside the course.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lessonlingo.glossary import GlossaryTranslator, load_glossary
from lessonlingo.languages import SUPPORTED_LANGUAGES, validate_targets
from lessonlingo.pack import make_class_pack
from lessonlingo.pipeline import LESSON_SUFFIXES, translate_file
from lessonlingo.subtitles import Cue
from lessonlingo.translator import Mode, Translator
from lessonlingo.video import (
    SUBTITLE_SUFFIXES,
    VIDEO_SUFFIXES,
    StatusCallback,
    Transcriber,
    transcribe_lecture,
    translate_lecture,
)

NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,59}$")
LECTURE_SUFFIXES = VIDEO_SUFFIXES | SUBTITLE_SUFFIXES
DEFAULT_TARGETS = ["kan_Knda", "hin_Deva"]


@dataclass(frozen=True)
class Item:
    """One file in a course and the languages it has already been translated into."""

    name: str
    stem: str
    kind: str  # "lecture" or "lesson"
    path: Path
    done: list[str]


class Workspace:
    """A folder that holds courses."""

    def __init__(self, root: Path) -> None:
        """Use `root` as the workspace folder, creating it if needed."""

        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    # --- courses -----------------------------------------------------------------------

    def course_path(self, name: str) -> Path:
        """Folder of a course. Raises ValueError for names that could escape the workspace."""

        clean = name.strip()
        if not NAME_PATTERN.match(clean):
            raise ValueError("Use letters, numbers, spaces, - or _ (up to 60 characters).")
        path = (self.root / clean).resolve()
        if path.parent != self.root:
            raise ValueError("That course name is not allowed.")
        return path

    def list_courses(self) -> list[str]:
        """Names of all courses, alphabetically."""

        return sorted(p.name for p in self.root.iterdir() if (p / "course.json").is_file())

    def create_course(
        self, name: str, targets: list[str] | None = None, mode: Mode = "light"
    ) -> Path:
        """Create a new course folder with its settings."""

        path = self.course_path(name)
        if path.exists():
            raise ValueError(f"A course called '{path.name}' already exists.")
        for folder in ("lectures", "lessons", "outputs"):
            (path / folder).mkdir(parents=True)
        self.save_settings(path.name, targets or DEFAULT_TARGETS, mode)
        return path

    def settings(self, course: str) -> dict[str, object]:
        """Saved languages and mode of a course."""

        file = self.course_path(course) / "course.json"
        if not file.is_file():
            raise FileNotFoundError(f"Course not found: {course}")
        return json.loads(file.read_text(encoding="utf-8"))

    def save_settings(self, course: str, targets: list[str], mode: Mode) -> None:
        """Save the languages and mode used by 'translate everything'."""

        data = {"name": course, "targets": validate_targets(targets), "mode": mode}
        (self.course_path(course) / "course.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    # --- glossary ----------------------------------------------------------------------

    def glossary_path(self, course: str) -> Path | None:
        """The course glossary file, if one was saved."""

        path = self.course_path(course) / "glossary.csv"
        return path if path.is_file() else None

    def save_glossary(self, course: str, source: Path) -> Path:
        """Check a glossary CSV and keep a copy in the course."""

        load_glossary(Path(source))  # raises ValueError for a bad file
        target = self.course_path(course) / "glossary.csv"
        shutil.copyfile(source, target)
        return target

    # --- files -------------------------------------------------------------------------

    def _existing_stems(self, course: str) -> set[str]:
        path = self.course_path(course)
        return {p.stem for folder in ("lectures", "lessons") for p in (path / folder).glob("*")}

    def add_file(self, course: str, source: Path) -> Path:
        """Copy a video, audio, subtitle or lesson file into the right folder of the course."""

        source = Path(source)
        suffix = source.suffix.lower()
        if suffix in LECTURE_SUFFIXES:
            folder = "lectures"
        elif suffix in LESSON_SUFFIXES:
            folder = "lessons"
        else:
            raise ValueError(f"'{source.name}' is not a video, audio, subtitle or lesson file.")
        stem = re.sub(r"[^\w -]", "_", source.stem).strip() or "file"
        taken = self._existing_stems(course)
        unique, number = stem, 2
        while unique in taken:
            unique, number = f"{stem}-{number}", number + 1
        target = self.course_path(course) / folder / f"{unique}{suffix}"
        shutil.copyfile(source, target)
        return target

    def list_items(self, course: str) -> list[Item]:
        """All files of the course with the languages already translated."""

        path = self.course_path(course)
        self.settings(course)  # raises if the course does not exist
        items: list[Item] = []
        for folder, kind, extension in (
            ("lectures", "lecture", ".srt"),
            ("lessons", "lesson", ".md"),
        ):
            for file in sorted((path / folder).glob("*")):
                if not file.is_file():
                    continue
                out = path / "outputs" / file.stem
                done = [
                    c
                    for c in SUPPORTED_LANGUAGES
                    if (out / f"{file.stem}.{c}{extension}").is_file()
                ]
                items.append(Item(file.name, file.stem, kind, file, done))
        return items

    def trash_item(self, course: str, filename: str) -> Path:
        """Move a file and its outputs to the course's .trash folder (nothing is deleted)."""

        path = self.course_path(course)
        for folder in ("lectures", "lessons"):
            file = (path / folder / filename).resolve()
            if file.parent == (path / folder).resolve() and file.is_file():
                trash = path / ".trash"
                trash.mkdir(exist_ok=True)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                moved = trash / f"{stamp}-{file.name}"
                shutil.move(str(file), moved)
                outputs = path / "outputs" / file.stem
                if outputs.is_dir():
                    shutil.move(str(outputs), trash / f"{stamp}-{file.stem}-outputs")
                return moved
        raise FileNotFoundError(f"File not found in the course: {filename}")

    # --- translating -------------------------------------------------------------------

    def output_dir(self, course: str, stem: str) -> Path:
        """Where the translated files of one item are written."""

        return self.course_path(course) / "outputs" / stem

    def course_pack(self, course: str) -> Path | None:
        """Build one zip with every translated file of the course; None if nothing yet."""

        outputs = self.course_path(course) / "outputs"
        files = sorted(
            p for p in outputs.rglob("*") if p.suffix in {".srt", ".vtt", ".md"} and p.is_file()
        )
        if not files:
            return None
        return make_class_pack(files, outputs / f"{course.strip()}.classpack.zip")

    def translate_course(
        self,
        course: str,
        translator: Translator,
        transcriber_factory: Callable[..., Transcriber],
        status: StatusCallback | None = None,
        force: bool = False,
    ) -> list[Path]:
        """Translate every pending item of the course into its saved languages.

        All lectures are transcribed first (speech model), then everything is translated
        (translation model), so the two models never share the GPU. Finished items are
        skipped unless `force` is set. Returns the files written.
        """

        saved = self.settings(course)
        targets = list(saved["targets"])  # type: ignore[arg-type]
        mode: Mode = saved["mode"]  # type: ignore[assignment]
        terms: list[str] = []
        preferred: dict[str, dict[str, str]] = {}
        sheet = self.glossary_path(course)
        if sheet:
            terms, preferred = load_glossary(sheet)
        backend: Translator = (
            GlossaryTranslator(translator, terms, preferred) if terms else translator
        )

        def say(item: Item, message: str) -> None:
            if status:
                status(f"{item.name}: {message}")

        pending: list[tuple[Item, list[str]]] = []
        for item in self.list_items(course):
            wanted = targets if force else [t for t in targets if t not in item.done]
            if wanted:
                pending.append((item, wanted))

        heard: dict[str, list[Cue]] = {}
        for item, _ in pending:
            if item.kind == "lecture":
                heard[item.name] = transcribe_lecture(
                    item.path, transcriber_factory(hotwords=terms), lambda m, i=item: say(i, m)
                )

        written: list[Path] = []
        for item, wanted in pending:
            out = self.output_dir(course, item.stem)
            if item.kind == "lecture":
                written += translate_lecture(
                    heard[item.name],
                    item.stem,
                    wanted,
                    mode,
                    out,
                    backend,
                    lambda m, i=item: say(i, m),
                )
            else:
                say(item, "Translating")
                written += translate_file(item.path, wanted, mode, out, translator=backend)
        self.course_pack(course)
        return written
