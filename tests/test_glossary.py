from lessonlingo.glossary import GlossaryTranslator, parse_terms, protect, restore
from lessonlingo.pipeline import translate_segments, translate_text
from lessonlingo.translator import FakeTranslator


def test_parse_terms_handles_commas_newlines_and_duplicates() -> None:
    assert parse_terms("photosynthesis, Python\nPython,  ") == ["photosynthesis", "Python"]
    assert parse_terms(None) == []


def test_protect_is_whole_word_and_case_insensitive() -> None:
    masked, mapping = protect("Photosynthesis and photosynthesised plants", ["photosynthesis"])

    assert masked == "ZQX0 and photosynthesised plants"
    assert restore("ZQX0 ok", mapping) == "Photosynthesis ok"


def test_restore_returns_none_when_token_is_lost() -> None:
    _, mapping = protect("Use Python", ["Python"])

    assert restore("no token here", mapping) is None


def test_terms_survive_translation() -> None:
    translator = GlossaryTranslator(FakeTranslator(), ["photosynthesis"])

    out = translator.translate(["Plants use photosynthesis.", "Hello."], "hin_Deva")

    assert out == ["[hin_Deva] Plants use photosynthesis.", "[hin_Deva] Hello."]
    assert translator.fallbacks == 0


def test_lost_placeholder_falls_back_to_plain_translation() -> None:
    class Dropper(FakeTranslator):
        def translate(self, sentences: list[str], tgt_lang: str) -> list[str]:
            return ["gone" if "ZQX" in s else f"plain:{s}" for s in sentences]

    translator = GlossaryTranslator(Dropper(), ["Python"])

    assert translator.translate(["Learn Python."], "hin_Deva") == ["plain:Learn Python."]
    assert translator.fallbacks == 1


def test_no_terms_is_a_passthrough() -> None:
    assert GlossaryTranslator(FakeTranslator(), []).translate(["Hi."], "kan_Knda") == [
        "[kan_Knda] Hi."
    ]


def test_works_through_the_markdown_pipeline() -> None:
    translator = GlossaryTranslator(FakeTranslator(), ["Python"])

    result = translate_text("# Learn Python\n\nPython is fun.", ["hin_Deva"], "light", translator)

    assert "Python" in result["hin_Deva"] and "ZQX" not in result["hin_Deva"]


def test_translate_segments_aligns_with_translatable_segments() -> None:
    segments, translations = translate_segments(
        "Hello there.\n\n`code`", "tam_Taml", FakeTranslator()
    )

    assert len(translations) == sum(1 for s in segments if s.translatable)
