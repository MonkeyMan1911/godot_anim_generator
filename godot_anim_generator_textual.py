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


def write_library(file_name: str, animation_names: list[str], animation_text: str):
    with open(file_name, "r") as file:
        library_start_index = -1
        library_end_index = -1
        lines = file.readlines()
        for i in range(len(lines)):
            if '[sub_resource type="AnimationLibrary"' in lines[i]:
                library_start_index = i
        if library_start_index == -1:
            raise ValueError('No [sub_resource type="AnimationLibrary" ...] block found in that file')
        for i in range(library_start_index, len(lines)):
            if '}' in lines[i]:
                library_end_index = i
                break
        if library_end_index == -1:
            raise ValueError("Could not find the end of the AnimationLibrary block")

    lines.insert(library_start_index, animation_text)
    if lines[library_end_index][-2] != ',':
        lines[library_end_index] = lines[library_end_index][0:-1] + ',\n'
    for animation in animation_names:
        lines.insert(library_end_index + 1, f'&"{animation}": SubResource("Animation_{animation}"),\n')
    with open(file_name, "w") as file:
        file.writelines(lines)


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
            write_library(
                file_name, [name],
                generate_animation(name, fps, ticks, loop, num_frames, value_time),
            )
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

            write_library(file_name, names, result)
            status.update(f"[bold green]Wrote animations {', '.join(names)} to {file_name}[/]")
        except Exception as e:
            status.update(f"[bold red]Error: {e}[/]")


if __name__ == "__main__":
    AnimatorApp().run()
