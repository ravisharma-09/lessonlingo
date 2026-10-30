# Demo script (about 3 minutes)

Pitch line: **Free lectures in your language. Set up once, then no internet needed.**

Before the demo (online, once): `lessonlingo setup`, then
`python scripts/smoke_video.py lecture.mp4` to warm up and confirm the GPU.

1. **Problem (20s).** Great lectures are in English. Many students learn in Kannada, Hindi, Tamil.
2. **Open the app (10s).** Run `scripts\run_demo.ps1` (checks the models, loads one in the background, opens http://127.0.0.1:7860). Lecture video tab.
3. **Go offline (15s).** Turn Wi-Fi off on stage. The models are already on this laptop.
4. **Translate (60s).** Drop in the 60-90 second lecture clip. Pick Kannada and Hindi. Click Translate lecture. Name the stages as they pass: listening, translating.
5. **Play it (40s).** Choose the language and play the video with subtitles. Download the `.srt`.
6. **Text lessons (20s).** Show the Text lesson tab: headings, lists and links stay intact.
7. **Close (15s).** Open source (MIT), IndicTrans2 by AI4Bharat, runs on a laptop. Machine translation can be wrong, so teachers review before sharing.

Fallback if live transcription fails: run
`lessonlingo video samples/lecture_en.srt --to kan_Knda hin_Deva --offline`
(skips speech recognition), or play the pre-generated files in `samples/`.
