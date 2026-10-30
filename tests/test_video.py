from pathlib import Path

import pytest

from lessonlingo import video
from lessonlingo.subtitles import parse_subtitles
from lessonlingo.translator import FakeTranslator
from lessonlingo.video import FakeTranscriber, translate_video


class OrderTracker(FakeTranslator):
    """Records whether the speech model was closed before translation began."""

    def __init__(self, speech: FakeTranscriber) -> None:
        self.speech = speech
        self.speech_closed_first: bool | None = None

    def translate(self, sentences: list[str], tgt_lang: str) -> list[str]:
        if self.speech_closed_first is None:
            self.speech_closed_first = getattr(self.speech, "closed", False)
        return super().translate(sentences, tgt_lang)


class ClosingTranscriber(FakeTranscriber):
    closed = False

    def close(self) -> None:
        self.closed = True


def test_srt_input_skips_transcription_and_keeps_timestamps(tmp_path: Path) -> None:
    lecture = tmp_path / "talk.srt"
    lecture.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello class.\n", encoding="utf-8")

    paths = translate_video(
        lecture, ["kan_Knda"], "light", tmp_path / "out", translator=FakeTranslator()
    )

    assert sorted(p.name for p in paths) == [
        "talk.en.srt",
        "talk.kan_Knda.srt",
        "talk.kan_Knda.vtt",
    ]
    cue = parse_subtitles((tmp_path / "out" / "talk.kan_Knda.srt").read_text(encoding="utf-8"))[0]
    assert (cue.start, cue.end, cue.text) == (1.0, 2.0, "[kan_Knda] Hello class.")


def test_video_runs_speech_then_frees_it_before_translating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(video, "extract_audio", lambda source, wav: wav.write_bytes(b""))
    speech = ClosingTranscriber()
    translator = OrderTracker(speech)
    clip = tmp_path / "lecture.mp4"
    clip.write_bytes(b"fake")
    stages: list[str] = []

    paths = translate_video(
        clip,
        ["hin_Deva", "tam_Taml"],
        "light",
        tmp_path / "out",
        transcriber=speech,
        translator=translator,
        status=stages.append,
    )

    assert translator.speech_closed_first is True
    assert len(paths) == 5
    assert stages[:2] == ["Extracting audio", "Listening to the lecture"] and stages[-1] == "Done"


def test_missing_ffmpeg_gives_install_hint(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(video.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="ffmpeg was not found"):
        video.extract_audio(tmp_path / "a.mp4", tmp_path / "a.wav")


def test_ffmpeg_command_makes_16k_mono_wav() -> None:
    command = video.ffmpeg_extract_command(Path("in.mp4"), Path("out.wav"))

    assert command[:3] == ["ffmpeg", "-y", "-i"] and "16000" in command and "-vn" in command


def test_bad_inputs_are_rejected(tmp_path: Path) -> None:
    other = tmp_path / "notes.pdf"
    other.write_text("x")

    with pytest.raises(FileNotFoundError):
        translate_video(tmp_path / "nope.mp4", ["hin_Deva"], "light", tmp_path)
    with pytest.raises(ValueError):
        translate_video(other, ["hin_Deva"], "light", tmp_path, translator=FakeTranslator())
