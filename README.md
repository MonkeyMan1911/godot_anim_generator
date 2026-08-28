# Godot Animation Generator

A lightweight terminal-based GUI for quickly generating **Godot 4 sprite animations** directly inside existing `.tscn` scene files.

Instead of manually creating animation resources and configuring sprite-sheet regions in Godot, this tool lets you enter the animation settings, select your `.tscn` file, and generate the required animation data automatically.

The application uses [Textual](https://textual.textualize.io/) to provide a mouse-friendly terminal UI.

## Features

* Generate a **single animation** at a time
* Generate **four directional animations** at once
* Automatically creates Godot `Animation` sub-resources
* Automatically adds animations to an existing `AnimationLibrary`
* Supports sprite sheets using `Sprite2D:region_rect`
* Choose `.tscn` files using a built-in file browser
* Mouse and keyboard support
* Input validation with helpful error messages
* Linux and Windows builds available

## How It Works

The generator modifies an existing Godot `.tscn` file.

For each animation, it generates:

* An `Animation` sub-resource
* Frame timing information
* Sprite-sheet region coordinates
* Loop settings
* Animation length
* Animation FPS/step timing
* An entry in the scene's `AnimationLibrary`

The tool expects your scene to already contain an `AnimationLibrary` sub-resource.

## Requirements

### Running from Source

* Python 3.10+
* [Textual](https://textual.textualize.io/)

Install the dependency with:

```bash
pip install textual
```

Then run:

```bash
python3 godot_anim_generator_textual.py
```

On Windows:

```powershell
python godot_anim_generator_textual.py
```

## Usage

When the program starts, you'll see two tabs:

* **Single Animation**
* **Multi-Directional**

You can switch between them using the mouse or keyboard.

---

## Single Animation

The **Single Animation** tab creates one animation.

### Fields

| Field                      | Description                                                 |
| -------------------------- | ----------------------------------------------------------- |
| **Animation name**         | Name assigned to the generated animation, such as `walk_up` |
| **FPS**                    | Animation playback speed                                    |
| **Usable ticks**           | Number of timing ticks used to determine animation length   |
| **Loop**                   | Whether the animation should loop                           |
| **Row number (0-indexed)** | Sprite-sheet row containing the animation                   |
| **Number of frames**       | Number of frames in the animation                           |
| **Sprite height (px)**     | Height of each frame                                        |
| **Sprite width (px)**      | Width of each frame                                         |
| **Output file**            | Existing `.tscn` file that will be modified                 |

### Example

For a 4-frame, 32×32 walking animation on the first row of a sprite sheet:

```text
Animation name:       walk_down
FPS:                  12
Usable ticks:         4
Loop:                 On
Row number:           0
Number of frames:     4
Sprite height:        32
Sprite width:         32
```

After selecting your `.tscn` file, click:

```text
Generate Animation
```

The generated animation is inserted into the scene's `AnimationLibrary`.

---

## Multi-Directional Animations

The **Multi-Directional** tab generates four animations at once.

This is useful for characters that have separate sprite-sheet rows for:

* Up
* Down
* Left
* Right

### Direction Order

You choose which row corresponds to each direction.

For example:

```text
1st direction: Up
2nd direction: Down
3rd direction: Left
4th direction: Right
```

The tool requires all four directions to be used exactly once.

### Animation Type

The **Type** field determines the beginning of each animation name.

For example:

```text
Type: walk
```

generates:

```text
walk_up
walk_down
walk_left
walk_right
```

Another example:

```text
Type: idle
```

generates:

```text
idle_up
idle_down
idle_left
idle_right
```

### Other Settings

The remaining fields work similarly to the Single Animation mode:

| Field                  | Description                            |
| ---------------------- | -------------------------------------- |
| **Type**               | Prefix used for each animation name    |
| **FPS**                | Animation playback speed               |
| **Usable ticks**       | Timing ticks used for animation length |
| **Loop**               | Whether the animations loop            |
| **Row number start**   | First sprite-sheet row                 |
| **Number of frames**   | Frames per animation                   |
| **Sprite height (px)** | Height of each sprite                  |
| **Sprite width (px)**  | Width of each sprite                   |
| **Output file**        | Existing `.tscn` file to modify        |

The row number automatically increases by one for each direction.

For example, starting at row `0`:

```text
Up     -> Row 0
Down   -> Row 1
Left   -> Row 2
Right  -> Row 3
```

## Important: Your `.tscn` File

The generator modifies the scene file directly.

Before generating an animation, make sure the target `.tscn` contains an `AnimationLibrary` sub-resource.

For example:

```text
[sub_resource type="AnimationLibrary" id="AnimationLibrary_xxxxx"]
_data = {
}
```

The program searches for this block and inserts the generated animations into it.

### Back Up Your Scene

Because the program writes directly to the `.tscn` file, it is recommended that you:

1. Save your Godot project
2. Back up the `.tscn` file
3. Run the generator
4. Open the project in Godot and verify the generated animations

## Sprite Sheet Layout

The generator assumes your sprites are arranged in a regular grid.

For a 32×32 sprite sheet:

```text
+--------+--------+--------+--------+
| Frame 1| Frame 2| Frame 3| Frame 4|
+--------+--------+--------+--------+
| Frame 1| Frame 2| Frame 3| Frame 4|
+--------+--------+--------+--------+
| Frame 1| Frame 2| Frame 3| Frame 4|
+--------+--------+--------+--------+
| Frame 1| Frame 2| Frame 3| Frame 4|
+--------+--------+--------+--------+
```

Each frame must have the same width and height.

The program calculates the `Rect2` region for each frame automatically.

## Generated Godot Data

The program generates Godot animation resources similar to:

```text
[sub_resource type="Animation" id="Animation_walk_down"]
resource_name = "walk_down"
length = 0.3333333333333333
loop_mode = 1
step = 0.08333333
```

It also creates frame region values such as:

```text
Rect2(0, 0, 32, 32)
Rect2(32, 0, 32, 32)
Rect2(64, 0, 32, 32)
Rect2(96, 0, 32, 32)
```

These are applied to:

```text
Sprite2D:region_rect
```

## Error Handling

Errors are displayed directly inside the application.

Common errors include:

### Missing animation name

```text
Animation name is required
```

Enter a name such as:

```text
walk_down
```

### Missing output file

```text
Choose an output file first (Browse...)
```

Use the **Browse...** button to select your `.tscn` file.

### Duplicate directions

The multi-directional mode requires all four directions to be unique.

For example, this is invalid:

```text
Up
Down
Up
Right
```

The program will report:

```text
Each direction (Up/Down/Left/Right) must be used exactly once
```

### Missing AnimationLibrary

If your scene doesn't contain an `AnimationLibrary`, the generator cannot add the animations and will report an error.

## Keyboard Controls

The application supports keyboard navigation in addition to mouse input.

Press:

```text
Q
```

to quit the application.

Press:

```text
Esc
```

to close the file picker.

You can also use `Tab` to move between input fields.

## Installing the Prebuilt Version

### Linux

The Linux release includes:

```text
godot-anim-generator
icon_256.png
install-linux.sh
```

Make the installer executable:

```bash
chmod +x install-linux.sh
```

Then run:

```bash
./install-linux.sh
```

The application will be installed to:

```text
~/.local/bin/godot-anim-generator
```

and a desktop launcher will be created in:

```text
~/.local/share/applications/
```

The application should then appear in your Linux application launcher.

### Windows

The Windows release is distributed as:

```text
Godot-Anim-Generator-Setup.exe
```

Run the installer and follow the setup wizard.

The installer creates:

* A Start Menu shortcut
* A Desktop shortcut
* An uninstall entry

## Building From Source

This project uses [PyInstaller](https://pyinstaller.org/) to create standalone executables.

Install the dependencies:

```bash
pip install -r requirements.txt
```

Build the application:

```bash
pyinstaller godot-anim-generator.spec
```

The generated executable will be placed in:

```text
dist/
```

### Linux

The Linux executable is:

```text
dist/godot-anim-generator
```

### Windows

The Windows executable is:

```text
dist/godot-anim-generator.exe
```

## GitHub Actions Builds

The project includes GitHub Actions workflows for automatically building Linux and Windows releases.

Builds are triggered by version tags such as:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The version number is automatically passed to the Windows installer.

For example:

```text
v1.0.0
```

produces an installer with version:

```text
1.0.0
```

## Project Structure

```text
godot-anim-generator/
├── .github/
│   └── workflows/
│       └── build.yml
├── installer/
│   └── windows.iss
├── godot_anim_generator_textual.py
├── godot-anim-generator.spec
├── icon.ico
├── icon_256.png
├── install-linux.sh
├── requirements.txt
└── README.md
```

## License

Add your preferred license here.

For example:

```text
MIT License
```

## Contributing

Contributions and improvements are welcome.

To contribute:

```bash
git clone <repository-url>
cd godot-anim-generator
pip install -r requirements.txt
python3 godot_anim_generator_textual.py
```

Create a branch for your changes, test the generator with real Godot `.tscn` files, and submit a pull request.
