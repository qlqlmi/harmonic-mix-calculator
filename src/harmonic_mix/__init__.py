"""
harmonic_mix
============
Determines whether two tracks can be harmonically mixed once you account for
the pitch shift caused by matching their BPMs on a true vari-speed turntable
(e.g. Technics SL-1200), where speed and pitch are coupled (no keylock).

Core idea:
    speed_ratio      = target_bpm / original_bpm
    semitone_shift   = 12 * log2(speed_ratio)      <- continuous, not quantized
    new_key          = original_key transposed by semitone_shift (rounded)
    key_drift_cents  = how far off-grid the true pitch lands (for realism)

Then checks Camelot-wheel compatibility between the two *resulting* keys.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

__version__ = "0.1.0"

__all__ = [
    "Key",
    "Track",
    "MixResult",
    "key_from_camelot",
    "camelot_compatible",
    "pitch_percent_needed",
    "semitone_shift",
    "pitch_track_to_bpm",
    "check_harmonic_mix",
]

# ---------------------------------------------------------------------------
# Key <-> Camelot <-> pitch-class mapping
# ---------------------------------------------------------------------------

NOTE_TO_PC = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

PC_TO_NOTE_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

CAMELOT_MAJOR = {  # pitch class of tonic -> camelot number (letter B)
    0: 8, 7: 9, 2: 10, 9: 11, 4: 12, 11: 1, 6: 2, 1: 3, 8: 4, 3: 5, 10: 6, 5: 7
}
CAMELOT_MINOR = {  # pitch class of tonic -> camelot number (letter A)
    9: 8, 4: 9, 11: 10, 6: 11, 1: 12, 8: 1, 3: 2, 10: 3, 5: 4, 0: 5, 7: 6, 2: 7
}
# inverse lookups: (number, letter) -> tonic pitch class
_MAJOR_INV = {v: k for k, v in CAMELOT_MAJOR.items()}
_MINOR_INV = {v: k for k, v in CAMELOT_MINOR.items()}


def _parse_camelot_code(code: str) -> Tuple[int, str]:
    normalized = code.strip().upper()
    if (
        len(normalized) < 2
        or normalized[-1] not in ("A", "B")
        or not normalized[:-1].isdigit()
    ):
        raise ValueError("Camelot code must be a number from 1 to 12 followed by A or B")

    number = int(normalized[:-1])
    if not 1 <= number <= 12:
        raise ValueError("Camelot number must be between 1 and 12")
    return number, normalized[-1]


def _validate_bpm(value: float, name: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")


@dataclass
class Key:
    tonic: str      # e.g. "A", "Bb", "F#"
    mode: str       # "major" or "minor"

    def __post_init__(self):
        if self.tonic not in NOTE_TO_PC:
            raise ValueError(f"Unknown note name: {self.tonic!r}")
        if self.mode not in ("major", "minor"):
            raise ValueError("mode must be 'major' or 'minor'")

    def pitch_class(self) -> int:
        return NOTE_TO_PC[self.tonic]

    def camelot(self) -> str:
        pc = self.pitch_class()
        if self.mode == "major":
            return f"{CAMELOT_MAJOR[pc]}B"
        return f"{CAMELOT_MINOR[pc]}A"

    def transpose(self, semitones: float) -> Tuple["Key", float]:
        """
        Transpose by (possibly fractional) semitones.
        Returns (nearest-key Key object, drift_in_cents from that nearest key).
        """
        pc_float = (self.pitch_class() + semitones) % 12
        nearest_pc = round(pc_float) % 12
        drift_cents = (pc_float - round(pc_float)) * 100  # +/- up to 50 cents

        new_tonic = PC_TO_NOTE_SHARP[nearest_pc]
        return Key(new_tonic, self.mode), drift_cents

    def __str__(self):
        return f"{self.tonic} {self.mode} ({self.camelot()})"


def key_from_camelot(code: str) -> Key:
    """e.g. '8A' -> Key('A', 'minor'), '5B' -> Key('C', 'major')"""
    number, letter = _parse_camelot_code(code)
    if letter == "B":
        pc = _MAJOR_INV[number]
        return Key(PC_TO_NOTE_SHARP[pc], "major")
    pc = _MINOR_INV[number]
    return Key(PC_TO_NOTE_SHARP[pc], "minor")


# ---------------------------------------------------------------------------
# Camelot-wheel compatibility
# ---------------------------------------------------------------------------

def camelot_compatible(code_a: str, code_b: str) -> Tuple[bool, str]:
    num_a, let_a = _parse_camelot_code(code_a)
    num_b, let_b = _parse_camelot_code(code_b)

    if (num_a, let_a) == (num_b, let_b):
        return True, "identical key"

    if let_a == let_b and (num_a % 12) + 1 == num_b:
        return True, "adjacent (+1) on wheel, same mode"
    if let_a == let_b and (num_b % 12) + 1 == num_a:
        return True, "adjacent (-1) on wheel, same mode"
    if num_a == num_b and let_a != let_b:
        return True, "relative major/minor"

    return False, "not harmonically compatible"


# ---------------------------------------------------------------------------
# Turntable pitch-shift model
# ---------------------------------------------------------------------------

def pitch_percent_needed(original_bpm: float, target_bpm: float) -> float:
    _validate_bpm(original_bpm, "original BPM")
    _validate_bpm(target_bpm, "target BPM")
    return (target_bpm / original_bpm - 1.0) * 100.0


def semitone_shift(original_bpm: float, target_bpm: float) -> float:
    _validate_bpm(original_bpm, "original BPM")
    _validate_bpm(target_bpm, "target BPM")
    return 12.0 * math.log2(target_bpm / original_bpm)


@dataclass
class Track:
    name: str
    bpm: float
    key: Key

    def __post_init__(self):
        _validate_bpm(self.bpm, "track BPM")


@dataclass
class MixResult:
    pitch_percent: float
    within_deck_range: bool
    semitone_shift: float
    resulting_key: Key
    drift_cents: float


def pitch_track_to_bpm(track: Track, target_bpm: float, pitch_range_pct: float = 8.0) -> MixResult:
    if not math.isfinite(pitch_range_pct) or pitch_range_pct < 0:
        raise ValueError("pitch range must be a finite non-negative number")
    pct = pitch_percent_needed(track.bpm, target_bpm)
    shift = semitone_shift(track.bpm, target_bpm)
    new_key, drift = track.key.transpose(shift)
    return MixResult(
        pitch_percent=pct,
        within_deck_range=abs(pct) <= pitch_range_pct,
        semitone_shift=shift,
        resulting_key=new_key,
        drift_cents=drift,
    )


def check_harmonic_mix(
    track_a: Track,
    track_b: Track,
    target_bpm: Optional[float] = None,
    pitch_range_pct: float = 8.0,
) -> Dict[str, Any]:
    """
    If target_bpm is None, matches B's tempo to A (A stays at native pitch).
    Pass target_bpm explicitly to pitch both tracks to a common tempo.
    """
    if target_bpm is None:
        target_bpm = track_a.bpm

    result_a = pitch_track_to_bpm(track_a, target_bpm, pitch_range_pct)
    result_b = pitch_track_to_bpm(track_b, target_bpm, pitch_range_pct)

    compatible, reason = camelot_compatible(
        result_a.resulting_key.camelot(), result_b.resulting_key.camelot()
    )

    return {
        "target_bpm": target_bpm,
        "track_a": {
            "name": track_a.name,
            "original": f"{track_a.bpm} BPM, {track_a.key}",
            "pitch_needed_%": round(result_a.pitch_percent, 2),
            "within_deck_range": result_a.within_deck_range,
            "semitone_shift": round(result_a.semitone_shift, 3),
            "resulting_key": str(result_a.resulting_key),
            "drift_cents": round(result_a.drift_cents, 1),
        },
        "track_b": {
            "name": track_b.name,
            "original": f"{track_b.bpm} BPM, {track_b.key}",
            "pitch_needed_%": round(result_b.pitch_percent, 2),
            "within_deck_range": result_b.within_deck_range,
            "semitone_shift": round(result_b.semitone_shift, 3),
            "resulting_key": str(result_b.resulting_key),
            "drift_cents": round(result_b.drift_cents, 1),
        },
        "harmonically_compatible": compatible,
        "reason": reason,
    }
