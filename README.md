# LessonLingo

> Free lessons in your language. Set up once, then no internet needed.

LessonLingo translates English Markdown and text lessons into Indian languages
on the user's own computer. It preserves document structure such as headings,
links, tables, HTML tags, and code blocks while translating the lesson text
with AI4Bharat's open IndicTrans2 models. It is designed for teachers and
students who need local access to English-only educational material.

## Project status

LessonLingo translates English text, lecture videos, audio and subtitle files into ten Indian
languages, and speaks the result in Hindi and Kannada. The guided app (`lessonlingo app`) walks
through Add, Languages, Options, Check text and Result; `lessonlingo video` does the same from the
command line. For a lecture it extracts audio with ffmpeg, transcribes it with faster-whisper,
frees the speech model, translates each subtitle with IndicTrans2 and writes `.srt` and `.vtt`
files, and can add a dubbed voice and put everything into one video. Unit tests use deterministic
fakes and never download model files; real model quality and speed are measured on the GPU laptop.

A project page with the specs, setup guide and a recorded demo is in [`site/`](site/)
(https://lessonlingo-site.vercel.app). The app itself runs on your own computer.

## What "offline" means

Models and dependencies are downloaded once during initial setup. After setup,
translating lessons needs no internet connection. The first installation,
Hugging Face login, gated-model approval, and model download do require an
internet connection.

## Requirements

- Python 3.11.
- A free Hugging Face account.
- Internet during installation and `lessonlingo setup`.
- Access accepted in a browser for both gated model repositories:
  [quality (1B)](https://huggingface.co/ai4bharat/indictrans2-en-indic-1B)
  and
  [light (200M)](https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M).
- ffmpeg on your PATH for lecture videos (Windows: `winget install ffmpeg`).
- Approximately 0.5 GB for the speech model, 4.5 GB for the quality weights and 1.1 GB for the light
  weights, plus cache and installation overhead. The setup command downloads
  both modes.
- An NVIDIA GPU with a CUDA-enabled PyTorch installation for quality mode.
  Light mode can use a CUDA GPU or CPU.

The Windows test laptop uses an RTX 4070-class laptop GPU with 8 GB VRAM and
16 GB system RAM. Final memory use and performance must be measured there.

## One-time setup

### Windows PowerShell with NVIDIA CUDA

Clone the project and create the Python environment:

```powershell
git clone https://github.com/ravisharma-09/lessonlingo.git
Set-Location lessonlingo
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Open the [official PyTorch selector](https://pytorch.org/get-started/locally/),
choose Windows, Pip, Python, and the supported CUDA version, then run its exact
installation command. The project lists plain `torch` without a CUDA index URL
so it does not replace that choice.

Install the remaining dependencies:

```powershell
python -m pip install -r requirements.txt
```

If IndicTransToolkit fails to compile on Windows, install the C++ workload from
Visual Studio Build Tools and rerun the requirements command. Do not silently
replace the toolkit with another package.

### macOS or Linux development

```bash
git clone https://github.com/ravisharma-09/lessonlingo.git
cd lessonlingo
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-deps -e .
python -m pip install -r requirements-dev.txt
```

Do not run `lessonlingo setup` or load the real models on the Mac development
machine. Mac development and CI use `FakeTranslator` only.

### Hugging Face login and model download

While the Windows test laptop is online:

1. Open both model links in the requirements section and accept their terms.
2. Sign in with `hf auth login` (`huggingface-cli login` on older clients).
3. Download both model snapshots with one command.

```powershell
lessonlingo setup
```

If access is missing or Hugging Face returns HTTP 401, the command prints both
approval links and exits without claiming setup succeeded.

## Command-line usage

List supported languages:

```powershell
lessonlingo languages
```

Translate one lesson into Hindi and Kannada with the light model:

```powershell
lessonlingo translate .\samples\lesson_en.md `
  --to hin_Deva kan_Knda `
  --mode light `
  --out .\outputs
```

Use quality mode on the CUDA GPU:

```powershell
lessonlingo translate .\samples\lesson_en.md `
  --to hin_Deva kan_Knda tam_Taml `
  --mode quality `
  --out .\outputs
```

Pass a folder instead of a file to translate a whole course; the sub-folder layout is
kept under `--out`.

Output names follow `<source>.<language-code>.md`, for example
`lesson_en.hin_Deva.md`.

### Lecture videos

```powershell
lessonlingo video .\lecture.mp4 --to kan_Knda hin_Deva --mode light --offline --out .\outputs
```

This writes `lecture.en.srt` plus `lecture.<lang>.srt` and `.vtt` per language. An
existing `.srt`/`.vtt` file also works and skips speech recognition. Add `--embed` to also write `lecture.subtitled.mp4`, which holds every language as a
selectable subtitle track (VLC and most players can switch them). If the speech model
fails on CUDA, add `--whisper-device cpu`.

### Web UI

```powershell
lessonlingo app --offline
```

Open http://127.0.0.1:7860. The left menu has five steps and every step has Back and Next:

1. **Add**: text, video, audio or a subtitle file ("Try the sample lecture" needs no file).
2. **Languages**: tick the ones you need; Hindi and Kannada are marked "voice".
3. **Options**: translation model (Fast 200M for any laptop, Best quality 1B needs an NVIDIA GPU),
   what you get (subtitle files; a video with subtitles inside; a video with subtitles and dubbed
   audio), the voice (natural or quick) and words to keep in English. A line under the voice
   options gives the expected time.
4. **Check text**: fix the English before it is translated (video, audio and subtitle input).
5. **Result**: the player has **CC**, **Aa** (subtitle size, position, background, width), **Audio**
   (original or a dubbed voice) and a fullscreen button; downloads and a ready-to-share video
   are below. **Courses** is a separate page for whole folders.

Slow steps show a loader with a timer and a **Cancel** button that really stops the work. The
terminal prints timed lines (`speech recognised in 15.2s`) so a slow step can be seen.
`--lan` lets phones and laptops on the same Wi-Fi or hotspot open the app, with no
internet; use it only on a network you trust. `--warm light` (or `quality`) loads that model in the background so the first translation
is fast. `--offline` (or `LESSONLINGO_OFFLINE=1`) blocks all Hugging Face network calls,
so models must already be downloaded by `lessonlingo setup`.

Quick checks on the GPU laptop:

```powershell
python scripts/smoke.py --mode light --offline
python scripts/bench.py   # writes docs/benchmarks.md
```

### Review and keep-in-English

In the web UI, choosing Text shows English and the translation side by side on the Result page
after translating. Click a translation cell to fix it, then press Save my edits to download the
corrected file. Type words such as `photosynthesis, Python` in the keep-in-English box (or
use `--keep photosynthesis Python` on the command line) to leave them untranslated. Kept
words are swapped for placeholders during translation; if the model drops a placeholder,
that sentence is translated again without protection.

The data flow, module interfaces and UI system are described in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### My courses (folders, videos and batch translation)

The Courses tab of the web app keeps whole courses on disk, under `~/LessonLingo` by default
(`--workspace PATH` or `LESSONLINGO_HOME` changes it):

```
Science 8/
  course.json   glossary.csv   lectures/   lessons/   outputs/   .trash/
```

The same thing from the command line:

```powershell
lessonlingo course new "Science 8" --to kan_Knda hin_Deva
lessonlingo course add "Science 8" .\unit1.mp4 .\notes.md
lessonlingo course status "Science 8"
lessonlingo course translate "Science 8" --offline
```

Create a course, add videos, audio, `.srt` files and lessons (they are sorted into `lectures/`
and `lessons/`), then press Translate everything. All lectures are transcribed first and then
everything is translated, so the speech and translation models never share the GPU. Finished
items are skipped next time. Removing a file moves it to `.trash/`; nothing is deleted
permanently. Course settings hold the languages, the run mode and an optional glossary. The
course pack zip collects every translated file.

### Spoken dubbing in Hindi and Kannada (optional)

`--dub` (or "Video with subtitles and dubbed audio" in the app's Options) speaks each translated
subtitle line in Hindi or Kannada. In the app the preview plays the dubbed video itself and the
**Audio** menu switches between the original sound and each voice, keeping the time and the
subtitles. You also get one `.wav` and one `<name>.<language>.dubbed.mp4` (voice only) per
language, plus `<name>.dubbed.mp4` with the original sound, every voice and every subtitle
language as extra tracks (VLC and most players can switch them; browsers play only the first audio
track, which is why the app plays the per-language videos).

**How long it takes** (measured on the RTX 4070 laptop; the quick voice is an estimate):
natural voice about 8 to 9 minutes for each minute of video; quick voice about 1 minute;
subtitles about 20 seconds. Choose with "Voice quality" in the app or `--voice-engine parler|mms`.

Two voice engines, chosen with `--voice-engine auto|parler|mms` (default `auto`):

| Engine | Sounds like | Size | Licence | Extra setup |
| --- | --- | --- | --- | --- |
| **Indic Parler-TTS** (AI4Bharat) | a real person, named speakers | about 3.8 GB | Apache-2.0 per its Hugging Face page (confirm on the model card) | `git`, an extra package, accept the model terms |
| **Meta MMS-TTS** | robotic but clear | about 145 MB per language | CC-BY-NC 4.0, non-commercial only | none |

`auto` uses Indic Parler-TTS when it is installed and downloaded, otherwise MMS.

One-time setup, while online (natural voice):

```powershell
python -m pip install -r requirements-voice.txt
hf auth login
lessonlingo setup --voices hin_Deva kan_Knda --voice-engine parler
```

Open https://huggingface.co/ai4bharat/indic-parler-tts and accept the terms first. For the small
fallback voice instead: `lessonlingo setup --voices hin_Deva kan_Knda`. Then:

```powershell
lessonlingo video .\lecture.mp4 --to kan_Knda hin_Deva --dub --offline
python scripts/smoke_voice.py --engine both     # writes sample audio to outputs\voice_test
```

Only Hindi and Kannada are offered; other languages are skipped with a note. A spoken line that is
longer than its slot is trimmed of silence, may use the pause after its subtitle, is time-stretched
(pitch kept, ffmpeg `atempo`) by at most 1.5 times and may start up to 0.3 s early; after that the
voice falls a little behind the picture, and the command prints how much.

### Course glossary, transcript check and class pack

- **Check the English first.** In the app, the Check text step shows the English transcript; fix
  any mistakes there, then Translate. Lines the speech model was unsure about are marked Check, with
  the doubtful words named (for example `Check: flay, fart`). The word threshold (probability below
  0.5) is a starting guess; `scripts/show_scores.py` prints the numbers to tune it. When a whole
  course is translated in one go, each lecture with doubtful lines gets an `<name>.check.txt` list
  in its outputs folder.
  Errors in the transcript would otherwise be translated too.
- **Course glossary.** A CSV with a `term` column and one column per language code, for example:

  ```csv
  term,hin_Deva,kan_Knda
  force,बल,
  Python,,
  ```

  A filled cell is the exact word to use in that language. An empty cell keeps the term in
  English. Use it with `--glossary course.csv` or the upload box. The terms are also given to the
  speech model as hints so it hears technical words correctly.
- **Class pack.** `--zip` (and the web UI) also writes a `.classpack.zip` with the subtitles or
  lessons and a START_HERE.txt, easy to copy to a pen drive.
- **Our own docs.** `scripts/translate_docs.ps1` translates this README and CONTRIBUTING into
  Hindi and Kannada under `docs/i18n/`. A speaker should check them before they are committed.
- **Pilot.** [docs/PILOT.md](docs/PILOT.md) explains how a fluent speaker rates 20 lines.

## Supported languages

| Code | Language |
| --- | --- |
| `hin_Deva` | Hindi |
| `kan_Knda` | Kannada |
| `tam_Taml` | Tamil |
| `tel_Telu` | Telugu |
| `mal_Mlym` | Malayalam |
| `ben_Beng` | Bengali |
| `mar_Deva` | Marathi |
| `guj_Gujr` | Gujarati |
| `pan_Guru` | Punjabi |
| `ory_Orya` | Odia |

The source language is always English (`eng_Latn`).

## Quality and light modes

| Mode | Model | Device | Default batch | Load time | Seconds/sentence |
| --- | --- | --- | ---: | ---: | ---: |
| Quality | IndicTrans2 En-Indic 1B | CUDA GPU (RTX 4070 laptop) | 8 | 7.7 to 8.9 s | 0.08 s |
| Light | IndicTrans2 En-Indic 200M | CUDA GPU (RTX 4070 laptop) | 16 | 5.2 to 5.8 s | 0.08 to 0.14 s |
| Light | IndicTrans2 En-Indic 200M | CPU only (same laptop) | 16 | 6.2 s | 0.55 s |

Two runs each, measured with `scripts/smoke.py` on the Windows test laptop (4 sentences into Hindi, Kannada and
Tamil, offline flag on). Load time includes the first sentence. A full `scripts/bench.py` run
writes `docs/benchmarks.md`.

## Proving local operation after setup

After the one-time setup, turn off Wi-Fi manually on the test laptop and run:

```powershell
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
lessonlingo verify
lessonlingo translate .\samples\short_lesson_en.md `
  --to hin_Deva kan_Knda tam_Taml `
  --mode light `
  --out .\outputs
```

`lessonlingo verify` checks that both snapshots are available from the local
cache. The environment variables disable Hugging Face and Transformers network
calls; they are not a system-wide firewall. Turning off Wi-Fi provides the
demo's system-level proof.

## Mac and test-laptop workflow

All source changes are made and fake-tested on the Mac. After a verified commit
is pushed, the Windows laptop synchronizes exactly to `origin/main` and runs the
real environment checks:

```powershell
git fetch origin main
git reset --hard origin/main
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -m "not gpu"
python -m pytest -m gpu --run-gpu
```

The dedicated laptop can continuously watch for new commits:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\watch_and_test.ps1
```

The watcher writes its latest ignored report to `reports/last_run.txt`. The
hard reset is only for the dedicated test laptop, where source code is never
edited.

## Development checks

```bash
python -m pip install --no-deps -e .
python -m pip install -r requirements-dev.txt
ruff check .
pytest -m "not gpu"
```

## Demo flow

The full script is in [docs/DEMO.md](docs/DEMO.md). Short version:

1. While online, show the accepted model pages and run `lessonlingo setup`.
2. Turn off Wi-Fi.
3. Translate `samples/short_lesson_en.md` into Hindi, Kannada, and Tamil.
4. Open the three generated Markdown files and show that links and structure
   remain intact.
5. Report measured GPU and CPU timing only after running the Phase 2 benchmark.

## Limitations

- Machine translation can be wrong. A fluent speaker should review important
  educational material before it is published or taught.
- Sentence segmentation is intentionally simple and dependency-light.
- Quality mode requires CUDA and may not fit every GPU configuration.
- Speech recognition can mishear technical terms, so review subtitles before publishing.
- Subtitles are added as selectable tracks (`--embed`), not burned into the picture.
- Real model loading and generated-language quality are not verified on the Mac.
- Speech recognition runs on the CPU by default (reliable on every machine, about 15 s for each
  minute of audio). Set `LESSONLINGO_WHISPER_DEVICE=cuda` to use the GPU; if its libraries are
  missing it falls back to the CPU.
- The natural voice needs an NVIDIA GPU and takes minutes; Hindi and Kannada only. Meta MMS, the
  quick voice, is non-commercial.
- Only short lectures (about a minute) have been timed end to end. No accuracy rating or
  classroom pilot has been run yet (a pilot sheet is in `docs/PILOT.md`).
- The app is tested on Gradio 6.17.3 (pinned in `requirements.txt`).

## Measured end to end

On the same laptop (RTX 4070 laptop GPU, offline flag on), the 61-second sample lecture went from
video to Kannada, Hindi and Tamil subtitles in 12.4 s with Whisper `small` and the light model.
A course of three files (that lecture, a lesson and a subtitle file) translated into Kannada and
Hindi in 11.2 s. Speech recognition made two clear mistakes on the synthetic narration
("Plants also flay a fart", "the second Akichurtha"), which is why the English transcript can be
corrected before translating. GPU memory during a run has not been measured properly yet.

## Sample files

- `samples/lecture_demo.mp4` is a 61-second test lecture about the water cycle. Its narration was
  made with the macOS built-in voice "Aman" (synthetic speech) from `samples/lecture_demo_script.txt`;
  the picture is a plain green screen. It exists so anyone can try the video flow without
  recording anything. Real teachers' voices and accents are harder, so record your own for a real
  evaluation.
- `samples/lecture_en.srt`, `samples/lesson_en.md` and `samples/short_lesson_en.md` are short
  texts written for this project.

## AI tools used

This project was written with AI coding assistants: OpenAI Codex (initial repository,
translation pipeline and CLI) and Anthropic Claude Code (web UI, lecture video flow,
glossary, review table, documentation). Every team member can explain the code.
Translation itself uses open models only (IndicTrans2, Whisper), run locally.

## Credits and licences

LessonLingo is licensed under the [MIT License](LICENSE).

Translation uses
[IndicTrans2 by AI4Bharat](https://github.com/AI4Bharat/IndicTrans2) and
[IndicTransToolkit](https://github.com/VarunGumma/IndicTransToolkit), both
distributed under MIT licences. Speech recognition uses
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT) with OpenAI Whisper weights. IndicTrans2 model access remains subject to
the terms displayed on each Hugging Face model page.
