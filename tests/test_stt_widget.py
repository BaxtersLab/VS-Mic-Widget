"""Tests for VS Mic Widget.

This tree had NO tests of any kind — it was the last gate exemption in the
estate, recorded as "a real gap, not a decision". The widget is one 409-line
Tkinter class, so the logic worth testing was first lifted out of the methods it
was tangled in; those helpers are unchanged, and the methods now call them.

Nothing here needs a display, a microphone, whisper.cpp or xdotool. What cannot
be tested without hardware is stated plainly at the bottom rather than faked.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "stt_widget.py"


@pytest.fixture(scope="module")
def w():
    """Import the app module WITHOUT constructing any Tk object.

    This works only because the helpers live at module level, above the class.
    If someone later moves window construction to import time, this fixture
    fails loudly rather than the suite quietly needing a display.
    """
    spec = importlib.util.spec_from_file_location("stt_widget_under_test", APP)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["stt_widget_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- clean_whisper_output ---------------------------------------------------

def test_plain_transcript_passes_through(w):
    assert w.clean_whisper_output("Hello there.") == "Hello there."


def test_blank_lines_are_dropped(w):
    assert w.clean_whisper_output("\n\nHello\n\n  \nworld\n") == "Hello world"


def test_special_tokens_are_stripped(w):
    """--print-special 0 does not always suppress these, so the regex is the
    thing that actually removes them."""
    out = w.clean_whisper_output("<|en|>Hello<|endoftext|>")
    assert out == "Hello"
    assert "<|" not in out


def test_multiple_special_tokens_in_one_line(w):
    assert w.clean_whisper_output("<|a|>one<|b|>two<|c|>") == "onetwo"


def test_bracket_lines_are_dropped(w):
    """whisper-cli writes progress and timestamp lines starting with '['."""
    raw = "[00:00.000 --> 00:02.000]  ignored\nkept text\n"
    assert w.clean_whisper_output(raw) == "kept text"


def test_lines_are_joined_with_single_spaces(w):
    assert w.clean_whisper_output("  one  \n  two  \n three ") == "one two three"


def test_empty_input_gives_empty_string(w):
    assert w.clean_whisper_output("") == ""


def test_only_noise_gives_empty_string(w):
    """An empty result must be distinguishable from a transcript: the caller
    shows an error when the transcript is falsy."""
    assert w.clean_whisper_output("[progress]\n\n<|endoftext|>\n") == ""


def test_a_line_that_becomes_empty_after_stripping_is_not_joined_as_a_gap(w):
    """A line consisting only of special tokens must vanish entirely, not leave
    a double space in the middle of the transcript."""
    assert w.clean_whisper_output("one\n<|endoftext|>\ntwo") == "one two"


def test_transcript_starting_with_a_bracket_is_dropped(w):
    """KNOWN LIMITATION, pinned deliberately rather than called correct.

    The '[' filter cannot tell a whisper progress line from speech that really
    begins with a bracket, so dictating "[laughs] hello" loses the first line.
    With --no-timestamps this is rare, and widening the filter risks keeping
    genuine progress output in the transcript. If this is ever changed, this
    test should fail and be updated on purpose."""
    assert w.clean_whisper_output("[laughs] hello") == ""


# --- is_own_widget_window ---------------------------------------------------

def test_the_widgets_own_window_is_recognised(w):
    assert w.is_own_widget_window("STT") is True
    assert w.is_own_widget_window("STT Widget") is True


def test_an_editor_showing_a_similarly_named_file_is_still_a_valid_target(w):
    """The length half of the heuristic is what makes this work: an editor
    title contains STT but is long, so it stays a legitimate paste target.
    Without it, dictating into a file called stt_widget.py would refuse."""
    assert w.is_own_widget_window("stt_widget.py - VS Code") is False


def test_an_unrelated_window_is_not_the_widget(w):
    assert w.is_own_widget_window("Firefox") is False
    assert w.is_own_widget_window("") is False


def test_the_match_is_case_sensitive(w):
    """Documents actual behaviour: lowercase 'stt' does not match."""
    assert w.is_own_widget_window("stt") is False


def test_the_length_boundary_is_exactly_fifteen(w):
    fourteen = "STT" + "x" * 11
    fifteen = "STT" + "x" * 12
    assert len(fourteen) == 14 and len(fifteen) == 15
    assert w.is_own_widget_window(fourteen) is True
    assert w.is_own_widget_window(fifteen) is False


# --- shorten_window_name ----------------------------------------------------

def test_short_names_are_unchanged(w):
    assert w.shorten_window_name("Firefox") == "Firefox"


def test_long_names_are_truncated_with_an_ellipsis(w):
    name = "x" * 50
    out = w.shorten_window_name(name)
    assert out.endswith("…")
    assert len(out) == 39          # 38 characters plus the ellipsis
    assert out[:38] == "x" * 38


def test_a_name_exactly_at_the_limit_is_not_truncated(w):
    name = "x" * 38
    assert w.shorten_window_name(name) == name
    assert "…" not in w.shorten_window_name(name)


def test_one_over_the_limit_is_truncated(w):
    assert w.shorten_window_name("x" * 39).endswith("…")


def test_the_limit_is_adjustable(w):
    assert w.shorten_window_name("abcdef", limit=3) == "abc…"


# --- packaging-relevant invariants ------------------------------------------

def test_the_module_imports_without_creating_a_window(w):
    """If window construction moves to import time, this whole suite would need
    a display — and on a headless gate that is a silent skip, not a failure."""
    assert hasattr(w, "STTWidget")
    assert hasattr(w, "clean_whisper_output")


def test_external_tool_paths_are_module_constants(w):
    """whisper-cli and the model are looked up under the user's home. They are
    constants so a package can override them; pinning that here means a change
    to the layout is a deliberate edit, not a surprise at runtime."""
    assert w.WHISPER_CLI.endswith("whisper-cli")
    assert w.MODEL.endswith(".bin")
    assert not w.WHISPER_CLI.startswith("~"), "path must be expanded, not literal ~"


# --- what is NOT covered here, stated rather than skipped silently ----------
#
# Recording (arecord), transcription (whisper.cpp) and pasting (xdotool type)
# all shell out to external programs and need a microphone, a model file and a
# focused X11 window. None of that is simulated here, because a mock of the
# three would only assert that the mock was called. Those paths remain
# operator-verified on real hardware. What this suite does cover is every piece
# of logic that decides WHAT gets typed and WHERE.
