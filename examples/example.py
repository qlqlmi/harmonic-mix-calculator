"""
Basic usage example for harmonic_mix.

Run with:
    python examples/example.py
"""

from harmonic_mix import Key, Track, check_harmonic_mix

track_a = Track("Deep Cut A", bpm=126.0, key=Key("A", "minor"))   # 8A
track_b = Track("Deep Cut B", bpm=132.0, key=Key("C", "major"))   # 8B

# Match B down to A's tempo, on a stock +/-8% Technics fader
result = check_harmonic_mix(track_a, track_b, target_bpm=None, pitch_range_pct=8.0)

for k, v in result.items():
    print(f"{k}: {v}")
