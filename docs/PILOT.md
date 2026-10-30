# Quality pilot

A fluent speaker rates sample lines. This is our real-world check that the translations are usable.

1. Translate a lecture: `lessonlingo video lecture.mp4 --to kan_Knda --offline`.
2. Make the sheet: `python scripts/make_pilot_sheet.py outputs/lecture.en.srt outputs/lecture.kan_Knda.srt --n 20`.
3. Give `pilot_sheet.csv` to a fluent speaker. Scale: 1 = wrong or misleading, 3 = understandable,
   5 = natural. They also note wrong technical terms in `comment`.
4. Score it: `python scripts/make_pilot_sheet.py --score pilot_sheet.csv`.
5. Add the result below.

| Language | Reviewer | Lines rated | Average (1 to 5) | Share rated 4 or 5 | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| Not run yet | | | | | |
