"""Keep chosen words in English while the rest of a sentence is translated.

Each kept term is swapped for a neutral placeholder before translation and put back
afterwards. If the model drops a placeholder, that sentence is translated again without
protection, so the output is never left with a broken token.
"""

from __future__ import annotations

import re

from lessonlingo.translator import Translator

PLACEHOLDER = "ZQX{n}"


def parse_terms(raw: str | None) -> list[str]:
    """Split a comma- or newline-separated list of terms, dropping blanks and duplicates."""

    if not raw:
        return []
    parts = (part.strip() for part in re.split(r"[,\n]", raw))
    return list(dict.fromkeys(part for part in parts if part))


def protect(sentence: str, terms: list[str]) -> tuple[str, dict[str, str]]:
    """Replace whole-word, case-insensitive matches of the terms with placeholders."""

    mapping: dict[str, str] = {}
    masked = sentence
    for term in sorted(terms, key=len, reverse=True):
        pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)

        def swap(match: re.Match[str]) -> str:
            token = PLACEHOLDER.format(n=len(mapping))
            mapping[token] = match.group(0)
            return token

        masked = pattern.sub(swap, masked)
    return masked, mapping


def restore(output: str, mapping: dict[str, str]) -> str | None:
    """Put the original terms back; return None if any placeholder was lost."""

    for token, original in mapping.items():
        if token not in output:
            return None
        output = output.replace(token, original)
    return output


class GlossaryTranslator:
    """Wraps a translator so the given terms stay in English."""

    def __init__(self, inner: Translator, terms: list[str]) -> None:
        """Wrap `inner`; with no terms it behaves exactly like `inner`."""

        self.inner = inner
        self.terms = terms
        self.fallbacks = 0

    def translate(self, sentences: list[str], tgt_lang: str) -> list[str]:
        """Translate with terms protected, re-translating any sentence that lost a term."""

        if not self.terms:
            return self.inner.translate(sentences, tgt_lang)
        masked = [protect(sentence, self.terms) for sentence in sentences]
        outputs = self.inner.translate([text for text, _ in masked], tgt_lang)

        results: list[str] = []
        retry: list[int] = []
        for index, ((_, mapping), output) in enumerate(zip(masked, outputs, strict=True)):
            restored = restore(output, mapping) if mapping else output
            if restored is None:
                retry.append(index)
                results.append("")
            else:
                results.append(restored)
        if retry:
            self.fallbacks += len(retry)
            plain = self.inner.translate([sentences[i] for i in retry], tgt_lang)
            for index, text in zip(retry, plain, strict=True):
                results[index] = text
        return results

    def close(self) -> None:
        """Close the wrapped translator."""

        self.inner.close()
