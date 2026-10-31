"""Every kind of input with every kind of output, driven through the real app with fake models."""

import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("gradio")
client_module = pytest.importorskip("gradio_client")

from lessonlingo.app import ModelHolder, build_app  # noqa: E402
from lessonlingo.translator import FakeTranslator  # noqa: E402
from lessonlingo.tts import FakeSynthesizer  # noqa: E402
from lessonlingo.video import FakeTranscriber  # noqa: E402
from lessonlingo.workspace import Workspace  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")


def _make(tmp_path: Path, args: list[str], name: str) -> Path:
    out = tmp_path / name
    made = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", *args, str(out)], capture_output=True, check=False
    )
    if made.returncode != 0:
        pytest.skip("this ffmpeg cannot make test media")
    return out


@pytest.fixture()
def client(tmp_path: Path):
    app = build_app(
        ModelHolder(lambda mode: FakeTranslator()),
        FakeTranscriber,
        Workspace(tmp_path / "home"),
        FakeSynthesizer,
    )
    _, url, _ = app.launch(prevent_thread_lock=True, server_port=None, quiet=True)
    yield client_module.Client(url, verbose=False)
    app.close()


def _run(client, media: Path, want: str):
    heard = client.predict(client_module.handle_file(str(media)), "", None, api_name="/on_listen")
    rows = heard[1]["value"] if "value" in heard[1] else heard[1]
    return client.predict(
        client_module.handle_file(str(media)),
        {"headers": rows["headers"], "data": [list(r) for r in rows["data"]], "metadata": None},
        ["kan_Knda", "hin_Deva"],
        "light",
        "",
        None,
        want,
        "natural",
        api_name="/on_translate_video",
    )


def _names(result) -> list[str]:
    files = (
        result[0]["value"] if isinstance(result[0], dict) and "value" in result[0] else result[0]
    )
    return [Path(f["name"] if isinstance(f, dict) else f).name for f in files]


def _streams(path: Path) -> str:
    return subprocess.run(["ffmpeg", "-i", str(path)], capture_output=True, text=True).stderr


@pytest.fixture()
def video(tmp_path: Path) -> Path:
    return _make(
        tmp_path,
        ["-f", "lavfi", "-i", "color=c=green:s=160x90:d=3", "-f", "lavfi", "-i", "sine=d=3",
         "-shortest", "-c:v", "mpeg4", "-c:a", "aac"],
        "talk.mp4",
    )  # fmt: skip


def test_video_with_subtitle_files_only(client, video: Path) -> None:
    names = _names(_run(client, video, "subs"))

    assert any(n.endswith(".kan_Knda.srt") for n in names)
    assert not any(n.endswith(".mp4") for n in names)


def test_video_with_subtitles_inside(client, video: Path) -> None:
    result = _run(client, video, "embed")
    names = _names(result)
    final = next(
        Path(f["name"] if isinstance(f, dict) else f)
        for f in (result[0]["value"] if isinstance(result[0], dict) else result[0])
        if str(f["name"] if isinstance(f, dict) else f).endswith(".subtitled.mp4")
    )

    assert "talk.subtitled.mp4" in names
    assert _streams(final).count("Subtitle:") == 2


def test_video_with_subtitles_and_dubbed_audio(client, video: Path) -> None:
    result = _run(client, video, "dub")
    files = result[0]["value"] if isinstance(result[0], dict) else result[0]
    final = next(
        Path(f["name"] if isinstance(f, dict) else f)
        for f in files
        if str(f["name"] if isinstance(f, dict) else f).endswith("talk.dubbed.mp4")
    )

    streams = _streams(final)
    assert streams.count("Audio:") == 3 and streams.count("Subtitle:") == 2


def test_audio_file_with_voice(client, tmp_path: Path) -> None:
    audio = _make(tmp_path, ["-f", "lavfi", "-i", "sine=d=3"], "talk.wav")

    names = _names(_run(client, audio, "voice"))

    assert any(n.endswith(".hin_Deva.wav") for n in names)
    assert any(n.endswith(".kan_Knda.srt") for n in names)


def test_subtitle_file_in_gives_subtitles_and_voice_out(client, tmp_path: Path) -> None:
    srt = tmp_path / "talk.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello class.\n", encoding="utf-8")

    names = _names(_run(client, srt, "voice"))

    assert any(n.endswith(".kan_Knda.wav") for n in names)
    assert not any(n.endswith(".mp4") for n in names)


def test_text_in_gives_one_file_per_language(client) -> None:
    result = client.predict(
        "# Water\n\nWater moves.", None, ["hin_Deva", "kan_Knda"], "light", "", None,
        api_name="/on_translate",
    )  # fmt: skip

    files = (
        result[0]["value"] if isinstance(result[0], dict) and "value" in result[0] else result[0]
    )
    names = [Path(f["name"] if isinstance(f, dict) else f).name for f in files]
    assert any("hin_Deva" in n for n in names) and any("kan_Knda" in n for n in names)
