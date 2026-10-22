# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions release workflow triggered on `v*` tags with PyPI trusted publishing (`id-token: write`, environment `pypi`) and GitHub Release artifact attachments.
- Comprehensive PEP 621 / PyPI package metadata including classifiers, `Source` and `Changelog` URLs, `license-files`, expanded keywords, and `py.typed` package marker.
- Real-engine integration test (`tests/test_espeak_integration.py`) verifying timing invariants, WAV frame sums, and word boundary alignment when `espeak` is on PATH.
- CI wheel smoke test outside the source tree and Ubuntu `espeak-ng` system package installation and render validation.
- CLI `--dry-run` flag to inspect planned speech segments without invoking a TTS engine.
- CLI `--list-voices` option to query installed voices from `espeak-ng` / `espeak` with clear missing-binary reporting.
- Turkish narration example (`examples/script.tr.md`) and extended sentence splitting heuristics for Turkish decimal commas, abbreviations ("yy.", "vb.", "vs.", "örn.", "bkz."), and ordinal dates ("22. Ekim 2026").
- Deterministic example manifest generation script (`scripts/make_example.py`), committed sample (`examples/manifest.example.json`), and regression test.
- Community health files: Contributor Covenant 2.1 Code of Conduct (`CODE_OF_CONDUCT.md`), GitHub issue templates for bug reports and feature requests, and pull request template.

### Changed
- Refactored `render()` to perform streaming concatenation directly to `narration.wav`, keeping only the current segment in memory rather than buffering full audio.
- Enabled strict `mypy` type checking across `src/tts_batch` in project configuration and CI.
- Updated English and Turkish README documentation with manifest excerpts, console output, and Turkish voice guidance.

### Fixed
- Hardened CLI error handling to guarantee clean single-line `tts-batch: ...` error reporting without tracebacks on invalid directives, empty scripts, non-directory output destinations, non-WAV engine bytes, or mismatched sample rates.

## [0.1.0] - 2026-10-22

- Add local Piper subprocess, optional Kokoro and espeak adapters.
- Parse pause, voice, speed and emphasis markup in UTF-8 scripts.
- Split sentences with abbreviation, decimal and multilingual punctuation rules.
- Export per-segment WAV files and concatenated narration with configurable gaps.
- Normalize 16-bit PCM audio with pure Python RMS/peak gain and clipping limits.
- Export frame-based sentence timing and explicitly estimated word timing.
- Cache validated raw WAV output by synthesis settings and local asset identity.
- Add generated-audio and mocked-engine tests, bilingual documentation and CI.

[Unreleased]: https://github.com/YusufBeratZengin/tts-batch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YusufBeratZengin/tts-batch/releases/tag/v0.1.0
