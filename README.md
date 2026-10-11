# harmonic-mix

Check whether two tracks are harmonically mixable **after** you account for
the pitch shift caused by BPM-matching them on a true vari-speed turntable
(e.g. a Technics SL-1200), where pitch and tempo are coupled — there's no
keylock/master-tempo, so speeding a record up also raises its pitch.

## What it do

Two tracks that look compatible on paper (e.g. both 8A on the Camelot wheel)
can stop being compatible once you pitch one to match the other's tempo,
because the pitch fader shifts the *actual* key, not just the tempo. This
tool computes that shift and re-checks Camelot-wheel compatibility on the
**resulting** keys, not the original ones.

### The math

```
speed_ratio     = target_bpm / original_bpm
semitone_shift  = 12 * log2(speed_ratio)      # continuous, not quantized
new_key         = original_key transposed by semitone_shift (rounded)
drift_cents     = how far the true pitch lands from that nearest key
```

Because vari-speed pitch shift is continuous, a shift like -0.8 semitones
doesn't land cleanly on a new key — it lands mostly there, with some
leftover drift (in cents) that a trained ear can notice. The tool reports
both the rounded key (for Camelot-wheel matching) and the drift.

It also flags whether the required pitch change is within your turntable's
fader range (stock Technics decks are typically ±8%, some switchable up to
±16/±24/±50%).

### Compatibility rule (Camelot wheel)

Two resulting keys are considered harmonically compatible if they are:

- identical,
- adjacent number, same letter (e.g. `8A` ↔ `9A` or `7A`),
- same number, opposite letter — relative major/minor (e.g. `8A` ↔ `8B`).

## Install

```bash
pip install .
# or, for development with tests:
pip install -e ".[dev]"
```

## Usage

### As a library

```python
from harmonic_mix import Key, Track, check_harmonic_mix

track_a = Track("Deep Cut A", bpm=126.0, key=Key("A", "minor"))   # 8A
track_b = Track("Deep Cut B", bpm=132.0, key=Key("C", "major"))   # 8B

# Match B's tempo down to A's (A stays at native pitch)
result = check_harmonic_mix(track_a, track_b, pitch_range_pct=8.0)

print(result["harmonically_compatible"], result["reason"])
```

Keys can also be built directly from Camelot codes:

```python
from harmonic_mix import key_from_camelot

key = key_from_camelot("8A")   # -> Key(tonic='A', mode='minor')
```

Pitch both tracks to a common tempo instead of matching one to the other:

```python
result = check_harmonic_mix(track_a, track_b, target_bpm=129.0)
```

### As a CLI

```bash
harmonic-mix --bpm-a 126 --key-a 8A --bpm-b 132 --key-b 8B
```

```
Target BPM: 126.0

Track A
  original         : 126.0 BPM, A minor (8A)
  pitch needed     : +0.00% (within deck range)
  semitone shift   : +0.000
  resulting key    : A minor (8A)
  drift from key   : +0.0 cents

Track B
  original         : 132.0 BPM, C major (8B)
  pitch needed     : -4.55% (within deck range)
  semitone shift   : -0.805
  resulting key    : B major (1B)
  drift from key   : +19.5 cents

Verdict: NOT COMPATIBLE — not harmonically compatible
```

Options:

| Flag              | Description                                                        |
|-------------------|---------------------------------------------------------------------|
| `--bpm-a/-b`       | Original BPM of each track                                        |
| `--key-a/-b`       | Key as a Camelot code (`8A`) or `"Note mode"` (`"A minor"`)        |
| `--target-bpm`     | Common tempo to pitch both to (default: Track A's BPM)            |
| `--pitch-range`    | Turntable pitch fader range in % (default: `8`)                   |
| `--json`           | Output raw JSON instead of formatted text                         |

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## Limitations

- Assumes a linear vari-speed relationship between BPM and pitch, as on
  turntables and tape — this does **not** apply to modern digital
  keylock/master-tempo gear, which decouples pitch from tempo.
- Key detection isn't part of this tool — feed it keys from your own
  analysis (Camelot code or note name) rather than expecting it to
  analyze audio.
- Compatibility rules are the standard Camelot wheel; it doesn't attempt
  more advanced harmonic techniques (modal interchange, energy-boost
  mixing, etc.).

## License

MIT
