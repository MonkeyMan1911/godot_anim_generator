#!/usr/bin/env python3
"""
Godot Animation Generator - Textual TUI edition

A real GUI-like TUI: every field is visible at once, you tab or click
between them, toggle switches with the mouse, pick the output file from
a clickable directory tree, and hit one "Generate" button - no chains of
Enter prompts.

Run with:
    pip install textual
    python3 godot_anim_generator_textual.py
"""

import math
import os
import random
import re
import string

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)


# region Helper / generation functions (unchanged logic from the original script)
def round_up(number, decimals=0):
    factor = 10 ** decimals
    return math.ceil(number * factor) / factor


def get_values(row_number, num_frames, height, width, fps):
    values = []
    times = []
    for i in range(num_frames):
        values.append(f"Rect2({i * width}, {row_number * height}, {height}, {width})")
        times.append(round_up(i / fps, 7))
    return {"values": values, "times": times}


_ANIMPLAYER_RE = re.compile(r'^\[node name="[^"]*" type="AnimationPlayer"')


def _random_id_suffix(length: int = 5) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _find_first_node_index(lines: list[str]):
    for i, line in enumerate(lines):
        if line.lstrip().startswith("[node "):
            return i
    return None


def _find_animationplayer_index(lines: list[str]):
    for i, line in enumerate(lines):
        if _ANIMPLAYER_RE.match(line.strip()):
            return i
    return None


def _format_entries(animation_names: list[str]) -> list[str]:
    """&"name": SubResource("Animation_name") lines, comma-separated, no
    trailing comma on the last one - matches real Godot _data formatting."""
    entries = []
    last = len(animation_names) - 1
    for i, name in enumerate(animation_names):
        comma = "," if i != last else ""
        entries.append(f'&"{name}": SubResource("Animation_{name}"){comma}\n')
    return entries


def write_library(file_name: str, animation_names: list[str], animation_text: str) -> str | None:
    """Writes the Animation sub_resources into file_name and makes sure they
    end up in an AnimationLibrary's _data dict.

    - If the file already has a `[sub_resource type="AnimationLibrary" ...]`
      block (with a `_data = { ... }` dict under it), the new entries are
      appended into that dict.
    - If it doesn't (a bare scene straight out of the editor), a brand new
      AnimationLibrary sub_resource is created and, if an AnimationPlayer
      node is present, wired up via `libraries/ = SubResource(...)`.

    Returns a warning string if something noteworthy happened (e.g. no
    AnimationPlayer to link to), or None if everything went cleanly.
    """
    with open(file_name, "r") as file:
        lines = file.readlines()

    library_header_idx = None
    for i, line in enumerate(lines):
        if '[sub_resource type="AnimationLibrary"' in line:
            library_header_idx = i
            break

    if library_header_idx is not None:
        # --- Existing AnimationLibrary: append into its _data dict ---
        data_idx = None
        for i in range(library_header_idx + 1, min(library_header_idx + 4, len(lines))):
            if lines[i].strip().startswith("_data"):
                data_idx = i
                break
        if data_idx is None:
            raise ValueError(
                'Found a [sub_resource type="AnimationLibrary" ...] block but no '
                '"_data = {" dict underneath it - the file doesn\'t look like a '
                "normal Godot scene."
            )

        close_idx = None
        for i in range(data_idx + 1, len(lines)):
            if lines[i].strip() == "}":
                close_idx = i
                break
        if close_idx is None:
            raise ValueError("Could not find the closing '}' of the AnimationLibrary's _data block")

        # Make sure whatever was previously the last entry now ends with a comma
        if close_idx > data_idx + 1:
            prev = lines[close_idx - 1].rstrip("\n")
            if not prev.rstrip().endswith(","):
                lines[close_idx - 1] = prev + ",\n"

        lines[close_idx:close_idx] = _format_entries(animation_names)
        lines.insert(library_header_idx, animation_text)

        with open(file_name, "w") as file:
            file.writelines(lines)
        return None

    # --- No AnimationLibrary yet: create one from scratch ---
    library_id = f"AnimationLibrary_{_random_id_suffix()}"
    library_block = (
        f'[sub_resource type="AnimationLibrary" id="{library_id}"]\n'
        "_data = {\n"
        + "".join(_format_entries(animation_names))
        + "}\n\n"
    )

    insert_idx = _find_first_node_index(lines)
    if insert_idx is None:
        insert_idx = len(lines)
    lines[insert_idx:insert_idx] = [animation_text, library_block]

    player_idx = _find_animationplayer_index(lines)
    if player_idx is not None:
        lines.insert(player_idx + 1, f'libraries/ = SubResource("{library_id}")\n')

    with open(file_name, "w") as file:
        file.writelines(lines)

    if player_idx is None:
        return (
            f'Created a new AnimationLibrary ("{library_id}") but found no '
            "AnimationPlayer node to link it to. Add one in Godot, then set "
            f'libraries/ = SubResource("{library_id}") on it manually.'
        )
    return None


def generate_animation(name, fps, ticks, loop, num_frames, value_time):
    code = (
        f'[sub_resource type="Animation" id="Animation_{name}"]\n'
        f'resource_name = "{name}"\n'
        f'length = {ticks / fps}\n'
        f'loop_mode = {loop}\n'
        f'step = {round_up(1 / fps, 8)}\n'
        'tracks/0/type = "value"\n'
        'tracks/0/imported = false\n'
        'tracks/0/enabled = true\n'
        'tracks/0/path = NodePath("Sprite2D:region_rect")\n'
        'tracks/0/interp = 1\n'
        'tracks/0/loop_wrap = true\n'
        'tracks/0/keys = { \n'
        f'"times": PackedFloat32Array{tuple(value_time["times"])},\n'
        f'"transitions": PackedFloat32Array({"1, " * (num_frames - 1)}1),\n'
        '"update": 1,\n'
        f'"values": [{", ".join(value_time["values"])}]\n'
        '}\n\n'
    )
    return code
# endregion


DIRECTIONS = ["Up", "Down", "Left", "Right"]


class FilePicker(ModalScreen[str | None]):
    """Click-around directory tree for picking the output .tscn file."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    FilePicker {
        align: center middle;
    }
    #picker-dialog {
        width: 80%;
        height: 80%;
        border: round $accent;
        background: $panel;
        padding: 1 2;
    }
    #picker-tree {
        height: 1fr;
        border: solid $primary;
        margin-top: 1;
    }
    #picker-nav {
        height: auto;
        margin-top: 1;
        align: left middle;
    }
    #picker-nav Button {
        margin-right: 1;
        width: auto;
    }
    #picker-current-path {
        color: $text-muted;
    }
    #picker-buttons {
        height: auto;
        margin-top: 1;
        align: right middle;
    }
    #picker-hint {
        color: $text-muted;
    }
    """

    def __init__(self, start_path: str = ".") -> None:
        super().__init__()
        self.start_path = os.path.abspath(start_path)

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-dialog"):
            yield Label("Select output .tscn file", id="picker-title")
            yield Label("Click a file to select it, double-click a folder to open it.", id="picker-hint")
            with Horizontal(id="picker-nav"):
                yield Button("⬆ Up one level", id="picker-up")
                yield Label(self.start_path, id="picker-current-path")
            yield DirectoryTree(self.start_path, id="picker-tree")
            with Horizontal(id="picker-buttons"):
                yield Button("Cancel", id="picker-cancel", variant="error")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.dismiss(str(event.path))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "picker-cancel":
            self.dismiss(None)
        elif event.button.id == "picker-up":
            self._go_up()

    def _go_up(self) -> None:
        tree = self.query_one("#picker-tree", DirectoryTree)
        current = str(tree.path)
        parent = os.path.dirname(os.path.abspath(current))
        if parent and parent != os.path.abspath(current):
            tree.path = parent
            self.query_one("#picker-current-path", Label).update(parent)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AnimatorApp(App):
    TITLE = "Godot Animation Generator"

    CSS = """
    Screen {
        layout: vertical;
    }
    .form-row {
        height: auto;
        margin-bottom: 1;
    }
    .form-row Label {
        width: 26;
        height: 3;
        content-align: left middle;
    }
    .form-row Input, .form-row Select {
        width: 1fr;
        height: 3;
    }
    .file-row Input {
        width: 1fr;
        height: 3;
    }
    .file-row Button {
        margin-left: 1;
        width: auto;
        height: 3;
    }
    #single-status, #multi-status {
        margin-top: 1;
        height: auto;
    }
    .generate-btn {
        margin-top: 1;
        width: auto;
    }
    VerticalScroll {
        padding: 1 2;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="single-tab"):
            with TabPane("Single Animation", id="single-tab"):
                with VerticalScroll():
                    with Horizontal(classes="form-row"):
                        yield Label("Animation name")
                        yield Input(placeholder="e.g. walk_up", id="single_name")
                    with Horizontal(classes="form-row"):
                        yield Label("FPS")
                        yield Input(placeholder="12", type="number", id="single_fps")
                    with Horizontal(classes="form-row"):
                        yield Label("Usable ticks")
                        yield Input(placeholder="4", type="number", id="single_ticks")
                    with Horizontal(classes="form-row"):
                        yield Label("Loop")
                        yield Switch(value=True, id="single_loop")
                    with Horizontal(classes="form-row"):
                        yield Label("Row number (0-indexed)")
                        yield Input(placeholder="0", type="integer", id="single_row")
                    with Horizontal(classes="form-row"):
                        yield Label("Number of frames")
                        yield Input(placeholder="4", type="integer", id="single_frames")
                    with Horizontal(classes="form-row"):
                        yield Label("Sprite height (px)")
                        yield Input(placeholder="32", type="integer", id="single_height")
                    with Horizontal(classes="form-row"):
                        yield Label("Sprite width (px)")
                        yield Input(placeholder="32", type="integer", id="single_width")
                    with Horizontal(classes="form-row file-row"):
                        yield Label("Output file")
                        yield Input(placeholder="No file selected", id="single_file", disabled=True)
                        yield Button("Browse...", id="single_browse")
                    yield Button("Generate Animation", id="single_generate", variant="primary", classes="generate-btn")
                    yield Static("", id="single_status")

            with TabPane("Multi-Directional", id="multi-tab"):
                with VerticalScroll():
                    with Horizontal(classes="form-row"):
                        yield Label("1st direction")
                        yield Select(((d, d) for d in DIRECTIONS), value="Up", id="multi_order_1", allow_blank=False)
                    with Horizontal(classes="form-row"):
                        yield Label("2nd direction")
                        yield Select(((d, d) for d in DIRECTIONS), value="Down", id="multi_order_2", allow_blank=False)
                    with Horizontal(classes="form-row"):
                        yield Label("3rd direction")
                        yield Select(((d, d) for d in DIRECTIONS), value="Left", id="multi_order_3", allow_blank=False)
                    with Horizontal(classes="form-row"):
                        yield Label("4th direction")
                        yield Select(((d, d) for d in DIRECTIONS), value="Right", id="multi_order_4", allow_blank=False)
                    with Horizontal(classes="form-row"):
                        yield Label("Type (idle, walk, etc.)")
                        yield Input(placeholder="walk", id="multi_type")
                    with Horizontal(classes="form-row"):
                        yield Label("FPS")
                        yield Input(placeholder="12", type="number", id="multi_fps")
                    with Horizontal(classes="form-row"):
                        yield Label("Usable ticks")
                        yield Input(placeholder="4", type="number", id="multi_ticks")
                    with Horizontal(classes="form-row"):
                        yield Label("Loop")
                        yield Switch(value=True, id="multi_loop")
                    with Horizontal(classes="form-row"):
                        yield Label("Row number start (0-indexed)")
                        yield Input(placeholder="0", type="integer", id="multi_row")
                    with Horizontal(classes="form-row"):
                        yield Label("Number of frames")
                        yield Input(placeholder="4", type="integer", id="multi_frames")
                    with Horizontal(classes="form-row"):
                        yield Label("Sprite height (px)")
                        yield Input(placeholder="32", type="integer", id="multi_height")
                    with Horizontal(classes="form-row"):
                        yield Label("Sprite width (px)")
                        yield Input(placeholder="32", type="integer", id="multi_width")
                    with Horizontal(classes="form-row file-row"):
                        yield Label("Output file")
                        yield Input(placeholder="No file selected", id="multi_file", disabled=True)
                        yield Button("Browse...", id="multi_browse")
                    yield Button("Generate Animations", id="multi_generate", variant="primary", classes="generate-btn")
                    yield Static("", id="multi_status")
        yield Footer()

    # region field helpers
    def _req_str(self, selector: str, label: str) -> str:
        value = self.query_one(selector, Input).value.strip()
        if not value:
            raise ValueError(f"{label} is required")
        return value

    def _req_float(self, selector: str, label: str) -> float:
        value = self.query_one(selector, Input).value.strip()
        if not value:
            raise ValueError(f"{label} is required")
        return float(value)

    def _req_int(self, selector: str, label: str) -> int:
        value = self.query_one(selector, Input).value.strip()
        if not value:
            raise ValueError(f"{label} is required")
        return int(value)
    # endregion

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "single_browse":
            self.push_screen(FilePicker("."), self._set_single_file)
        elif bid == "multi_browse":
            self.push_screen(FilePicker("."), self._set_multi_file)
        elif bid == "single_generate":
            self._do_single_generate()
        elif bid == "multi_generate":
            self._do_multi_generate()

    def _set_single_file(self, path: str | None) -> None:
        if path:
            self.query_one("#single_file", Input).value = path

    def _set_multi_file(self, path: str | None) -> None:
        if path:
            self.query_one("#multi_file", Input).value = path

    def _do_single_generate(self) -> None:
        status = self.query_one("#single_status", Static)
        try:
            name = self._req_str("#single_name", "Animation name")
            fps = self._req_float("#single_fps", "FPS")
            ticks = self._req_float("#single_ticks", "Usable ticks")
            loop = 1 if self.query_one("#single_loop", Switch).value else 0
            row_number = self._req_int("#single_row", "Row number")
            num_frames = self._req_int("#single_frames", "Number of frames")
            height = self._req_int("#single_height", "Sprite height")
            width = self._req_int("#single_width", "Sprite width")
            file_name = self.query_one("#single_file", Input).value
            if not file_name:
                raise ValueError("Choose an output file first (Browse...)")

            value_time = get_values(row_number, num_frames, height, width, fps)
            warning = write_library(
                file_name, [name],
                generate_animation(name, fps, ticks, loop, num_frames, value_time),
            )
            if warning:
                status.update(f"[bold yellow]Wrote animation '{name}' to {file_name}\n{warning}[/]")
            else:
                status.update(f"[bold green]Wrote animation '{name}' to {file_name}[/]")
        except Exception as e:
            status.update(f"[bold red]Error: {e}[/]")

    def _do_multi_generate(self) -> None:
        status = self.query_one("#multi_status", Static)
        try:
            order = [
                self.query_one(f"#multi_order_{i}", Select).value for i in range(1, 5)
            ]
            if len(set(order)) != 4:
                raise ValueError("Each direction (Up/Down/Left/Right) must be used exactly once")

            anim_type = self._req_str("#multi_type", "Type")
            fps = self._req_float("#multi_fps", "FPS")
            ticks = self._req_float("#multi_ticks", "Usable ticks")
            loop = 1 if self.query_one("#multi_loop", Switch).value else 0
            row_number = self._req_int("#multi_row", "Row number start")
            num_frames = self._req_int("#multi_frames", "Number of frames")
            height = self._req_int("#multi_height", "Sprite height")
            width = self._req_int("#multi_width", "Sprite width")
            file_name = self.query_one("#multi_file", Input).value
            if not file_name:
                raise ValueError("Choose an output file first (Browse...)")

            result = ""
            names = []
            row = row_number
            for direction in order:
                value_time = get_values(row, num_frames, height, width, fps)
                result += generate_animation(f"{anim_type}_{direction.lower()}", fps, ticks, loop, num_frames, value_time)
                names.append(f"{anim_type}_{direction.lower()}")
                row += 1

            warning = write_library(file_name, names, result)
            if warning:
                status.update(f"[bold yellow]Wrote animations {', '.join(names)} to {file_name}\n{warning}[/]")
            else:
                status.update(f"[bold green]Wrote animations {', '.join(names)} to {file_name}[/]")
        except Exception as e:
            status.update(f"[bold red]Error: {e}[/]")


if __name__ == "__main__":
    AnimatorApp().run()
