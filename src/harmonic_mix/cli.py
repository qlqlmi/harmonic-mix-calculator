"""
Command-line interface for harmonic_mix.

Usage:
    harmonic-mix --bpm-a 126 --key-a 8A --bpm-b 132 --key-b 8B
    harmonic-mix --bpm-a 126 --key-a 8A --bpm-b 132 --key-b 8B --target-bpm 129 --pitch-range 16
"""

import argparse
import json
import sys

from . import Key, Track, check_harmonic_mix, key_from_camelot


def parse_key(value: str) -> Key:
    """Accepts either a Camelot code ('8A') or 'Note mode' ('A minor')."""
    value = value.strip()
    if len(value) <= 3 and value[-1].upper() in ("A", "B") and value[:-1].isdigit():
        return key_from_camelot(value)
    parts = value.split()
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"Could not parse key {value!r}. Use a Camelot code like '8A' "
            f"or 'Note mode' like 'A minor'."
        )
    tonic, mode = parts
    return Key(tonic, mode.lower())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Check whether two tracks are harmonically mixable after "
        "BPM-matching them on a vari-speed (Technics-style) turntable."
    )
    parser.add_argument("--name-a", default="Track A")
    parser.add_argument("--bpm-a", type=float, required=True)
    parser.add_argument("--key-a", type=parse_key, required=True, help="e.g. '8A' or 'A minor'")

    parser.add_argument("--name-b", default="Track B")
    parser.add_argument("--bpm-b", type=float, required=True)
    parser.add_argument("--key-b", type=parse_key, required=True, help="e.g. '8B' or 'C major'")

    parser.add_argument(
        "--target-bpm",
        type=float,
        default=None,
        help="Common tempo to pitch both tracks to. Defaults to Track A's BPM.",
    )
    parser.add_argument(
        "--pitch-range",
        type=float,
        default=8.0,
        help="Turntable pitch fader range in %% (default: 8, stock Technics).",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON.")

    args = parser.parse_args(argv)

    track_a = Track(args.name_a, args.bpm_a, args.key_a)
    track_b = Track(args.name_b, args.bpm_b, args.key_b)

    result = check_harmonic_mix(
        track_a, track_b, target_bpm=args.target_bpm, pitch_range_pct=args.pitch_range
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Target BPM: {result['target_bpm']}\n")
    for key in ("track_a", "track_b"):
        t = result[key]
        print(f"{t['name']}")
        print(f"  original         : {t['original']}")
        print(f"  pitch needed     : {t['pitch_needed_%']:+.2f}%"
              f" ({'within' if t['within_deck_range'] else 'EXCEEDS'} deck range)")
        print(f"  semitone shift   : {t['semitone_shift']:+.3f}")
        print(f"  resulting key    : {t['resulting_key']}")
        print(f"  drift from key   : {t['drift_cents']:+.1f} cents")
        print()

    verdict = "COMPATIBLE" if result["harmonically_compatible"] else "NOT COMPATIBLE"
    print(f"Verdict: {verdict} — {result['reason']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
