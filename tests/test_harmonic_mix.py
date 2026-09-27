import math

import pytest

from harmonic_mix import (
    Key,
    Track,
    camelot_compatible,
    check_harmonic_mix,
    key_from_camelot,
    pitch_percent_needed,
    semitone_shift,
)


def test_key_camelot_roundtrip():
    for code in ["1A", "8A", "12A", "1B", "8B", "12B"]:
        key = key_from_camelot(code)
        assert key.camelot() == code


def test_known_camelot_values():
    assert Key("C", "major").camelot() == "8B"
    assert Key("A", "minor").camelot() == "8A"
    assert Key("G", "major").camelot() == "9B"
    assert Key("E", "minor").camelot() == "9A"


def test_pitch_percent_needed():
    assert pitch_percent_needed(120, 120) == 0
    assert pitch_percent_needed(120, 126) == pytest.approx(5.0)
    assert pitch_percent_needed(126, 120) == pytest.approx(-4.7619, rel=1e-3)


def test_semitone_shift_zero_when_same_bpm():
    assert semitone_shift(128, 128) == 0


def test_semitone_shift_matches_formula():
    shift = semitone_shift(120, 127.14)  # roughly +1 semitone (2^(1/12) ratio)
    assert shift == pytest.approx(12 * math.log2(127.14 / 120))


def test_transpose_no_shift_keeps_key():
    key = Key("A", "minor")
    new_key, drift = key.transpose(0)
    assert new_key.tonic == "A"
    assert drift == 0


def test_transpose_whole_semitone_up():
    key = Key("C", "major")
    new_key, drift = key.transpose(1.0)
    assert new_key.tonic == "C#"
    assert drift == pytest.approx(0)


def test_transpose_wraps_around_octave():
    key = Key("B", "major")
    new_key, drift = key.transpose(1.0)
    assert new_key.tonic == "C"


def test_camelot_compatible_identical():
    ok, _ = camelot_compatible("8A", "8A")
    assert ok


def test_camelot_compatible_relative_major_minor():
    ok, reason = camelot_compatible("8A", "8B")
    assert ok
    assert "relative" in reason


def test_camelot_compatible_adjacent_number():
    ok, _ = camelot_compatible("8A", "9A")
    assert ok
    ok, _ = camelot_compatible("9A", "8A")
    assert ok


def test_camelot_compatible_wraps_at_12_to_1():
    ok, _ = camelot_compatible("12A", "1A")
    assert ok


def test_camelot_incompatible():
    ok, reason = camelot_compatible("8A", "3B")
    assert not ok


def test_check_harmonic_mix_same_bpm_same_key():
    a = Track("A", 126, Key("A", "minor"))
    b = Track("B", 126, Key("A", "minor"))
    result = check_harmonic_mix(a, b)
    assert result["harmonically_compatible"] is True
    assert result["track_a"]["pitch_needed_%"] == 0
    assert result["track_b"]["pitch_needed_%"] == 0


def test_check_harmonic_mix_default_target_matches_track_a():
    a = Track("A", 126, Key("A", "minor"))
    b = Track("B", 132, Key("C", "major"))
    result = check_harmonic_mix(a, b)
    assert result["target_bpm"] == 126


def test_check_harmonic_mix_explicit_target_bpm():
    a = Track("A", 120, Key("A", "minor"))
    b = Track("B", 124, Key("A", "minor"))
    result = check_harmonic_mix(a, b, target_bpm=122)
    assert result["target_bpm"] == 122
    assert result["track_a"]["pitch_needed_%"] == pytest.approx(1.667, rel=1e-2)
    assert result["track_b"]["pitch_needed_%"] == pytest.approx(-1.613, rel=1e-2)


def test_pitch_range_flagging():
    # A large BPM gap should exceed an 8% stock pitch fader
    a = Track("A", 100, Key("A", "minor"))
    b = Track("B", 140, Key("A", "minor"))
    result = check_harmonic_mix(a, b, pitch_range_pct=8.0)
    assert result["track_b"]["within_deck_range"] is False
