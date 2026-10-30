"""Read, wrap and write SRT and WebVTT subtitle files."""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, replace
from pathlib import Path

WRAP_WIDTH = 42

_TIME = r"(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})"
_TIMING_LINE = re.compile(rf"^\s*{_TIME}\s*-->\s*{_TIME}")


@dataclass(frozen=True)
class Cue:
    """One subtitle: start and end in seconds, and its text."""

    start: float
    end: float
    text: str


def _seconds(hours: str | None, minutes: str, seconds: str, millis: str) -> float:
    return (
        int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + int(millis.ljust(3, "0")) / 1000
    )


def format_timestamp(seconds: float, separator: str = ",") -> str:
    """Format seconds as HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT)."""

    total_ms = round(max(seconds, 0.0) * 1000)
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def parse_subtitles(text: str) -> list[Cue]:
    """Parse SRT or WebVTT text into cues, keeping the timestamps."""

    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip())
    for block in blocks:
        lines = block.split("\n")
        for index, line in enumerate(lines):
            match = _TIMING_LINE.match(line)
            if match:
                g = match.groups()
                body = " ".join(part.strip() for part in lines[index + 1 :] if part.strip())
                cues.append(Cue(_seconds(*g[0:4]), _seconds(*g[4:8]), body))
                break
    if not cues and text.strip():
        raise ValueError("No subtitle cues found. Use a valid .srt or .vtt file.")
    return cues


def load_subtitles(path: Path) -> list[Cue]:
    """Read a .srt or .vtt file."""

    if Path(path).suffix.lower() not in {".srt", ".vtt"}:
        raise ValueError("Subtitle input must be a .srt or .vtt file.")
    return parse_subtitles(Path(path).read_text(encoding="utf-8-sig"))


def wrap_text(text: str, width: int = WRAP_WIDTH) -> str:
    """Wrap a subtitle onto lines of at most `width` characters, on word boundaries."""

    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False)) or text


def with_text(cues: list[Cue], texts: list[str]) -> list[Cue]:
    """Return the cues with new texts, keeping timestamps and order."""

    if len(cues) != len(texts):
        raise ValueError("Cue and text counts differ.")
    return [replace(cue, text=text) for cue, text in zip(cues, texts, strict=True)]


def _timing(cue: Cue, separator: str) -> str:
    return f"{format_timestamp(cue.start, separator)} --> {format_timestamp(cue.end, separator)}"


def to_srt(cues: list[Cue], width: int = WRAP_WIDTH) -> str:
    """Render cues as SRT with wrapped lines."""

    parts = [
        f"{number}\n{_timing(c, ',')}\n{wrap_text(c.text, width)}\n"
        for number, c in enumerate(cues, start=1)
    ]
    return "\n".join(parts)


def to_vtt(cues: list[Cue], width: int = WRAP_WIDTH) -> str:
    """Render cues as WebVTT with wrapped lines."""

    parts = [f"{_timing(c, '.')}\n{wrap_text(c.text, width)}\n" for c in cues]
    return "WEBVTT\n\n" + "\n".join(parts)
