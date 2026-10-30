# LessonLingo

> Free lessons in your language. Set up once, then no internet needed.

LessonLingo translates English Markdown and text lessons into Indian languages
on the user's own computer. It preserves document structure such as headings,
links, tables, HTML tags, and code blocks while translating the lesson text
with AI4Bharat's open IndicTrans2 models. It is designed for teachers and
students who need local access to English-only educational material.

## Project status

LessonLingo translates text lessons and English lecture videos. The video flow
(`lessonlingo video`, or the Lecture video tab in `lessonlingo app`) extracts audio
with ffmpeg, transcribes it with faster-whisper, frees the speech model, then
translates each subtitle with IndicTrans2 and writes `.srt` and `.vtt` files.
The video flow is tested with fakes on the Mac and still needs a real run on the GPU laptop. Unit
tests use a deterministic fake translator and never download model files.

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
existing `.srt`/`.vtt` file also works and skips speech recognition. If the speech model
fails on CUDA, add `--whisper-device cpu`.

### Web UI

```powershell
lessonlingo app --offline
```

Open http://127.0.0.1:7860. Paste a lesson or upload a `.md`/`.txt` file, pick
languages, choose quick or best quality, and download one file per language.
`--offline` (or `LESSONLINGO_OFFLINE=1`) blocks all Hugging Face network calls,
so models must already be downloaded by `lessonlingo setup`.

Quick checks on the GPU laptop:

```powershell
python scripts/smoke.py --mode light --offline
python scripts/bench.py   # writes docs/benchmarks.md
```

### Review and keep-in-English

In the web UI, the Text lesson tab shows English and the translation side by side after
translating. Click a translation cell to fix it, then press Save my edits to download the
corrected file. Type words such as `photosynthesis, Python` in the keep-in-English box (or
use `--keep photosynthesis Python` on the command line) to leave them untranslated. Kept
words are swapped for placeholders during translation; if the model drops a placeholder,
that sentence is translated again without protection.

The data flow, module interfaces and UI system are described in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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
| Quality | IndicTrans2 En-Indic 1B | CUDA GPU | 8 | Not measured | Not measured |
| Light | IndicTrans2 En-Indic 200M | CUDA or CPU | 16 | Not measured | Not measured |

Timing fields stay "Not measured" until `scripts/bench.py` is run on the Windows GPU
laptop; results are written to `docs/benchmarks.md`.

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
- Subtitles are not burned into the video; use the `.vtt`/`.srt` with any player.
- Real model loading and generated-language quality are not verified on the Mac.

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
