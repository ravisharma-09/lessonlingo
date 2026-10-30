"""Markdown-aware segmentation and reconstruction."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    """A source fragment marked as translatable or structurally protected."""

    text: str
    translatable: bool


_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_STRUCTURAL_PREFIX_RE = re.compile(
    r"^(?:\s{0,3}#{1,6}[ \t]+|\s*>[ \t]*|\s*(?:[-+*]|\d+[.)])[ \t]+(?:\[[ xX]\][ \t]+)?)"
)
_PROTECTED_INLINE_RE = re.compile(
    r"(`+.*?`+|!?\[[^\]\n]*\]\([^\n)]*\)|https?://[^\s<>]+|<!--.*?-->|</?[A-Za-z][^>]*>)"
)
_SENTENCE_RE = re.compile(r".*?(?:[.!?।]+(?=\s|$)|$)", re.DOTALL)
_TABLE_DIVIDER_RE = re.compile(r"^\s*:?-{3,}:?\s*$")


def _append(segments: list[Segment], text: str, translatable: bool) -> None:
    if not text:
        return
    if not translatable and segments and not segments[-1].translatable:
        previous = segments[-1]
        segments[-1] = Segment(previous.text + text, False)
        return
    segments.append(Segment(text, translatable))


def _split_sentences(text: str, segments: list[Segment]) -> None:
    for match in _SENTENCE_RE.finditer(text):
        piece = match.group(0)
        if not piece:
            continue
        if not piece.strip():
            _append(segments, piece, False)
            continue
        leading_length = len(piece) - len(piece.lstrip())
        trailing_length = len(piece) - len(piece.rstrip())
        leading = piece[:leading_length]
        content_end = len(piece) - trailing_length if trailing_length else len(piece)
        content = piece[leading_length:content_end]
        trailing = piece[content_end:]
        _append(segments, leading, False)
        _append(segments, content, bool(re.search(r"\w", content, re.UNICODE)))
        _append(segments, trailing, False)


def _split_inline(text: str, segments: list[Segment]) -> None:
    cursor = 0
    for match in _PROTECTED_INLINE_RE.finditer(text):
        _split_table_text(text[cursor : match.start()], segments)
        _append(segments, match.group(0), False)
        cursor = match.end()
    _split_table_text(text[cursor:], segments)


def _split_table_text(text: str, segments: list[Segment]) -> None:
    parts = re.split(r"(\|)", text)
    for part in parts:
        if part == "|" or _TABLE_DIVIDER_RE.fullmatch(part):
            _append(segments, part, False)
        else:
            _split_sentences(part, segments)


def _split_line(line: str, segments: list[Segment]) -> None:
    body = line.rstrip("\r\n")
    newline = line[len(body) :]
    remaining = body

    while remaining:
        prefix = _STRUCTURAL_PREFIX_RE.match(remaining)
        if prefix is None:
            break
        _append(segments, prefix.group(0), False)
        remaining = remaining[prefix.end() :]

    _split_inline(remaining, segments)
    _append(segments, newline, False)


def split_markdown(document: str) -> list[Segment]:
    """Split Markdown into sentence-sized text and protected structure."""

    if not document:
        return []

    lines = document.splitlines(keepends=True)
    segments: list[Segment] = []
    index = 0

    if lines and lines[0].strip() == "---":
        front_matter_end = next(
            (
                line_index
                for line_index in range(1, len(lines))
                if lines[line_index].strip() in {"---", "..."}
            ),
            None,
        )
        if front_matter_end is not None:
            _append(segments, "".join(lines[: front_matter_end + 1]), False)
            index = front_matter_end + 1

    fence_character: str | None = None
    fence_length = 0
    while index < len(lines):
        line = lines[index]
        fence = _FENCE_RE.match(line)
        if fence_character is not None:
            _append(segments, line, False)
            if (
                fence
                and fence.group(1)[0] == fence_character
                and len(fence.group(1)) >= fence_length
            ):
                fence_character = None
                fence_length = 0
        elif fence:
            marker = fence.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            _append(segments, line, False)
        else:
            _split_line(line, segments)
        index += 1

    return segments


def rebuild(segments: list[Segment], translations: list[str]) -> str:
    """Reassemble a document while preserving every protected fragment exactly."""

    expected = sum(segment.translatable for segment in segments)
    if len(translations) != expected:
        raise ValueError(f"Expected {expected} translations, received {len(translations)}.")

    translated = iter(translations)
    return "".join(
        next(translated) if segment.translatable else segment.text for segment in segments
    )
