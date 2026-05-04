#!/usr/bin/env python3
"""
STT Floating Widget
Always-on-top speech-to-text widget using whisper.cpp + ffmpeg.
Source: ~/Desktop/master constitution/stt_widget.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import os
import signal
import re

# ── Paths ──────────────────────────────────────────────────────────────────────
WHISPER_CLI = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
MODEL       = os.path.expanduser("~/whisper.cpp/models/ggml-base.en.bin")
TMPFILE     = "/tmp/stt_widget_recording.wav"

# ── Colours ────────────────────────────────────────────────────────────────────
BG          = "#1e1e1e"
BG2         = "#2d2d2d"
FG          = "#d4d4d4"
RED         = "#e05555"
GREEN       = "#4ec994"
ACCENT      = "#569cd6"
YELLOW      = "#dcdcaa"
ORANGE      = "#ce9178"


class STTWidget:
    def __init__(self, root):
        self.root = root
        self.recording      = False
        self.ffmpeg_proc    = None
        self.countdown_job  = None
        self.remaining      = 0
        self._drag_x        = 0
        self._drag_y        = 0
        self._target_win    = None   # X11 window ID to paste into

        self._build_window()
        self._build_ui()
        # Capture the currently focused window at startup (likely VS Code)
        self._update_target_window()

    # ── Window setup ──────────────────────────────────────────────────────────
    def _build_window(self):
        self.root.title("STT")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        w, h = 330, 375
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self.root.bind("<Button-1>",  self._drag_start)
        self.root.bind("<B1-Motion>", self._drag_move)

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Title bar ──
        title_bar = tk.Frame(self.root, bg=BG2, height=28)
        title_bar.pack(fill="x")
        title_bar.bind("<Button-1>",  self._drag_start)
        title_bar.bind("<B1-Motion>", self._drag_move)

        tk.Label(title_bar, text="  STT Widget",
                 bg=BG2, fg=FG, font=("Segoe UI", 9, "bold")
                 ).pack(side="left", pady=4)

        tk.Button(title_bar, text="X", command=self.root.destroy,
                  bg=BG2, fg=FG, relief="flat", font=("Segoe UI", 9, "bold"),
                  activebackground=RED, activeforeground="white",
                  cursor="hand2", bd=0, padx=8
                  ).pack(side="right")

        # ── Timeout row ──
        ctrl = tk.Frame(self.root, bg=BG, pady=5)
        ctrl.pack(fill="x", padx=12)

        tk.Label(ctrl, text="Timeout (s):", bg=BG, fg=FG,
                 font=("Segoe UI", 9)).pack(side="left")

        self.timeout_var = tk.IntVar(value=30)
        tk.Spinbox(ctrl, from_=5, to=120, increment=5,
                   textvariable=self.timeout_var,
                   width=5, bg=BG2, fg=YELLOW,
                   buttonbackground=BG2, relief="flat",
                   font=("Segoe UI", 10, "bold"),
                   disabledbackground=BG2
                   ).pack(side="left", padx=6)

        # ── Auto-copy + Auto-paste toggles ──
        toggles = tk.Frame(self.root, bg=BG)
        toggles.pack(fill="x", padx=12, pady=(0, 4))

        self.auto_copy_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toggles, text="Auto-copy",
                       variable=self.auto_copy_var,
                       bg=BG, fg=FG, selectcolor=BG2,
                       activebackground=BG, activeforeground=FG,
                       font=("Segoe UI", 9)
                       ).pack(side="left")

        self.auto_paste_var = tk.BooleanVar(value=False)
        tk.Checkbutton(toggles, text="Auto-paste",
                       variable=self.auto_paste_var,
                       command=self._on_autopaste_toggle,
                       bg=BG, fg=ACCENT, selectcolor=BG2,
                       activebackground=BG, activeforeground=ACCENT,
                       font=("Segoe UI", 9, "bold")
                       ).pack(side="left", padx=(10, 0))

        # ── Target window indicator ──
        self.target_lbl = tk.Label(self.root, text="Paste target: (none)",
                                   bg=BG, fg=ORANGE,
                                   font=("Segoe UI", 8, "italic"),
                                   anchor="w")
        self.target_lbl.pack(fill="x", padx=13, pady=(0, 2))

        tk.Button(self.root, text="Set paste target = focused window",
                  command=self._update_target_window,
                  bg=BG2, fg=ACCENT, relief="flat",
                  font=("Segoe UI", 8), cursor="hand2",
                  activebackground=BG2, activeforeground="white",
                  pady=2
                  ).pack(fill="x", padx=12, pady=(0, 4))

        # ── Status label ──
        self.status_var = tk.StringVar(value="Ready")
        self.status_lbl = tk.Label(self.root, textvariable=self.status_var,
                                   bg=BG, fg=GREEN,
                                   font=("Segoe UI", 9, "italic"))
        self.status_lbl.pack(pady=(0, 3))

        # ── Main button row: [CLEAR]  [START/STOP] ──
        main_btns = tk.Frame(self.root, bg=BG)
        main_btns.pack(pady=(0, 6))

        self.clear_btn = tk.Button(main_btns, text="CLEAR",
                                   command=self._clear,
                                   bg=BG2, fg=FG,
                                   font=("Segoe UI", 11, "bold"),
                                   relief="flat", cursor="hand2",
                                   activebackground=RED,
                                   activeforeground="white",
                                   padx=18, pady=7)
        self.clear_btn.pack(side="left", padx=(0, 6))

        self.mic_btn = tk.Button(main_btns, text="  START",
                                 command=self._toggle,
                                 bg=GREEN, fg="#1e1e1e",
                                 font=("Segoe UI", 11, "bold"),
                                 relief="flat", cursor="hand2",
                                 activebackground="#3aaf7a",
                                 padx=18, pady=7)
        self.mic_btn.pack(side="left")

        # ── Countdown bar ──
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=BG2,
                        background=ACCENT, thickness=5)
        self.progress = ttk.Progressbar(self.root, orient="horizontal",
                                        length=290, mode="determinate")
        self.progress.pack(pady=(0, 6))

        # ── Transcript box ──
        self.textbox = scrolledtext.ScrolledText(
            self.root, height=5, wrap="word",
            bg=BG2, fg=FG, insertbackground=FG,
            font=("Consolas", 9), relief="flat",
            borderwidth=0, padx=6, pady=6)
        self.textbox.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        self.textbox.config(state="disabled")

        # ── Copy button + GitHub link ──
        btn_row = tk.Frame(self.root, bg=BG)
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        tk.Button(btn_row, text="Copy all", command=self._copy,
                  bg=BG2, fg=FG, relief="flat", font=("Segoe UI", 9, "bold"),
                  activebackground=ACCENT, cursor="hand2", padx=12, pady=5
                  ).pack(side="left")

        tk.Button(btn_row, text="⭐ GitHub",
                  command=lambda: __import__('webbrowser').open(
                      'https://github.com/BaxtersLab2/VS-Mic-Widget'),
                  bg=BG, fg=ACCENT, relief="flat",
                  font=("Segoe UI", 8), cursor="hand2",
                  activebackground=BG, activeforeground="white",
                  bd=0, pady=5
                  ).pack(side="right")

    # ── Drag handlers ─────────────────────────────────────────────────────────
    def _drag_start(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag_move(self, event):
        self.root.geometry(f"+{event.x_root - self._drag_x}"
                           f"+{event.y_root - self._drag_y}")

    # ── Target window tracking ────────────────────────────────────────────────
    def _update_target_window(self):
        """Capture the currently focused X11 window as the paste target."""
        try:
            win_id = subprocess.check_output(
                ["xdotool", "getactivewindow"], text=True).strip()
            win_name = subprocess.check_output(
                ["xdotool", "getwindowname", win_id], text=True).strip()
            # Don't target our own widget
            if "STT" in win_name and len(win_name) < 15:
                self.target_lbl.config(
                    text="Paste target: click button from target window",
                    fg=RED)
                return
            self._target_win = win_id
            short = win_name[:38] + "…" if len(win_name) > 38 else win_name
            self.target_lbl.config(text=f"Target: {short}", fg=GREEN)
        except Exception:
            self.target_lbl.config(text="Paste target: xdotool error", fg=RED)

    def _on_autopaste_toggle(self):
        if self.auto_paste_var.get():
            # Force auto-copy on if auto-paste is on
            self.auto_copy_var.set(True)
            self._set_status("Auto-paste ON — set target window", ACCENT)
        else:
            self._set_status("Auto-paste OFF", FG)

    # ── Recording toggle ──────────────────────────────────────────────────────
    def _toggle(self):
        if self.recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self.recording = True
        self.remaining = self.timeout_var.get()
        self.progress["maximum"] = self.remaining
        self.progress["value"]   = self.remaining

        self.mic_btn.config(text="  STOP", bg=RED,
                            activebackground="#c04040")
        self._set_status(f"Recording... {self.remaining}s", RED)

        self.ffmpeg_proc = subprocess.Popen(
            ["ffmpeg", "-y", "-f", "alsa", "-i", "default",
             "-ar", "16000", "-ac", "1",
             "-t", str(self.remaining), TMPFILE],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self._tick()

    def _tick(self):
        if not self.recording:
            return
        if self.remaining > 0:
            self.progress["value"] = self.remaining
            self._set_status(f"Recording... {self.remaining}s", RED)
            self.remaining -= 1
            self.countdown_job = self.root.after(1000, self._tick)
        else:
            self._stop_recording()

    def _stop_recording(self):
        self.recording = False
        if self.countdown_job:
            self.root.after_cancel(self.countdown_job)
            self.countdown_job = None

        if self.ffmpeg_proc and self.ffmpeg_proc.poll() is None:
            self.ffmpeg_proc.send_signal(signal.SIGINT)
            try:
                self.ffmpeg_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.ffmpeg_proc.kill()
        self.ffmpeg_proc = None

        self.mic_btn.config(text="  START", bg=GREEN,
                            activebackground="#3aaf7a", state="disabled")
        self.progress["value"] = 0
        self._set_status("Transcribing...", YELLOW)

        threading.Thread(target=self._transcribe, daemon=True).start()

    # ── Transcription ─────────────────────────────────────────────────────────
    def _transcribe(self):
        if not os.path.isfile(TMPFILE) or os.path.getsize(TMPFILE) == 0:
            self._on_done("", error="No audio captured.")
            return

        try:
            result = subprocess.run(
                [WHISPER_CLI,
                 "--model",         MODEL,
                 "--file",          TMPFILE,
                 "--language",      "en",
                 "--output-txt",
                 "--no-timestamps",
                 "--print-special", "0"],
                capture_output=True, text=True, timeout=120
            )
            lines = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("["):
                    continue
                line = re.sub(r"<\|[^|]*\|>", "", line).strip()
                if line:
                    lines.append(line)
            transcript = " ".join(lines).strip()
        except Exception as e:
            self._on_done("", error=str(e))
            return
        finally:
            try:
                os.remove(TMPFILE)
            except FileNotFoundError:
                pass

        self._on_done(transcript)

    def _on_done(self, transcript, error=None):
        def _update():
            self.mic_btn.config(state="normal")
            if error or not transcript:
                self._set_status(error or "Empty result.", RED)
                return

            self._write_text(transcript + "\n")

            if self.auto_copy_var.get():
                self._copy_text(transcript)
                self._set_status("Copied to clipboard", GREEN)

            if self.auto_paste_var.get():
                self._set_status("Pasting in 1s...", ACCENT)
                self.root.after(1000, lambda: self._do_paste(transcript))
            else:
                self._set_status("Done", GREEN)

        self.root.after(0, _update)

    def _do_paste(self, transcript):
        """Activate target window and simulate Ctrl+V."""
        try:
            if not self._target_win:
                self._set_status("No paste target set.", RED)
                return
            # Refill clipboard right before paste (safety)
            self._copy_text(transcript)
            # Single xdotool call: windowactivate raises via WM, then key fires
            subprocess.run(
                ["xdotool", "windowactivate", "--sync", self._target_win,
                 "key", "--clearmodifiers", "ctrl+v"],
                check=True)
            self._set_status("Pasted!", GREEN)
        except Exception as e:
            self._set_status(f"Paste failed: {e}", RED)

    # ── Text helpers ──────────────────────────────────────────────────────────
    def _write_text(self, text):
        self.textbox.config(state="normal")
        self.textbox.insert("end", text)
        self.textbox.see("end")
        self.textbox.config(state="disabled")

    def _copy(self):
        text = self.textbox.get("1.0", "end-1c").strip()
        if text:
            self._copy_text(text)
            self._set_status("Copied!", GREEN)

    def _copy_text(self, text):
        try:
            subprocess.run(["xclip", "-selection", "clipboard"],
                           input=text.encode(), check=True)
        except Exception:
            try:
                subprocess.run(["xsel", "--clipboard", "--input"],
                               input=text.encode(), check=True)
            except Exception:
                pass

    def _clear(self):
        self.textbox.config(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.config(state="disabled")
        self._set_status("Ready", GREEN)
        self.progress["value"] = 0

    def _set_status(self, msg, colour=FG):
        self.status_var.set(msg)
        self.status_lbl.config(fg=colour)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = STTWidget(root)
    root.mainloop()
