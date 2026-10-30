import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from make_pilot_sheet import make_sheet, score_sheet  # noqa: E402


def _srt(path: Path, lines: list[str]) -> Path:
    body = "\n".join(
        f"{i}\n00:00:{i:02d},000 --> 00:00:{i:02d},500\n{text}\n" for i, text in enumerate(lines, 1)
    )
    path.write_text(body, encoding="utf-8")
    return path


def test_sheet_samples_pairs_and_scores_ratings(tmp_path: Path) -> None:
    english = _srt(tmp_path / "en.srt", [f"line {i}" for i in range(10)])
    other = _srt(tmp_path / "kn.srt", [f"ಸಾಲು {i}" for i in range(10)])

    sheet = make_sheet(english, other, 4, tmp_path / "sheet.csv")
    text = sheet.read_text(encoding="utf-8-sig").replace(",,", ",5,", 4)
    sheet.write_text(text, encoding="utf-8-sig")

    summary = score_sheet(sheet)
    assert summary["rated"] == 4 and summary["average"] == 5.0


def test_mismatched_files_and_empty_scores_are_rejected(tmp_path: Path) -> None:
    a = _srt(tmp_path / "a.srt", ["x", "y"])
    b = _srt(tmp_path / "b.srt", ["x"])
    with pytest.raises(ValueError):
        make_sheet(a, b, 1, tmp_path / "s.csv")
    empty = make_sheet(a, a, 2, tmp_path / "e.csv")
    with pytest.raises(ValueError):
        score_sheet(empty)
