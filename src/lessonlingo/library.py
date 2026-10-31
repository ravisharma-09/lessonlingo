"""The "My courses" tab: folders of lectures and lessons, translated together."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from lessonlingo import cancel
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
        if not workspace.settings(course)["targets"]:
            raise gr.Error("Pick languages and press Save settings first.")
        if not workspace.list_items(course):
            raise gr.Error("This course has no files yet. Add some first.")
        cancel.reset()
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
    with gr.Row(elem_classes="split"):
        with gr.Column(scale=2, min_width=320, elem_classes="side-card"):
            course = gr.Dropdown(label="Course", choices=courses, value=first)
            with gr.Row():
                new_name = gr.Textbox(
                    show_label=False, placeholder="New course name", scale=3, container=False
                )
                create = gr.Button("Create", scale=1)
            note = gr.Markdown(elem_classes="hint")
            upload = gr.File(
                label="Add files (video, audio, .srt, lessons)",
                file_count="multiple",
            )
            add = gr.Button("Add to course", variant="secondary")
        with gr.Column(scale=3, min_width=320, elem_classes="side-card"):
            targets = gr.CheckboxGroup(label="Languages", choices=language_choices, value=[])
            mode = gr.Radio(
                label="Translation model",
                choices=mode_choices,
                value="light",
                elem_classes="lang-chips",
            )
            sheet = gr.File(
                label="Glossary file (.csv, optional)",
                file_types=[".csv"],
                type="filepath",
            )
            save = gr.Button("Save settings", variant="secondary")
    table = gr.Dataframe(
        headers=["Name", "Type", "Translated into"],
        datatype=["str", "str", "str"],
        interactive=False,
        wrap=True,
        type="array",
        value=item_rows(workspace, first),
    )
    pack = gr.File(label="Course pack (.zip)", visible=False)
    with gr.Accordion("Manage one file", open=False):
        item = gr.Dropdown(label="File", choices=[], value=None)
        send = gr.Button("Open in Add", variant="secondary")
        confirm = gr.Checkbox(label="Yes, move this file to the trash")
        remove = gr.Button("Remove file", variant="secondary")
    with gr.Row(elem_classes="nav-bar"):
        translate_all = gr.Button("Translate everything", variant="primary", size="lg")

    view = [note, table, item, targets, mode, pack]
    create.click(on_create, [new_name], [course, *view])
    course.change(on_pick, [course], view)
    add.click(on_add, [course, upload], [*view, upload])
    translate_event = translate_all.click(
        on_translate_all,
        [course],
        view,
        js=(
            "(...args) => { window.llBusy('Translating the whole course', "
            "'One file after the other. You can cancel any time.'); return args; }"
        ),
    )
    translate_event.then(None, None, None, js="() => window.llDone()")
    remove.click(on_remove, [course, item, confirm], [*view, confirm])
    save.click(on_save_settings, [course, targets, mode, sheet], view)
    return SimpleNamespace(
        course=course,
        item=item,
        send=send,
        view=view,
        on_load=on_load,
        translate_event=translate_event,
    )
