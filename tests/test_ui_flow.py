from pathlib import Path

import pytest

from lessonlingo.ui_assets import LESSON_STEPS, stepper_html


def test_stepper_marks_done_current_and_todo() -> None:
    html = stepper_html(2)

    assert html.count("<li") == 3
    assert '<li class="done"><span class="dot">✓</span>' in html
    assert '<li class="current"><span class="dot">2</span><span class="name">Check</span>' in html
    assert '<li class="todo"><span class="dot">3</span>' in html


def test_lesson_stepper_has_two_steps() -> None:
    assert stepper_html(1, LESSON_STEPS).count("<li") == 2


def test_whole_lecture_flow_through_the_real_app(tmp_path: Path) -> None:
    """Add, listen, edit a line, translate: driven through the real Gradio server with fakes."""

    pytest.importorskip("gradio")
    client_module = pytest.importorskip("gradio_client")
    from lessonlingo.app import ModelHolder, build_app
    from lessonlingo.translator import FakeTranslator
    from lessonlingo.tts import FakeSynthesizer
    from lessonlingo.video import FakeTranscriber
    from lessonlingo.workspace import Workspace

    home = Workspace(tmp_path / "home")
    talk = tmp_path / "talk.srt"
    talk.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nHello class.\n\n"
        "2\n00:00:02,000 --> 00:00:04,000\nWater cyle.\n",
        encoding="utf-8",
    )
    app = build_app(
        ModelHolder(lambda mode: FakeTranslator()), FakeTranscriber, home, FakeSynthesizer
    )
    _, url, _ = app.launch(prevent_thread_lock=True, server_port=None, quiet=True)
    try:
        client = client_module.Client(url, verbose=False)
        heard = client.predict(
            client_module.handle_file(str(talk)), "", None, api_name="/on_listen"
        )
        assert "Heard 2 lines" in heard[0]
        rows = heard[1]["value"] if "value" in heard[1] else heard[1]
        data = [list(r) for r in rows["data"]]
        data[1][1] = "Water cycle."
        result = client.predict(
            client_module.handle_file(str(talk)),
            {"headers": rows["headers"], "data": data, "metadata": None},
            ["kan_Knda", "hin_Deva"],
            "light",
            "",
            None,
            False,
            api_name="/on_translate_video",
        )
        shown = result[0]["value"] if isinstance(result[0], dict) else result[0]
        files = [Path(f["path"] if isinstance(f, dict) else f) for f in shown]
        names = sorted(f.name for f in files)
        assert "talk.kan_Knda.srt" in names and "talk.hin_Deva.vtt" in names
        srt = next(f for f in files if f.name == "talk.kan_Knda.srt")
        assert "Water cycle." in srt.read_text(encoding="utf-8")
    finally:
        app.close()
