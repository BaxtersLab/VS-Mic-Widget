#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# VS Mic Widget — Linux launcher.
#
# Replaces stt_widget.sh, which backgrounded python with `&`. That matters:
# nothing then owns the process, so a desktop launcher cannot stop it and
# signals do not reach it. This execs instead (A1 section 3.7).
#
# DISPLAY BACKEND: GDK_BACKEND is deliberately NOT set. This is Tkinter, not
# GTK; setting GDK's variable here would be cargo-cult.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

unset ELECTRON_RUN_AS_NODE

_strip_snap_list() {
    local IFS=':' out=() part
    for part in $1; do
        [[ "$part" == */snap/* ]] || out+=("$part")
    done
    local joined; printf -v joined '%s:' "${out[@]}"
    printf '%s' "${joined%:}"
}
[[ "${PATH:-}" == */snap/* ]] && PATH="$(_strip_snap_list "$PATH")" && export PATH
[[ "${XDG_DATA_DIRS:-}" == */snap/* ]] \
    && XDG_DATA_DIRS="$(_strip_snap_list "$XDG_DATA_DIRS")" && export XDG_DATA_DIRS
while IFS='=' read -r _name _value; do
    case "$_name" in
        PATH|XDG_DATA_DIRS) continue ;;
        *) [[ "$_value" == */snap/* ]] && unset "$_name" ;;
    esac
done < <(env)

if ! python3 -c 'import tkinter' 2>/dev/null; then
    echo "[vs-mic] Tkinter is not available.  sudo apt install python3-tk"
    exit 1
fi

# whisper.cpp is not packaged. Say so ONCE, clearly, rather than letting the
# user discover it as a red status line after their first recording.
WHISPER="$HOME/whisper.cpp/build/bin/whisper-cli"
if [ ! -x "$WHISPER" ]; then
    echo "[vs-mic] whisper-cli not found at $WHISPER"
    echo "[vs-mic] Recording will work; transcription will not until whisper.cpp is built."
fi

exec python3 stt_widget.py "$@"
