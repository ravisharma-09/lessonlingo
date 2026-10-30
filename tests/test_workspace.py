import zipfile
from pathlib import Path

import pytest

from lessonlingo import video
from lessonlingo.translator import FakeTranslator
from lessonlingo.video import FakeTranscriber
from lessonlingo.workspace import Workspace


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path / "home")


def _srt(path: Path, text: str = "Hello class.") -> Path:
    path.write_text(f"1\n00:00:00,000 --> 00:00:02,000\n{text}\n", encoding="utf-8")
    return path


def test_course_names_cannot_escape_the_workspace(ws: Workspace) -> None:
    for bad in ("../evil", "a/b", "", "..", "x" * 80, ".hidden"):
        with pytest.raises(ValueError):
            ws.course_path(bad)


def test_create_list_and_duplicate_course(ws: Workspace) -> None:
    ws.create_course("Science 8", ["hin_Deva"], "light")

    assert ws.list_courses() == ["Science 8"]
    assert ws.settings("Science 8")["targets"] == ["hin_Deva"]
    with pytest.raises(ValueError):
        ws.create_course("Science 8")


def test_add_file_sorts_by_type_and_never_overwrites(ws: Workspace, tmp_path: Path) -> None:
    ws.create_course("Maths")
    clip = tmp_path / "unit1.mp4"
    clip.write_bytes(b"x")
    note = tmp_path / "unit1.md"
    note.write_text("Hi.", encoding="utf-8")

    first = ws.add_file("Maths", clip)
    second = ws.add_file("Maths", clip)
    lesson = ws.add_file("Maths", note)

    assert first.parent.name == "lectures" and first.name == "unit1.mp4"
    assert second.name == "unit1-2.mp4"
    assert lesson.parent.name == "lessons" and lesson.stem == "unit1-3"
    with pytest.raises(ValueError):
        ws.add_file("Maths", tmp_path / "photo.png")


def test_translate_course_does_everything_then_skips_finished(
    ws: Workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(video, "extract_audio", lambda source, wav: wav.write_bytes(b""))
    ws.create_course("Science", ["kan_Knda", "hin_Deva"], "light")
    clip = tmp_path / "water.mp4"
    clip.write_bytes(b"x")
    ws.add_file("Science", clip)
    ws.add_file("Science", _srt(tmp_path / "talk.srt"))
    note = tmp_path / "notes.md"
    note.write_text("# Notes\n\nPlants need light.", encoding="utf-8")
    ws.add_file("Science", note)

    written = ws.translate_course("Science", FakeTranslator(), FakeTranscriber)

    items = {i.name: i for i in ws.list_items("Science")}
    assert set(items["water.mp4"].done) == {"kan_Knda", "hin_Deva"}
    assert set(items["notes.md"].done) == {"kan_Knda", "hin_Deva"}
    assert len(written) > 6
    pack = ws.course_pack("Science")
    assert pack is not None and "START_HERE.txt" in zipfile.ZipFile(pack).namelist()
    assert ws.translate_course("Science", FakeTranslator(), FakeTranscriber) == []


def test_course_glossary_is_applied(ws: Workspace, tmp_path: Path) -> None:
    ws.create_course("Physics", ["hin_Deva"])
    sheet = tmp_path / "g.csv"
    sheet.write_text("term,hin_Deva\nforce,बल\n", encoding="utf-8")
    ws.save_glossary("Physics", sheet)
    ws.add_file("Physics", _srt(tmp_path / "talk.srt", "Apply a force."))

    ws.translate_course("Physics", FakeTranslator(), FakeTranscriber)

    text = (ws.output_dir("Physics", "talk") / "talk.hin_Deva.srt").read_text(encoding="utf-8")
    assert "बल" in text
    bad = tmp_path / "bad.csv"
    bad.write_text("word,hin_Deva\nx,y\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ws.save_glossary("Physics", bad)


def test_trash_moves_file_and_outputs_instead_of_deleting(ws: Workspace, tmp_path: Path) -> None:
    ws.create_course("Maths", ["hin_Deva"])
    ws.add_file("Maths", _srt(tmp_path / "talk.srt"))
    ws.translate_course("Maths", FakeTranslator(), FakeTranscriber)

    moved = ws.trash_item("Maths", "talk.srt")

    assert moved.exists() and ".trash" in moved.parts
    assert ws.list_items("Maths") == []
    assert not ws.output_dir("Maths", "talk").exists()
    with pytest.raises(FileNotFoundError):
        ws.trash_item("Maths", "../../etc/passwd")
