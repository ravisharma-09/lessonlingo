"""Translation backends for LessonLingo."""

from __future__ import annotations

import gc
from typing import Any, Literal, Protocol

from lessonlingo.languages import SOURCE_LANGUAGE, SUPPORTED_LANGUAGES

Mode = Literal["quality", "light"]

MODEL_REPOSITORIES: dict[Mode, str] = {
    "quality": "ai4bharat/indictrans2-en-indic-1B",
    "light": "ai4bharat/indictrans2-en-indic-dist-200M",
}

DEFAULT_BATCH_SIZES: dict[Mode, int] = {
    "quality": 8,
    "light": 16,
}


class Translator(Protocol):
    """Interface shared by real and fake translation backends."""

    def translate(self, sentences: list[str], tgt_lang: str) -> list[str]:
        """Translate sentences into an IndicTrans2 target language."""

    def close(self) -> None:
        """Release resources held by the translator."""


class FakeTranslator:
    """Deterministic translator used by unit tests and Mac development."""

    def translate(self, sentences: list[str], tgt_lang: str) -> list[str]:
        """Prefix every non-empty sentence with its requested language code."""

        if tgt_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported target language: {tgt_lang}")
        return [
            f"[{tgt_lang}] {sentence}" if sentence.strip() else sentence
            for sentence in sentences
        ]

    def close(self) -> None:
        """Release resources; the fake backend has none."""


class IndicTransTranslator:
    """Lazy-loading AI4Bharat IndicTrans2 translation backend."""

    def __init__(
        self,
        mode: Mode,
        device: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        """Configure a model without loading it until the first translation."""

        if mode not in MODEL_REPOSITORIES:
            raise ValueError("Mode must be 'quality' or 'light'.")
        if batch_size is not None and batch_size < 1:
            raise ValueError("Batch size must be at least 1.")

        self.mode = mode
        self.requested_device = device
        self.batch_size = batch_size or DEFAULT_BATCH_SIZES[mode]
        self.device: str | None = None
        self._torch: Any = None
        self._tokenizer: Any = None
        self._model: Any = None
        self._processor: Any = None

    def _load(self) -> None:
        """Load runtime dependencies and model weights on first use."""

        if self._model is not None:
            return

        try:
            import torch
            from IndicTransToolkit.processor import IndicProcessor
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except (ImportError, OSError) as error:
            raise RuntimeError(
                "IndicTrans2 could not start. Install the dependencies from "
                "requirements.txt, including transformers==4.46.1 and "
                "IndicTransToolkit. On Windows, install Visual Studio Build Tools "
                "if IndicTransToolkit reports a compiler error."
            ) from error

        device = self.requested_device or ("cuda" if torch.cuda.is_available() else "cpu")
        if self.mode == "quality" and not device.startswith("cuda"):
            raise RuntimeError("Quality mode requires a CUDA GPU. Use light mode on CPU.")

        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        repository = MODEL_REPOSITORIES[self.mode]

        self._torch = torch
        self._processor = IndicProcessor(inference=True)
        self._tokenizer = AutoTokenizer.from_pretrained(
            repository,
            trust_remote_code=True,
        )
        self._model = AutoModelForSeq2SeqLM.from_pretrained(
            repository,
            trust_remote_code=True,
            torch_dtype=dtype,
        ).to(device)
        self._model.eval()
        self.device = device

    def translate(self, sentences: list[str], tgt_lang: str) -> list[str]:
        """Translate sentences in stable order, batching non-empty inputs."""

        if tgt_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported target language: {tgt_lang}")
        if not sentences:
            return []

        self._load()
        results = list(sentences)
        pending = [
            (index, sentence)
            for index, sentence in enumerate(sentences)
            if sentence.strip()
        ]

        for offset in range(0, len(pending), self.batch_size):
            chunk = pending[offset : offset + self.batch_size]
            indices = [index for index, _ in chunk]
            source = [sentence for _, sentence in chunk]
            processed = self._processor.preprocess_batch(
                source,
                src_lang=SOURCE_LANGUAGE,
                tgt_lang=tgt_lang,
            )
            inputs = self._tokenizer(
                processed,
                padding="longest",
                truncation=True,
                max_length=256,
                return_tensors="pt",
            ).to(self.device)

            with self._torch.no_grad():
                generated = self._model.generate(
                    **inputs,
                    num_beams=5,
                    max_length=256,
                    num_return_sequences=1,
                )

            decoded = self._tokenizer.batch_decode(
                generated,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )
            translated = self._processor.postprocess_batch(decoded, lang=tgt_lang)
            if len(translated) != len(indices):
                raise RuntimeError("The translation model returned an unexpected output count.")
            for index, output in zip(indices, translated, strict=True):
                results[index] = output

        return results

    def close(self) -> None:
        """Release model memory, including cached CUDA allocations."""

        model = self._model
        self._model = None
        self._tokenizer = None
        self._processor = None
        self.device = None
        if model is not None:
            del model
        gc.collect()
        if self._torch is not None and self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()
        self._torch = None
