# LessonLingo

> Free lessons in your language. Set up once, then no internet needed.

LessonLingo is an offline-first tool for translating English lessons into
Indian languages while preserving headings, links, and code blocks. It is
being built around AI4Bharat's MIT-licensed IndicTrans2 models, with a command
line interface and a simple Gradio upload page.

- **Quality mode:** the 1B model, intended for an NVIDIA GPU such as an RTX 4070.
- **Light mode:** the 200M model, intended for an ordinary laptop.
- **Video subtitles:** Subtitles generated on your device after one-time setup.

The current repository contains the one-time model setup and offline cache
verification foundation. Lesson translation and the Gradio interface are still
under development.

## Requirements

- Python 3.11.
- Internet access during installation and `lessonlingo setup` only.
- A free Hugging Face account with access accepted for both gated models:
  [quality (1B)](https://huggingface.co/ai4bharat/indictrans2-en-indic-1B)
  and
  [light (200M)](https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M).
- Approximately **4.5 GB** for the quality model weights and **1.1 GB** for the
  light model weights. The one-step setup downloads both, approximately
  **5.6 GB** of model weights plus metadata and cache overhead.
- An NVIDIA GPU and a compatible PyTorch CUDA build for quality-mode GPU
  acceleration. Light mode is intended to work on CPU.

The model repositories are gated. You must accept their access terms in a
browser once. LessonLingo can handle Hugging Face login, but it cannot accept
those terms for you.

## One-time setup

### macOS or Linux

```bash
git clone https://github.com/ravisharma-09/lessonlingo.git
cd lessonlingo
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
lessonlingo setup
```

### Windows PowerShell

```powershell
git clone https://github.com/ravisharma-09/lessonlingo.git
Set-Location lessonlingo
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
lessonlingo setup
```

If the computer is not already authenticated, `lessonlingo setup` starts the
Hugging Face login flow. It then downloads the quality and light repositories,
excluding duplicate legacy `.bin` weights when safetensors are available.

## Prove offline readiness

After setup, force the Hugging Face libraries into offline mode and verify that
both model snapshots are complete in the local cache.

macOS or Linux:

```bash
HF_HUB_OFFLINE=1 lessonlingo verify
HF_HUB_OFFLINE=1 python scripts/smoke.py
```

Windows PowerShell:

```powershell
$env:HF_HUB_OFFLINE = "1"
lessonlingo verify
python .\scripts\smoke.py
```

Runtime commands also set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`
before importing model libraries. These settings prevent Hugging Face and
Transformers HTTP calls; they are not a system-wide firewall. For the demo,
show the online setup step, turn off Wi-Fi, and then run the offline smoke check
before translating three languages.

## Development

Install the development dependencies and run the test suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Tests use fakes and do not download model files.

## License

Licensed under the [MIT License](LICENSE).
