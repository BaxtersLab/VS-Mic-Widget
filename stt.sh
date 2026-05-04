#!/bin/bash
# stt.sh — Record mic, transcribe with whisper.cpp, copy to clipboard
# Usage: stt.sh [seconds]  (default: 30 seconds, press Ctrl+C to stop early)

WHISPER_CLI="$HOME/whisper.cpp/build/bin/whisper-cli"
MODEL="$HOME/whisper.cpp/models/ggml-base.en.bin"
TMPFILE="/tmp/stt_recording.wav"
DURATION="${1:-30}"

# Notify start
echo ">>> Recording for up to ${DURATION}s — speak now. Press Ctrl+C to stop early." >&2
notify-send "STT" "Recording... (${DURATION}s max)" 2>/dev/null || true

# Record — trap Ctrl+C so early stop still processes the audio
ffmpeg -y -f alsa -i default -ar 16000 -ac 1 -t "$DURATION" "$TMPFILE" 2>/dev/null &
FFMPEG_PID=$!

trap "kill $FFMPEG_PID 2>/dev/null; wait $FFMPEG_PID 2>/dev/null" INT
wait $FFMPEG_PID
trap - INT

# Check we actually got audio
if [[ ! -f "$TMPFILE" || ! -s "$TMPFILE" ]]; then
    echo "ERROR: No audio captured." >&2
    exit 1
fi

echo ">>> Transcribing..." >&2

# Transcribe — suppress progress output, extract plain text only
TRANSCRIPT=$("$WHISPER_CLI" \
    --model "$MODEL" \
    --file "$TMPFILE" \
    --language en \
    --output-txt \
    --no-timestamps \
    --print-special 0 \
    2>/dev/null \
    | grep -v "^\[" \
    | sed 's/<|[^|]*|>//g' \
    | sed 's/^[[:space:]]*//' \
    | tr -s ' ' \
    | sed '/^$/d')

if [[ -z "$TRANSCRIPT" ]]; then
    echo "ERROR: Transcription returned empty." >&2
    exit 1
fi

# Copy to clipboard
echo "$TRANSCRIPT" | xclip -selection clipboard 2>/dev/null \
    || echo "$TRANSCRIPT" | xsel --clipboard --input 2>/dev/null

# Print to stdout (so VS Code task output panel shows it too)
echo "$TRANSCRIPT"

notify-send "STT" "Transcription copied to clipboard" 2>/dev/null || true

# Clean up
rm -f "$TMPFILE"
