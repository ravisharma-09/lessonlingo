from contextlib import nullcontext
from typing import Any

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


class StubBatch(dict[str, Any]):
    """Minimal tokenizer batch with the Transformers device API."""

    def to(self, device: str) -> "StubBatch":
        """Record the selected device and return this batch."""

        self["device"] = device
        return self


class StubProcessor:
    """Record IndicTrans preprocessing and postprocessing calls."""

    def __init__(self) -> None:
        """Create empty processor call logs."""

        self.preprocess_calls: list[tuple[list[str], str, str]] = []
        self.postprocess_calls: list[tuple[list[str], str]] = []

    def preprocess_batch(
        self,
        sentences: list[str],
        src_lang: str,
        tgt_lang: str,
    ) -> list[str]:
        """Record and tag inputs before tokenization."""

        self.preprocess_calls.append((sentences, src_lang, tgt_lang))
        return [f"pre:{sentence}" for sentence in sentences]

    def postprocess_batch(self, decoded: list[str], lang: str) -> list[str]:
        """Record and tag decoded model outputs."""

        self.postprocess_calls.append((decoded, lang))
        return [f"post:{sentence}" for sentence in decoded]


class StubTokenizer:
    """Small tokenizer stand-in that preserves test strings."""

    def __call__(self, sentences: list[str], **kwargs: Any) -> StubBatch:
        """Return a device-aware batch for the stub model."""

        return StubBatch(sentences=sentences, tokenizer_options=kwargs)

    def batch_decode(self, generated: list[str], **kwargs: Any) -> list[str]:
        """Return generated strings unchanged."""

        return generated


class StubModel:
    """Record generation settings without running a model."""

    def __init__(self) -> None:
        """Create an empty generation call log."""

        self.calls: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> list[str]:
        """Return the preprocessed source strings as generated output."""

        self.calls.append(kwargs)
        return kwargs["sentences"]


class StubTorch:
    """Provide the no-grad context used during generation."""

    @staticmethod
    def no_grad() -> Any:
        """Return a context manager matching `torch.no_grad`."""

        return nullcontext()


def test_indic_translator_batches_and_runs_both_processor_steps() -> None:
    """Real-backend control flow is covered without importing heavy libraries."""

    translator = IndicTransTranslator("light", device="cpu", batch_size=2)
    processor = StubProcessor()
    model = StubModel()
    translator._processor = processor
    translator._tokenizer = StubTokenizer()
    translator._model = model
    translator._torch = StubTorch()
    translator.device = "cpu"

    output = translator.translate(["One.", "", "Two.", "Three."], "hin_Deva")

    assert output == ["post:pre:One.", "", "post:pre:Two.", "post:pre:Three."]
    assert processor.preprocess_calls == [
        (["One.", "Two."], "eng_Latn", "hin_Deva"),
        (["Three."], "eng_Latn", "hin_Deva"),
    ]
    assert processor.postprocess_calls == [
        (["pre:One.", "pre:Two."], "hin_Deva"),
        (["pre:Three."], "hin_Deva"),
    ]
    assert all(call["num_beams"] == 5 for call in model.calls)
    assert all(call["max_length"] == 256 for call in model.calls)
    assert all(call["num_return_sequences"] == 1 for call in model.calls)
