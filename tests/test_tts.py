import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from lessonlingo import tts
from lessonlingo.subtitles import Cue
from lessonlingo.tts import FakeSynthesizer, render_dub, voice_repository


def _seconds(path: Path) -> float:
    with wave.open(str(path)) as handle:
        return handle.getnframes() / handle.getframerate()


def test_voice_repository_names() -> None:
    assert voice_repository("kan_Knda") == "facebook/mms-tts-kan"
    with pytest.raises(ValueError):
        voice_repository("xx_Xxxx")


def test_render_dub_places_speech_at_cue_times(tmp_path: Path) -> None:
    cues = [Cue(1.0, 3.0, "Hello"), Cue(5.0, 7.0, "Water cycle")]

    path, delay = render_dub(cues, "kan_Knda", FakeSynthesizer(), tmp_path / "a.wav")

    assert delay == 0.0
    assert _seconds(path) == pytest.approx(7.0 + tts.TAIL_SECONDS, abs=0.05)
    with wave.open(str(path)) as handle:
        frames = handle.readframes(handle.getnframes())
    first_second = frames[: 2 * 16000]
    assert set(first_second) == {0}  # silence before the first cue starts


def test_long_speech_is_sped_up_then_pushed_later_not_overlapped(tmp_path: Path) -> None:
    long_text = "x" * 200  # 10 seconds of fake speech in a 2 second slot
    cues = [Cue(0.0, 2.0, long_text), Cue(2.0, 4.0, "Next")]

    path, delay = render_dub(cues, "hin_Deva", FakeSynthesizer(), tmp_path / "b.wav")

    assert delay > 4.0  # 10 s / 1.5 is about 6.7 s, so "Next" starts over 4 s late
    assert _seconds(path) > 7.0


def test_empty_text_has_nothing_to_speak(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        render_dub([Cue(0, 1, "  ")], "hin_Deva", FakeSynthesizer(), tmp_path / "c.wav")


def test_dub_command_maps_each_spoken_track() -> None:
    command = tts.ffmpeg_dub_command(
        Path("in.mp4"), {"kan_Knda": Path("k.wav"), "ory_Orya": Path("o.wav")}, Path("out.mp4")
    )

    assert command.count("-i") == 3 and "language=kan" in command and "language=ori" in command
    assert "-metadata:s:a:1" in command and "-metadata:s:a:2" in command


def test_add_dubbed_audio_with_real_ffmpeg(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed")
    clip = tmp_path / "clip.mp4"
    made = subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=green:s=160x90:d=3",
            "-f",
            "lavfi",
            "-i",
            "sine=d=3",
            "-shortest",
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            str(clip),
        ],
        capture_output=True,
    )
    if made.returncode != 0:
        pytest.skip("this ffmpeg cannot make a test clip")
    wav, _ = render_dub(
        [Cue(0.0, 2.0, "Hello there")], "kan_Knda", FakeSynthesizer(), tmp_path / "k.wav"
    )

    out = tts.add_dubbed_audio(clip, {"kan_Knda": wav}, tmp_path / "out.mp4")

    probe = subprocess.run(["ffmpeg", "-i", str(out)], capture_output=True, text=True)
    assert probe.stderr.count("Audio:") == 2

    srt = tmp_path / "clip.hin_Deva.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nनमस्ते\n", encoding="utf-8")
    both = tts.add_dubbed_audio(
        clip, {"kan_Knda": wav}, tmp_path / "both.mp4", subtitles={"hin_Deva": srt}
    )

    probe = subprocess.run(["ffmpeg", "-i", str(both)], capture_output=True, text=True)
    assert probe.stderr.count("Audio:") == 2 and probe.stderr.count("Subtitle:") == 1


def test_engine_factory_and_auto_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(tts.make_synthesizer("mms"), tts.MMSSynthesizer)
    assert isinstance(tts.make_synthesizer("parler"), tts.IndicParlerSynthesizer)
    with pytest.raises(ValueError):
        tts.make_synthesizer("nope")

    monkeypatch.setattr(tts, "parler_installed", lambda: False)
    assert isinstance(tts.AutoSynthesizer()._inner, tts.MMSSynthesizer)

    monkeypatch.setattr(tts, "parler_installed", lambda: True)
    auto = tts.AutoSynthesizer()
    assert isinstance(auto._inner, tts.IndicParlerSynthesizer)

    class Broken(tts.IndicParlerSynthesizer):
        def synthesize(self, text: str, language: str):
            raise RuntimeError("not downloaded")

    class Backup(FakeSynthesizer):
        engine_name = "backup"

    monkeypatch.setattr(tts, "MMSSynthesizer", Backup)
    auto._inner = Broken()
    samples, _ = auto.synthesize("Hello", "kan_Knda")

    assert samples and auto.engine_name == "backup"


def test_parler_without_its_package_explains_the_install() -> None:
    voice = tts.IndicParlerSynthesizer()

    if tts.parler_installed():
        pytest.skip("parler_tts is installed here")
    with pytest.raises(RuntimeError, match="requirements-voice.txt"):
        voice.synthesize("Hello", "hin_Deva")
    with pytest.raises(ValueError):
        voice.synthesize("Hello", "tam_Taml")


def test_only_tested_languages_are_spoken_and_each_gets_its_own_video(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed")
    clip = tmp_path / "clip.mp4"
    made = subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=green:s=160x90:d=3",
            "-f",
            "lavfi",
            "-i",
            "sine=d=3",
            "-shortest",
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            str(clip),
        ],
        capture_output=True,
    )
    if made.returncode != 0:
        pytest.skip("this ffmpeg cannot make a test clip")
    srts = []
    for code in ("kan_Knda", "hin_Deva", "tam_Taml"):
        srt = tmp_path / f"clip.{code}.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello there\n", encoding="utf-8")
        srts.append(srt)
    notes: list[str] = []

    written = tts.dub_subtitles(srts, clip, tmp_path, FakeSynthesizer(), notes.append)

    names = sorted(p.name for p in written)
    assert "clip.kan_Knda.dubbed.mp4" in names and "clip.hin_Deva.dubbed.mp4" in names
    assert "clip.dubbed.mp4" in names and not any("tam_Taml" in n for n in names)
    assert any("tam_Taml" in n and "No tested voice" in n for n in notes)
    probe = subprocess.run(
        ["ffmpeg", "-i", str(tmp_path / "clip.kan_Knda.dubbed.mp4")], capture_output=True, text=True
    )
    assert probe.stderr.count("Audio:") == 1


def test_silence_at_clip_edges_is_trimmed() -> None:
    from array import array

    padded = array("h", [0] * 4000 + [8000] * 2000 + [0] * 4000)

    trimmed = tts._trim_silence(padded, 16000)

    assert 2000 <= len(trimmed) <= 2000 + 2 * int(tts.EDGE_PAD_SECONDS * 16000)


def test_clip_borrows_the_pause_after_its_cue_before_it_is_sped_up(tmp_path: Path) -> None:
    cues = [Cue(0.0, 2.0, "x" * 50), Cue(5.0, 7.0, "Next")]  # 2.5 s of speech, slot 2 s plus gap

    _, delay = render_dub(cues, "hin_Deva", FakeSynthesizer(), tmp_path / "d.wav")

    assert delay == 0.0  # fits in the 2 s cue plus the pause, so nothing falls behind


def test_time_stretch_keeps_length_ratio_or_falls_back() -> None:
    from array import array

    clip = array("h", [3000, -3000] * 8000)  # 1 second at 16 kHz

    faster = tts._time_stretch(clip, 16000, 1.5)

    assert 0.6 * 16000 <= len(faster) <= 0.75 * 16000


def test_dub_command_adds_subtitle_tracks_after_the_audio() -> None:
    command = tts.ffmpeg_dub_command(
        Path("in.mp4"),
        {"kan_Knda": Path("k.wav")},
        Path("out.mp4"),
        subtitles={"hin_Deva": Path("h.srt")},
    )

    assert command.count("-i") == 3 and "mov_text" in command and "language=hin" in command
    assert command.index("h.srt") > command.index("k.wav")
