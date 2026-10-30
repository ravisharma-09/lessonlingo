"""Make a CSV for a fluent speaker to rate sample translations.

Usage:
    python scripts/make_pilot_sheet.py outputs/lecture.en.srt outputs/lecture.kan_Knda.srt --n 20

The speaker fills the `rating` column (1 = wrong, 3 = understandable, 5 = natural) and
`comment`. Then run `python scripts/make_pilot_sheet.py --score sheet.csv` for the summary.
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from lessonlingo.subtitles import load_subtitles


def make_sheet(english: Path, translated: Path, count: int, out: Path, seed: int = 7) -> Path:
    """Write a CSV of `count` randomly chosen English/translation pairs."""

    source = load_subtitles(english)
    target = load_subtitles(translated)
    if len(source) != len(target):
        raise ValueError("The two subtitle files must have the same number of lines.")
    picks = sorted(random.Random(seed).sample(range(len(source)), min(count, len(source))))
    with out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["line", "english", "translation", "rating", "comment"])
        for index in picks:
            writer.writerow([index + 1, source[index].text, target[index].text, "", ""])
    return out


def score_sheet(sheet: Path) -> dict[str, float]:
    """Summarise a rated sheet: lines rated, average rating, share rated 4 or 5."""

    with sheet.open(encoding="utf-8-sig", newline="") as handle:
        ratings = [int(r["rating"]) for r in csv.DictReader(handle) if r["rating"].strip()]
    if not ratings:
        raise ValueError("No ratings found. Fill the `rating` column first.")
    return {
        "rated": len(ratings),
        "average": round(sum(ratings) / len(ratings), 2),
        "share_4_or_5": round(sum(r >= 4 for r in ratings) / len(ratings), 2),
    }


def main() -> None:
    """Command-line entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("english", nargs="?", type=Path)
    parser.add_argument("translated", nargs="?", type=Path)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--out", type=Path, default=Path("pilot_sheet.csv"))
    parser.add_argument("--score", type=Path, help="summarise an already rated sheet")
    args = parser.parse_args()
    if args.score:
        print(score_sheet(args.score))
    elif args.english and args.translated:
        print(make_sheet(args.english, args.translated, args.n, args.out))
    else:
        parser.error("give the English and translated files, or --score SHEET")


if __name__ == "__main__":
    main()
