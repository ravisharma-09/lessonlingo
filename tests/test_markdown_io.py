import pytest

from lessonlingo.markdown_io import rebuild, split_markdown

COMPLEX_DOCUMENT = """---
title: Keep this metadata
---
# Lesson heading

Read the introduction. Then answer the question!

> - Use `print("hello")` and visit [the guide](https://example.com/guide).

| Topic | Description |
| :--- | ---: |
| Math | Add two values. |

![Diagram](images/example.png)
<strong>Important</strong> text.

```python
value = "Do not translate this."
```
"""


def test_identity_translation_round_trip_is_exact() -> None:
    """An identity translator reconstructs every byte of Markdown structure."""

    segments = split_markdown(COMPLEX_DOCUMENT)
    identity = [segment.text for segment in segments if segment.translatable]

    assert rebuild(segments, identity) == COMPLEX_DOCUMENT


def test_protected_markdown_is_not_sent_for_translation() -> None:
    """Code, links, images, tags, metadata, and structural markers stay protected."""

    segments = split_markdown(COMPLEX_DOCUMENT)
    protected = "".join(segment.text for segment in segments if not segment.translatable)

    assert "title: Keep this metadata" in protected
    assert "`print(\"hello\")`" in protected
    assert "[the guide](https://example.com/guide)" in protected
    assert "![Diagram](images/example.png)" in protected
    assert "<strong>" in protected and "</strong>" in protected
    assert 'value = "Do not translate this."' in protected
    assert "# " in protected
    assert "> - " in protected
    assert "|" in protected


def test_sentence_splitter_handles_supported_terminators() -> None:
    """Simple sentence splitting recognizes Latin and Indic punctuation."""

    segments = split_markdown("One. Two? Three! Four।")

    assert [segment.text for segment in segments if segment.translatable] == [
        "One.",
        "Two?",
        "Three!",
        "Four।",
    ]


def test_rebuild_rejects_wrong_translation_count() -> None:
    """Missing model output cannot silently corrupt the document."""

    segments = split_markdown("One. Two.")

    with pytest.raises(ValueError, match="Expected 2"):
        rebuild(segments, ["Only one."])
