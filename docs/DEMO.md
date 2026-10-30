# Demo script (about 3 minutes)

Pitch line: **Free lessons in your language. Set up once, then no internet needed.**

Before the demo (online, once): `lessonlingo setup`, then `python scripts/smoke.py` to warm up and confirm the GPU.

1. **Problem (20s).** Good lessons are in English. Many students learn in Kannada, Hindi, Tamil and more.
2. **Open the app (10s).** `lessonlingo app --offline` then open http://127.0.0.1:7860.
3. **Go offline (15s).** Turn Wi-Fi off on stage. Say: models were downloaded once during setup; nothing more is needed.
4. **Translate (60s).** Paste or upload `samples/short_lesson_en.md`. Pick Hindi, Kannada, Tamil. Choose "Quick and light". Click Translate lesson.
5. **Show the result (40s).** Download a file. Point out that the heading, numbered list and link are unchanged and only the text is translated.
6. **Quality mode (20s).** Switch to "Best quality", translate again, compare.
7. **Close (15s).** Open source (MIT), IndicTrans2 by AI4Bharat, runs on a laptop. Machine translation can be wrong, so teachers should review important material.

Fallback if the model fails live: run the same command from the terminal
(`lessonlingo translate samples/short_lesson_en.md --to hin_Deva kan_Knda tam_Taml --mode light --offline`)
or show the files already saved in `outputs/`.
