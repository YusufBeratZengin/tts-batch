# tts-batch

Turn UTF-8 text scripts into local narration, numbered sentence WAVs and a JSON
caption timeline. Python 3.10 or newer is required. The core has no runtime
dependencies outside the Python standard library.

[Türkçe](README.tr.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## Install

From a checkout:

```sh
python -m pip install -e .
```

Install an engine separately. The default `espeak` adapter uses `espeak-ng` or
`espeak` on PATH. Piper uses the `piper` executable on PATH and an existing local
`.onnx` model with its adjacent `.onnx.json` file. The package does not install
engine binaries or download models. Engine and model licenses are separate from
this project's MIT license.

```sh
tts-batch render examples/script.md -o out/ --engine espeak --voice en
tts-batch render examples/script.tr.md -o out/ --engine espeak --voice tr
tts-batch render script.md -o out/ --engine piper --voice models/en_US.onnx
```

`python -m tts_batch` is equivalent to `tts-batch`. Engines run locally; no cloud
credentials or paid API is needed. If an engine is missing, the command fails
with an actionable error. Choose `--engine espeak` explicitly to use the fallback.

## Script format

Use `.txt` or `.md`, encoded as UTF-8 (a BOM is accepted by the CLI):

```text
# This whole line is ignored
Hello, world. This is a *short* narration.
[pause 500ms]
[speed 1.1]
This section is faster.
[voice models/another.onnx]
This section uses another voice.
```

| Syntax | Meaning |
| --- | --- |
| `[pause 500ms]` | Add 500 ms of silence; decimal milliseconds are accepted |
| `[speed 1.1]` | Set the speed multiplier for following speech; default 1.0 |
| `[voice x]` | Set the voice for following speech; paths can contain spaces |
| `*emphasis*` | Remove the asterisks; emphasis is ignored by the adapters |
| A line whose first non-space character is `#` | Ignore the whole line |

Directives are case-sensitive, flush any preceding speech and take effect
immediately. A directive inside a sentence therefore creates separate audio
segments. Voice and speed persist until changed. Square brackets are reserved
for directives; unknown or malformed directives are errors. Other Markdown
syntax is not interpreted. Newlines become spaces, so punctuation determines
sentence boundaries.

The splitter handles common English/Turkish abbreviations, initials, decimal
numbers, Latin sentence punctuation and Chinese/Japanese full-width punctuation.
It also works with whitespace-delimited Cyrillic text. It is a heuristic:
ambiguous abbreviations, ordinal numbers and language-specific punctuation may
need manual boundaries such as `[pause 0ms]`.

## Output and timing

An output directory contains:

```text
out/
  0001.wav
  0002.wav
  narration.wav
  manifest.json
  .cache/
```

Numbered files contain speech only. `narration.wav` includes leading/trailing
pauses, inline pauses and the configurable gap between speech segments. Explicit
pauses and `--gap` are additive. Gaps are not added before the first or after the
last speech segment. Each silence is rounded to the nearest sample frame; timing
is accumulated using integer frames to avoid drift.

`manifest.json` has `schema_version: 1`, engine, audio filename, sample rate,
channel count, total frames/duration, gap and normalization settings. Its
`sentences` list contains each segment's `text`, relative `file`, `voice`, `speed`,
`start`, `end`, `duration`, `start_frame`, `end_frame`, `cache_key`, `cache_hit` and
`words`. Seconds are measured from the start of `narration.wav`; end times are
exclusive. Per-file local timing starts at zero, so subtract the segment's
`start` from its word timestamps when editing an individual file.

Sentence timestamps come from actual WAV frame counts. **Word timestamps are
estimates, not forced alignment.** The manifest labels them
`word_timing: "estimated_character_weight"`. Speech duration is divided among
word tokens in proportion to character count; CJK characters form individual
caption units. Word estimates include any silence inside engine output and can
need manual adjustment. Punctuation-only segments have an empty `words` list.

All audio must be uncompressed 16-bit PCM with the same sample rate and channel
count. Mixed formats produce an error; there is no resampling. Switching voices
can therefore fail if their formats differ. Engine output is validated even on
cache hits.

Renders are staged before existing numbered files, `narration.wav` and
`manifest.json` are replaced. Synthesis/format failures preserve a previous
render, although new cache entries can remain. Replacement of the entire output
directory is not transactional against filesystem errors. Older numbered files
from a longer render are left in place; use the manifest as the authoritative
file list or choose a fresh output directory. Use a dedicated output directory
and one writer at a time. The renderer streams audio frames directly to
`narration.wav`, keeping only the current segment in memory.

### Manifest example and console output

Running `tts-batch render` prints a single-line summary:

```text
Rendered 2 segments (2.000s) to out/
```

The resulting `out/manifest.json` provides sentence and word timelines:

```json
{
  "schema_version": 1,
  "engine": "stub",
  "audio": "narration.wav",
  "sample_rate": 16000,
  "channels": 1,
  "duration": 2.0,
  "frames": 32000,
  "gap_seconds": 0.2,
  "normalization": "rms",
  "target_dbfs": -20.0,
  "word_timing": "estimated_character_weight",
  "sentences": [
    {
      "text": "Hello, world.",
      "file": "0001.wav",
      "voice": "",
      "speed": 1.0,
      "start": 0.0,
      "end": 0.6,
      "start_frame": 0,
      "end_frame": 9600,
      "duration": 0.6,
      "cache_hit": false,
      "cache_key": "a362ec42341e2f77fcff42ef970afa0c3adfe7b02accbdb38310db9892b79e65",
      "words": [
        {
          "text": "Hello",
          "start": 0.0,
          "end": 0.3
        },
        {
          "text": "world",
          "start": 0.3,
          "end": 0.6
        }
      ]
    },
    {
      "text": "This is a short narration.",
      "file": "0002.wav",
      "voice": "",
      "speed": 1.0,
      "start": 0.8,
      "end": 2.0,
      "start_frame": 12800,
      "end_frame": 32000,
      "duration": 1.2,
      "cache_hit": false,
      "cache_key": "10ced23c9fd24e29c4c8ff3463649d65f8881d21f74ba4db47c70632945f40c7",
      "words": [
        {
          "text": "This",
          "start": 0.8,
          "end": 1.0285625
        },
        {
          "text": "is",
          "start": 1.0285625,
          "end": 1.142875
        },
        {
          "text": "a",
          "start": 1.142875,
          "end": 1.2
        },
        {
          "text": "short",
          "start": 1.2,
          "end": 1.4856875
        },
        {
          "text": "narration",
          "start": 1.4856875,
          "end": 2.0
        }
      ]
    }
  ]
}
```

## Options

```sh
# Inspect planned speech segments without synthesizing audio
tts-batch render examples/script.md --dry-run

# List installed voices for espeak
tts-batch --list-voices

# Standard render with custom parameters
tts-batch render script.md -o out/ --engine espeak --voice en \
  --speed 1.0 --gap 0.15 --normalize rms --target-db -20
```

`--gap` is in seconds (default 0.2). `--normalize rms` applies a constant gain to
each segment, targeting -20 dBFS by default. `--normalize peak` targets a peak
level; `--normalize none` preserves levels. Targets range from -120 to 0 dBFS.
Gain is capped to prevent clipping, so an RMS target may not be reachable.
Silence stays silent. This is simple RMS/peak normalization, not LUFS mastering.

Raw engine WAVs are cached by a SHA-256 hash of engine identity, voice, speed
and text. Local asset paths, sizes and nanosecond modification times also
invalidate entries; Kokoro includes language/model/config identity. Changing
gap or normalization reuses synthesis. Use `--cache-dir path` to share a cache or
`--no-cache` to disable it. Corrupt entries are regenerated. If you replace a
model while preserving both its size and timestamp, clear the cache manually.
Engine binary/package upgrades also require clearing the cache. Scripts,
manifests and cached audio stay on disk locally; protect them if they contain
sensitive material.

## Optional Kokoro adapter

Install the optional Python dependencies separately, using a Python version
supported by those dependencies:

```sh
python -m pip install -e ".[kokoro]"
tts-batch render script.md -o out/ --engine kokoro \
  --kokoro-model models/kokoro-v1_0.pth \
  --kokoro-config models/config.json --voice voices/af_heart.pt --lang a
```

Model, configuration and voice must be existing local files. Voice names such
as `af_heart` are not accepted. Provision language/G2P resources ahead of time;
English requires an installed `en_core_web_sm` spaCy package. The adapter sets
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` before importing Kokoro; these
remain set for the process. Missing assets produce errors rather than an online
model fallback. For strict isolation, also run in a network-disabled environment.

Supported adapter language codes are `a` (US English), `b` (UK English), `e`
(Spanish), `f` (French), `h` (Hindi), `i` (Italian), `p` (Brazilian Portuguese)
and `z` (Mandarin, v1.0 configuration). Non-English language dependencies must
be provisioned separately. Japanese is excluded because its G2P dependency can
download dictionaries implicitly. Output is mono 24 kHz. This adapter uses the
Kokoro 0.9 API; it does not install, download or validate model licenses for you.

## Python engines and development

An engine implements `name: str` and
`synth(text: str, voice: str, speed: float) -> bytes`, returning a complete WAV.
An optional `cache_identity` string can include engine-specific configuration.
Use custom engines by passing an instance to `tts_batch.render`:

```python
from pathlib import Path
from tts_batch import render
from tts_batch.engines import EspeakEngine

manifest = render("Hello. Goodbye!", Path("out"), EspeakEngine(), voice="en")
```

The core and tests use only the standard library. From the repository root:

```sh
python -m unittest discover -v
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
```

Tests mock all engines and generate sine-wave fixtures; they never need models,
network access or engine binaries. Scratch files live under ignored `is/test-tmp/`.
CI runs lint and tests on Ubuntu and Windows with Python 3.10 and 3.14. Optional
Kokoro dependency compatibility and real-model quality are not covered by CI.

Project: [YusufBeratZengin/tts-batch](https://github.com/YusufBeratZengin/tts-batch).
See [LICENSE](LICENSE) for the MIT license.
