from pathlib import Path

import pytest

from lessonlingo import cancel
from lessonlingo.subtitles import Cue
from lessonlingo.translator import FakeTranslator
from lessonlingo.tts import FakeSynthesizer, render_dub
from lessonlingo.video import translate_cues


@pytest.fixture(autouse=True)
def _clear_signal():
    cancel.reset()
    yield
    cancel.reset()


def test_check_stops_only_after_a_request() -> None:
    cancel.check()
    cancel.request()
    with pytest.raises(cancel.Cancelled):
        cancel.check()
    cancel.reset()
    cancel.check()


def test_speaking_stops_when_cancelled(tmp_path: Path) -> None:
    cancel.request()

    with pytest.raises(cancel.Cancelled):
        render_dub([Cue(0, 1, "Hello")], "hin_Deva", FakeSynthesizer(), tmp_path / "a.wav")


def test_translating_stops_when_cancelled() -> None:
    cancel.request()

    with pytest.raises(cancel.Cancelled):
        translate_cues([Cue(0, 1, "Hello")], ["hin_Deva"], FakeTranslator())


def test_cancelled_is_shown_as_a_plain_message() -> None:
    from lessonlingo.app import friendly_error

    assert friendly_error(cancel.Cancelled("Stopped. Nothing was changed.")).startswith("Stopped")
