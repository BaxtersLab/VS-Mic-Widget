# VS Mic Widget

A floating always-on-top speech-to-text widget for Linux, built for use alongside VS Code.  
Runs **100% offline** — no cloud, no API keys, no subscriptions.

Powered by [whisper.cpp](https://github.com/ggerganov/whisper.cpp) and FFmpeg.

---

## Why this exists

The official **VS Code Speech** extension (`ms-vscode.vscode-speech`) uses Microsoft's Cognitive Services Speech SDK, which requires AVX2 CPU instructions. Any machine with a pre-2013 Intel CPU (Ivy Bridge or older, e.g. i5-3320M) will crash the VS Code extension host with exit code 132 (SIGILL — illegal instruction) every time the mic button is clicked. There is no workaround for this within the official extension.

This widget solves that problem by using `whisper.cpp` compiled without AVX2, and `ffmpeg` for audio capture — bypassing VS Code's audio stack entirely.

---

## Features

- Floating, always-on-top window — stays visible over VS Code
- Drag anywhere on screen
- Adjustable recording timeout (5–120s) via spinner
- Live countdown progress bar
- **Auto-copy** — transcript lands on clipboard automatically
- **Auto-paste** — focuses your target window (e.g. VS Code chat) and fires Ctrl+V
- Set paste target by clicking a button while your target window is focused
- Transcript history window with manual Copy all / Clear
- CLI script (`stt.sh`) for terminal use
- VS Code task + keybinding (`Ctrl+Shift+R`) for in-editor recording

---

## Requirements

- Ubuntu / Debian Linux (tested on Ubuntu 24.04)
- Python 3.8+ with tkinter
- `ffmpeg`, `xdotool`, `xclip`
- `cmake`, `build-essential` (for compiling whisper.cpp)
- Internet connection for initial install only (to clone whisper.cpp and download model)

---

## Install

```bash
git clone https://github.com/YOUR_USERNAME/VS-Mic-Widget.git
cd VS-Mic-Widget
chmod +x install.sh
./install.sh
```

The installer:
1. Installs system packages (`ffmpeg`, `xdotool`, `xclip`, `cmake`, `build-essential`, `python3-tk`)
2. Clones and compiles `whisper.cpp` with AVX2 disabled (compatible with older CPUs)
3. Downloads the `base.en` Whisper model (~142MB)
4. Copies `stt.sh` to `~/bin/`
5. Copies the desktop launcher to `~/Desktop/`
6. Installs a VS Code task (if no existing `tasks.json`)

> **Newer CPU?** If your CPU supports AVX2 (2013+), remove `-DGGML_AVX2=OFF -DGGML_FMA=OFF` from `install.sh` for better performance.

---

## Usage

### Floating Widget
Double-click `VS Mic Widget` on your Desktop, or:
```bash
python3 stt_widget.py
```

**Auto-paste setup:**
1. Click into the window you want to paste into (e.g. VS Code chat input)
2. Click **"Set paste target = focused window"** in the widget
3. Enable the **Auto-paste** checkbox
4. Click START, speak, click STOP — text pastes into your target window automatically

### CLI
```bash
~/bin/stt.sh 30    # record up to 30 seconds, Ctrl+C to stop early
```

### VS Code Task
Press `Ctrl+Shift+R` inside VS Code to record and transcribe. Output appears in the task panel and is copied to clipboard.

---

## Files

| File | Purpose |
|---|---|
| `stt_widget.py` | Main floating GUI widget |
| `stt_widget.sh` | Shell launcher |
| `stt.sh` | CLI record + transcribe script |
| `install.sh` | Automated installer |
| `vscode-tasks.json` | VS Code task definition (copy to `~/.config/Code/User/tasks.json`) |
| `VS Mic Widget.desktop` | Desktop launcher entry |

---

## License

MIT
