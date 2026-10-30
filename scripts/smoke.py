"""Prove that the required LessonLingo model snapshots are cached offline."""

from lessonlingo.cli import main
from lessonlingo.setup_models import enable_offline_mode

if __name__ == "__main__":
    enable_offline_mode()
    raise SystemExit(main(["verify"]))
