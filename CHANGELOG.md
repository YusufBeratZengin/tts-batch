# Changelog

## 0.1.0 - 2026-10-22

- Add local Piper subprocess, optional Kokoro and espeak adapters.
- Parse pause, voice, speed and emphasis markup in UTF-8 scripts.
- Split sentences with abbreviation, decimal and multilingual punctuation rules.
- Export per-segment WAV files and concatenated narration with configurable gaps.
- Normalize 16-bit PCM audio with pure Python RMS/peak gain and clipping limits.
- Export frame-based sentence timing and explicitly estimated word timing.
- Cache validated raw WAV output by synthesis settings and local asset identity.
- Add generated-audio and mocked-engine tests, bilingual documentation and CI.
