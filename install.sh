#!/bin/bash
# install.sh — VS Mic Widget setup for Ubuntu/Debian Linux
# Installs all dependencies and builds whisper.cpp

set -e

echo "=== VS Mic Widget Installer ==="
echo ""

# ── System dependencies ───────────────────────────────────────────────────────
echo "[1/4] Installing system packages..."
sudo apt install -y \
    ffmpeg \
    xdotool \
    xclip \
    cmake \
    build-essential \
    python3-tk

# ── Build whisper.cpp ─────────────────────────────────────────────────────────
echo "[2/4] Cloning and building whisper.cpp..."
if [ ! -d "$HOME/whisper.cpp" ]; then
    git clone https://github.com/ggerganov/whisper.cpp.git --depth=1 "$HOME/whisper.cpp"
fi

cd "$HOME/whisper.cpp"
cmake -B build -DGGML_AVX2=OFF -DGGML_FMA=OFF
cmake --build build --config Release -j$(nproc)

# ── Download model ────────────────────────────────────────────────────────────
echo "[3/4] Downloading base.en Whisper model (~142MB)..."
if [ ! -f "$HOME/whisper.cpp/models/ggml-base.en.bin" ]; then
    bash models/download-ggml-model.sh base.en
else
    echo "  Model already present, skipping."
fi

# ── Install widget ────────────────────────────────────────────────────────────
echo "[4/4] Installing widget..."
WIDGET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# CLI script
mkdir -p "$HOME/bin"
cp "$WIDGET_DIR/stt.sh" "$HOME/bin/stt.sh"
chmod +x "$HOME/bin/stt.sh"

# Desktop launcher
chmod +x "$WIDGET_DIR/stt_widget.sh"
cp "$WIDGET_DIR/VS Mic Widget.desktop" "$HOME/Desktop/VS Mic Widget.desktop"
chmod +x "$HOME/Desktop/VS Mic Widget.desktop"

# VS Code user tasks (non-destructive — only adds if tasks.json is empty/missing)
TASKS_FILE="$HOME/.config/Code/User/tasks.json"
if [ ! -f "$TASKS_FILE" ] || [ ! -s "$TASKS_FILE" ]; then
    mkdir -p "$(dirname "$TASKS_FILE")"
    cp "$WIDGET_DIR/vscode-tasks.json" "$TASKS_FILE"
    echo "  VS Code task installed (Ctrl+Shift+R to record)."
else
    echo "  Skipped VS Code tasks.json — file already exists."
    echo "  Manually add the task from vscode-tasks.json if needed."
fi

echo ""
echo "=== Install complete! ==="
echo ""
echo "  Launch widget : double-click 'VS Mic Widget' on your Desktop"
echo "                  or run: python3 \"$WIDGET_DIR/stt_widget.py\""
echo "  CLI shortcut  : ~/bin/stt.sh [seconds]"
echo "  VS Code hotkey: Ctrl+Shift+R"
echo ""
echo "  NOTE: The -DGGML_AVX2=OFF flag makes this compatible with older"
echo "  CPUs (pre-2013, no AVX2). Remove that flag for newer hardware."
