import zipfile
from pathlib import Path

from lessonlingo.pack import make_class_pack
from lessonlingo.subtitles import Cue
from lessonlingo.translator import FakeTranslator
from lessonlingo.video import FakeTranscriber, is_doubtful, transcribe_lecture, translate_lecture


def test_class_pack_contains_files_and_instructions(tmp_path: Path) -> None:
    a = tmp_path / "talk.kan_Knda.srt"
    a.write_text("x", encoding="utf-8")

    pack = make_class_pack([a], tmp_path / "out" / "talk.classpack.zip")

    with zipfile.ZipFile(pack) as archive:
        assert sorted(archive.namelist()) == ["START_HERE.txt", "talk.kan_Knda.srt"]
        assert "talk.kan_Knda.srt" in archive.read("START_HERE.txt").decode("utf-8")


def test_doubtful_lines_are_flagged_from_the_score() -> None:
    assert is_doubtful(Cue(0, 1, "x", -1.6))
    assert not is_doubtful(Cue(0, 1, "x", -0.2))
    assert not is_doubtful(Cue(0, 1, "x"))


def test_listen_then_translate_lets_the_teacher_fix_the_transcript(
    tmp_path: Path, monkeypatch
) -> None:
    from lessonlingo import video

    monkeypatch.setattr(video, "extract_audio", lambda source, wav: wav.write_bytes(b""))
    clip = tmp_path / "talk.mp4"
    clip.write_bytes(b"x")

    cues = transcribe_lecture(clip, FakeTranscriber())
    fixed = [Cue(c.start, c.end, c.text.replace("water", "WATER"), c.score) for c in cues]
    paths = translate_lecture(fixed, "talk", ["hin_Deva"], "light", tmp_path, FakeTranslator())

    text = (tmp_path / "talk.hin_Deva.srt").read_text(encoding="utf-8")
    assert "WATER cycle" in text and len(paths) == 3
