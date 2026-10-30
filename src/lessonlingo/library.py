"""The "My courses" tab: folders of lectures and lessons, translated together."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from lessonlingo.languages import SUPPORTED_LANGUAGES
from lessonlingo.translator import Mode
from lessonlingo.video import Transcriber
from lessonlingo.workspace import Workspace


def item_rows(workspace: Workspace, course: str | None) -> list[list[str]]:
    """Table rows [name, type, translated into] for a course."""

    if not course:
        return []
    return [
        [
            item.name,
            item.kind.capitalize(),
            ", ".join(SUPPORTED_LANGUAGES[c] for c in item.done) or "Not yet",
        ]
        for item in workspace.list_items(course)
    ]


def build_library_tab(
    gr: Any,
    workspace: Workspace,
    models: Any,
    transcriber_factory: Callable[..., Transcriber],
    friendly_error: Callable[[Exception], str],
    language_choices: list[tuple[str, str]],
    mode_choices: list[tuple[str, str]],
) -> SimpleNamespace:
    """Create the components and handlers of the course tab inside the current Blocks."""

    def snapshot(course: str | None, note: str = "") -> tuple[Any, ...]:
        """Everything that depends on the chosen course, in one update."""

        if not course:
            hint = note or "No courses yet. Type a name above and press Create course."
            return (
                hint,
                [],
                gr.Dropdown(choices=[], value=None),
                [],
                "light",
                gr.File(visible=False),
            )
        saved = workspace.settings(course)
        names = [i.name for i in workspace.list_items(course)]
        pack = workspace.course_pack(course)
        return (
            note,
            item_rows(workspace, course),
            gr.Dropdown(choices=names, value=names[0] if names else None),
            saved["targets"],
            saved["mode"],
            gr.File(value=str(pack), visible=True) if pack else gr.File(visible=False),
        )

    def on_create(name: str) -> tuple[Any, ...]:
        try:
            workspace.create_course(name)
        except ValueError as error:
            raise gr.Error(str(error)) from error
        created = name.strip()
        return (
            gr.Dropdown(choices=workspace.list_courses(), value=created),
            *snapshot(created, f"Created '{created}'. Add your videos and lessons next."),
        )

    def on_load() -> tuple[Any, ...]:
        names = workspace.list_courses()
        chosen = names[0] if names else None
        return (gr.Dropdown(choices=names, value=chosen), *snapshot(chosen))

    def on_pick(course: str | None) -> tuple[Any, ...]:
        return snapshot(course)

    def on_add(course: str | None, files: list[str] | None) -> tuple[Any, ...]:
        if not course:
            raise gr.Error("Create or choose a course first.")
        if not files:
            raise gr.Error("Choose at least one video or lesson file.")
        added, skipped = 0, []
        for file in files:
            try:
                workspace.add_file(course, Path(file))
                added += 1
            except ValueError as error:
                skipped.append(str(error))
        note = f"Added {added} file(s)." + (f" Skipped: {' '.join(skipped)}" if skipped else "")
        return (*snapshot(course, note), None)

    def on_translate_all(course: str | None, progress: Any = None) -> tuple[Any, ...]:
        if not course:
            raise gr.Error("Create or choose a course first.")
        progress = progress or gr.Progress()
        mode: Mode = workspace.settings(course)["mode"]  # type: ignore[assignment]
        models.close()  # free the GPU before the speech model loads
        try:
            written = workspace.translate_course(
                course,
                models.get(mode),
                transcriber_factory,
                status=lambda message: progress(None, desc=message),
            )
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            raise gr.Error(friendly_error(error)) from error
        note = (
            f"Done. {len(written)} file(s) written."
            if written
            else "Everything is already translated."
        )
        return snapshot(course, note)

    def on_remove(course: str | None, item: str | None, confirmed: bool) -> tuple[Any, ...]:
        if not course or not item:
            raise gr.Error("Choose the file to remove.")
        if not confirmed:
            raise gr.Error("Tick the box to confirm. The file moves to the course's .trash folder.")
        workspace.trash_item(course, item)
        return (*snapshot(course, f"Moved '{item}' to .trash."), False)

    def on_save_settings(
        course: str | None, targets: list[str], mode: Mode, sheet: str | None
    ) -> tuple[Any, ...]:
        if not course:
            raise gr.Error("Create or choose a course first.")
        try:
            workspace.save_settings(course, targets, mode)
            if sheet:
                workspace.save_glossary(course, Path(sheet))
        except ValueError as error:
            raise gr.Error(str(error)) from error
        return snapshot(course, "Settings saved.")

    courses = workspace.list_courses()
    first = courses[0] if courses else None
    gr.Markdown(
        "Keep a whole course in one place: add videos and lessons, then translate them all."
    )
    with gr.Row():
        course = gr.Dropdown(label="Course", choices=courses, value=first, scale=2)
        new_name = gr.Textbox(label="New course name", placeholder="Science grade 8", scale=2)
        create = gr.Button("Create course", scale=1)
    note = gr.Markdown()
    upload = gr.File(
        label="Add videos, audio, .srt files and lessons (.md, .txt)",
        file_count="multiple",
    )
    add = gr.Button("Add to course", size="sm")
    table = gr.Dataframe(
        headers=["Name", "Type", "Translated into"],
        datatype=["str", "str", "str"],
        interactive=False,
        wrap=True,
        type="array",
        value=item_rows(workspace, first),
    )
    translate_all = gr.Button("Translate everything", variant="primary", size="lg")
    pack = gr.File(label="Course pack (.zip) for sharing", visible=False)
    with gr.Accordion("One file: check or remove", open=False):
        item = gr.Dropdown(label="File", choices=[], value=None)
        send = gr.Button("Check this lecture's English first")
        confirm = gr.Checkbox(label="Yes, move this file to the trash")
        remove = gr.Button("Remove file")
    with gr.Accordion("Course settings", open=False):
        targets = gr.CheckboxGroup(label="Languages", choices=language_choices, value=[])
        mode = gr.Radio(label="How should it run?", choices=mode_choices, value="light")
        sheet = gr.File(
            label="Course glossary (.csv: term, then the exact word per language)",
            file_types=[".csv"],
            type="filepath",
        )
        save = gr.Button("Save settings")

    view = [note, table, item, targets, mode, pack]
    create.click(on_create, [new_name], [course, *view])
    course.change(on_pick, [course], view)
    add.click(on_add, [course, upload], [*view, upload])
    translate_all.click(on_translate_all, [course], view)
    remove.click(on_remove, [course, item, confirm], [*view, confirm])
    save.click(on_save_settings, [course, targets, mode, sheet], view)
    return SimpleNamespace(course=course, item=item, send=send, view=view, on_load=on_load)
