#!/usr/bin/env bash
# Installs Godot Anim Generator for the current user: binary, icon, and
# desktop launcher, all in standard XDG locations. No sudo required.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_SRC="$SCRIPT_DIR/godot-anim-generator"
ICON_SRC="$SCRIPT_DIR/icon_256.png"

BIN_DEST_DIR="$HOME/.local/bin"
ICON_DEST_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
DESKTOP_DEST_DIR="$HOME/.local/share/applications"

if [ ! -f "$BIN_SRC" ]; then
    echo "Error: expected binary at $BIN_SRC (build it first with: pyinstaller godot-anim-generator.spec)" >&2
    exit 1
fi

mkdir -p "$BIN_DEST_DIR" "$ICON_DEST_DIR" "$DESKTOP_DEST_DIR"

cp "$BIN_SRC" "$BIN_DEST_DIR/godot-anim-generator"
chmod +x "$BIN_DEST_DIR/godot-anim-generator"

cp "$ICON_SRC" "$ICON_DEST_DIR/godot-anim-generator.png"

cat > "$DESKTOP_DEST_DIR/godot-anim-generator.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Godot Anim Generator
Exec=$BIN_DEST_DIR/godot-anim-generator
Icon=godot-anim-generator
Terminal=true
Categories=Development;
EOF

chmod +x "$DESKTOP_DEST_DIR/godot-anim-generator.desktop"

command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$DESKTOP_DEST_DIR" >/dev/null 2>&1 || true

echo "Installed. Binary: $BIN_DEST_DIR/godot-anim-generator"
echo "It should now appear in your app launcher as 'Godot Anim Generator'."
echo "If \$HOME/.local/bin isn't on your PATH, add it in your shell rc file."
