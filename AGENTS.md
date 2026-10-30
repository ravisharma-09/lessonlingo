# LessonLingo contributor instructions

- Develop on macOS with Python 3.11, but keep runtime code OS-independent.
- Never download or load the real IndicTrans2 models on the Mac.
- Unit tests must use `FakeTranslator` and must not need model access.
- The Windows GPU laptop only synchronizes `origin/main` and runs tests.
- Use the wording: models and dependencies are downloaded once during setup;
  after setup, translating lessons needs no internet connection.
- Do not commit models, tokens, `.env`, outputs, or reports.
- Complete and verify one project phase before starting the next.
