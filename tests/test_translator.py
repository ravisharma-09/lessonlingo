import pytest

from lessonlingo.translator import FakeTranslator, IndicTransTranslator


def test_fake_translator_preserves_empty_text_and_order() -> None:
    """The fake backend mirrors the real translator interface deterministically."""

    translator = FakeTranslator()

    assert translator.translate(["First.", "", "  ", "Last."], "hin_Deva") == [
        "[hin_Deva] First.",
        "",
        "  ",
        "[hin_Deva] Last.",
    ]


def test_fake_translator_rejects_unknown_language() -> None:
    """Unsupported model codes fail before translation starts."""

    with pytest.raises(ValueError, match="Unsupported target language"):
        FakeTranslator().translate(["Hello"], "spa_Latn")


def test_indic_translator_does_not_load_model_during_construction() -> None:
    """Creating the real backend on the Mac must not import or load model code."""

    translator = IndicTransTranslator("light")

    assert translator.device is None
    assert translator.batch_size == 16


def test_indic_translator_validates_configuration_without_loading() -> None:
    """Invalid configuration is rejected without touching heavy dependencies."""

    with pytest.raises(ValueError, match="Mode"):
        IndicTransTranslator("fast")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Batch size"):
        IndicTransTranslator("light", batch_size=0)
