# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Dependabot configuration for automated weekly pip and GitHub Actions updates.
- CodeQL static analysis workflow for Python security scanning.
- Interactive GitHub Issue Forms (`.github/ISSUE_TEMPLATE/*.yml`) for structured bug reports and feature requests.
- Multi-platform CI matrix covering Ubuntu, Windows, and macOS on Python 3.10 and 3.14.
- Automated code coverage reporting via `pytest-cov` and edge-case branch tests.
- Terminal demo generator (`scripts/make-demo.py`) and static SVG artifact (`docs/demo.svg`).

## [0.1.0] - 2026-10-23

### Added
- Local offline narration engine supporting Piper (ONNX), espeak-ng, and optional Kokoro adapters.
- Script parsing for pauses (`[pause 500ms]`), speeds (`[speed 1.1]`), voices (`[voice ...]`), comments (`#`), and inline emphasis stripping.
- Robust multilingual sentence splitter handling abbreviations, initials, decimals, and dates in English and Turkish.
- Per-sentence WAV export alongside a unified `narration.wav` with configurable inter-segment gaps.
- Pure Python 16-bit PCM audio normalization (RMS and peak) with clipping prevention.
- JSON timing manifest (`schema_version: 1`) with integer-frame sentence timing and character-weighted word timing estimates.
- Deterministic SHA-256 synthesis caching taking into account engine parameters and local asset timestamps.
- CLI subcommands and flags: `render`, `--dry-run` inspection, and `--list-voices` discovery.
- GitHub Actions release workflow triggered on `v*` tags with PyPI trusted publishing.
- Bilingual documentation (English and Turkish) and end-to-end example scripts.

### Changed
- Refactored audio rendering to stream frames directly to disk for O(1) memory usage.
- Enforced strict `mypy` typing across all core source modules.

### Fixed
- Hardened CLI error reporting to produce single-line user errors without Python tracebacks on invalid input, missing binaries, or audio format mismatches.

[Unreleased]: https://github.com/YusufBeratZengin/tts-batch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YusufBeratZengin/tts-batch/releases/tag/v0.1.0
