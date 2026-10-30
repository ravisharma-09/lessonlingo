# Contributing to LessonLingo

Thanks for helping make lessons available in more languages.

## Set up (no models needed)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
python -m pip install --no-deps -e .
python -m pip install -r requirements-dev.txt
ruff check . && pytest -m "not gpu"
```

Unit tests use `FakeTranslator` and `FakeTranscriber`. They must never download a model or need
a GPU. Real-model checks live in `tests/test_gpu_smoke.py` and `scripts/`.

## Pull requests

- Keep changes small, one idea each. Commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Add or update a test for behaviour you change. Public functions need a docstring and type hints.
- Keep the wording rule: "offline" means models are downloaded once during setup, then
  translating needs no internet. Never claim it works with no internet on the first run.
- Do not commit model weights, tokens, `.env`, `outputs/` or `reports/`.

## Good first issues

- Add a glossary option to keep chosen terms in English.
- Add side-by-side review of English and translated lines.
- Burn subtitles into the video with ffmpeg.
- Translate a whole folder of lessons in one command.
- Add more target languages that IndicTrans2 supports.
