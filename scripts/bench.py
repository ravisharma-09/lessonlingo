"""Time quality vs light mode and write docs/benchmarks.md. Run on the GPU laptop."""

from __future__ import annotations

from pathlib import Path

from smoke import measure

from lessonlingo.translator import MODEL_REPOSITORIES, Mode

OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "benchmarks.md"


def main() -> None:
    """Measure both modes and write a Markdown table."""

    rows = [
        "| Mode | Model | Device | Load + first sentence (s) | Seconds/sentence |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for mode in ("quality", "light"):
        typed: Mode = mode  # type: ignore[assignment]
        try:
            r = measure(typed)
            rows.append(
                f"| {mode} | {MODEL_REPOSITORIES[typed]} | {r['device']} | "
                f"{r['load_seconds']:.1f} | {r['seconds_per_sentence']:.2f} |"
            )
        except Exception as error:  # report, keep benchmarking the other mode
            rows.append(f"| {mode} | {MODEL_REPOSITORIES[typed]} | n/a | n/a | failed: {error} |")
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        "# Benchmarks\n\nMeasured on the Windows test laptop.\n\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
