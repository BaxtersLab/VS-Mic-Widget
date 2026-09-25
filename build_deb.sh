#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# baxters-vs-mic-widget — build the .deb from this tree.
#
# Installs to /opt/baxters/vs-mic-widget, and that name is NOT free: the SOC
# Master Widget's packaged registry resolves this app as "../vs-mic-widget".
# Renaming the directory silently removes a button from the cluster launcher.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
HERE="$PWD"

. "$HOME/workspace/baxters-repo/packaging/bxdeb.sh"

PKG=baxters-vs-mic-widget
APPDIR=vs-mic-widget
CONTROL="$HERE/packaging/DEBIAN/control"

VERSION="$(bx_control_version "$CONTROL")"
bx_assert_control "$CONTROL"

STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
DEST="$STAGE/opt/baxters/$APPDIR"
mkdir -p "$DEST"

cp -a packaging/DEBIAN "$STAGE/DEBIAN"
cp -a packaging/usr/. "$STAGE/usr/"

bx_install_required "$HERE/run.sh"        "$DEST/run.sh" 0755
bx_install_required "$HERE/stt_widget.py" "$DEST/stt_widget.py"
for item in LICENSE README.md; do
    bx_install_required "$HERE/$item" "$DEST/$item"
done

# Editor history is not product. This tree carries a .bak of the pre-refactor
# widget; shipping it would put a second, older copy of the app on disk.
find "$DEST" -name '*.bak' -delete
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
n=$( { find "$DEST" -name '*.bak' -print 2>/dev/null || true; } | wc -l )
[ "$n" -eq 0 ] || { echo "FATAL: .bak files reached the payload" >&2; exit 1; }

bx_write_mit_copyright "$STAGE/usr/share/doc/$PKG/copyright" "VS Mic Widget"
bx_normalise_modes "$STAGE"
chmod 0755 "$DEST/run.sh"
bx_assert_not_group_writable "$STAGE"
bx_assert_copyright "$STAGE" "$PKG"
bx_assert_desktop "$STAGE" "$STAGE/usr/share/applications/$PKG.desktop"

# The payload must import without a display, which is only true while the pure
# helpers stay at module level. If window construction moves to import time
# this fails here rather than on a user's machine.
( cd "$DEST" && python3 -B -c '
import importlib.util, sys
spec = importlib.util.spec_from_file_location("m", "stt_widget.py")
m = importlib.util.module_from_spec(spec); sys.modules["m"] = m
spec.loader.exec_module(m)
assert m.clean_whisper_output("<|en|>ok") == "ok"
print("  payload imports and its helpers behave")
' ) || { echo "FATAL: the staged payload does not import cleanly" >&2; exit 1; }

# The cluster contract: SOC Master Widget resolves this as ../vs-mic-widget.
[ -d "$STAGE/opt/baxters/vs-mic-widget" ] || {
    echo "FATAL: install dir is not vs-mic-widget -- breaks the SOC cluster registry" >&2; exit 1; }

find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
OUT="$HERE/dist/${PKG}_${VERSION}_all.deb"
bx_build_deb "$STAGE" "$OUT"
echo "built $OUT ($(du -h "$OUT" | cut -f1))"
