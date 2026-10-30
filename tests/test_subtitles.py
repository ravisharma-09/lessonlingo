import pytest

from lessonlingo.subtitles import (
    Cue,
    format_timestamp,
    parse_subtitles,
    to_srt,
    to_vtt,
    with_text,
    wrap_text,
)

SRT = """1
00:00:01,000 --> 00:00:03,500
Hello class.

2
00:00:04,000 --> 00:01:05,250
Today we study the water cycle.
"""


def test_parse_srt_keeps_timestamps() -> None:
    cues = parse_subtitles(SRT)

    assert cues == [
        Cue(1.0, 3.5, "Hello class."),
        Cue(4.0, 65.25, "Today we study the water cycle."),
    ]


def test_srt_round_trip() -> None:
    assert to_srt(parse_subtitles(SRT)).strip() == SRT.strip()


def test_parse_vtt_with_header_and_dot_milliseconds() -> None:
    cues = parse_subtitles("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHi there\n")

    assert cues == [Cue(1.0, 2.0, "Hi there")]


def test_vtt_output_uses_dot_separator() -> None:
    assert to_vtt([Cue(0, 1.5, "Hi")]).startswith("WEBVTT\n\n00:00:00.000 --> 00:00:01.500")


def test_with_text_keeps_timing_and_checks_count() -> None:
    cues = [Cue(0, 1, "a"), Cue(1, 2, "b")]

    assert with_text(cues, ["x", "y"]) == [Cue(0, 1, "x"), Cue(1, 2, "y")]
    with pytest.raises(ValueError):
        with_text(cues, ["x"])


def test_wrap_text_breaks_long_lines_on_words() -> None:
    lines = wrap_text("word " * 20, width=30).split("\n")

    assert len(lines) > 1 and all(len(line) <= 30 for line in lines)


def test_format_timestamp_rounds_and_pads() -> None:
    assert format_timestamp(3661.0049) == "01:01:01,005"


def test_garbage_input_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_subtitles("this is not a subtitle file")
