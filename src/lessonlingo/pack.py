"""Bundle translated files into one zip that can be shared on a pen drive."""

from __future__ import annotations

import zipfile
from pathlib import Path

START_HERE = """LessonLingo class pack

Files in this pack:
{files}

How to use:
- Subtitle files (.srt, .vtt): open the video in VLC, then Subtitle > Add Subtitle File.
  Keep the subtitle file next to the video with a matching name and most players find it.
- Lesson files (.md): open in any text editor or Markdown viewer.

Machine translation can be wrong. Ask a speaker of the language to check the material
before teaching with it.

Made with LessonLingo (open source, MIT).
"""


def make_class_pack(files: list[Path], zip_path: Path) -> Path:
    """Write the files and a START_HERE.txt into a zip and return its path."""

    names = [Path(f).name for f in files]
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "START_HERE.txt", START_HERE.format(files="\n".join(f"- {n}" for n in names))
        )
        for path, name in zip(files, names, strict=True):
            archive.write(path, name)
    return zip_path
