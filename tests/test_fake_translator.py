class FakeTranslator:
    """Small deterministic stand-in for a model-backed translator."""

    def translate(self, text: str, target_language: str) -> str:
        return f"[{target_language}] {text}"


def test_translation_uses_fake_translator() -> None:
    translator = FakeTranslator()

    assert translator.translate("Hello", "es") == "[es] Hello"
