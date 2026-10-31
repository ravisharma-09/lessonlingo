from pathlib import Path

import pytest


def test_header_is_plain_with_one_theme() -> None:
    from lessonlingo.ui_assets import HERO_HTML, STYLE_CSS

    assert "pumpkin" not in HERO_HTML.lower() and "ghost" not in HERO_HTML.lower()
    assert HERO_HTML.count("<svg") == 1 and "LessonLingo logo" in HERO_HTML
    assert HERO_HTML.count('class="sw"') == 5
    assert "data-accent" not in STYLE_CSS and "body.dark" not in STYLE_CSS


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
            "subs",
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


def test_steps_refuse_to_go_on_without_what_they_need(tmp_path: Path) -> None:
    pytest.importorskip("gradio")
    client_module = pytest.importorskip("gradio_client")
    from lessonlingo.app import ModelHolder, build_app
    from lessonlingo.translator import FakeTranslator
    from lessonlingo.tts import FakeSynthesizer
    from lessonlingo.video import FakeTranscriber
    from lessonlingo.workspace import Workspace

    app = build_app(
        ModelHolder(lambda mode: FakeTranslator()),
        FakeTranscriber,
        Workspace(tmp_path / "home"),
        FakeSynthesizer,
    )
    _, url, _ = app.launch(prevent_thread_lock=True, server_port=None, quiet=True)
    try:
        client = client_module.Client(url, verbose=False)
        with pytest.raises(Exception, match="video"):
            client.predict("video", "", None, None, api_name="/check_add")
        with pytest.raises(Exception, match="at least one language"):
            client.predict([], api_name="/check_languages")
        talk = tmp_path / "talk.srt"
        talk.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello.\n", encoding="utf-8")
        with pytest.raises(Exception, match="Hindi and Kannada"):
            client.predict(
                "subs",
                "",
                None,
                client_module.handle_file(str(talk)),
                ["tam_Taml"],
                "voice",
                api_name="/check_options",
            )
    finally:
        app.close()
