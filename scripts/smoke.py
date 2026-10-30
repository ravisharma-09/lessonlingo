"""Prove that the required LessonLingo model snapshots are cached offline."""

from lessonlingo.cli import enable_offline_mode, main


if __name__ == "__main__":
    enable_offline_mode()
    raise SystemExit(main(["verify"]))
