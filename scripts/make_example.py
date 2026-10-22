#!/usr/bin/env python3
"""Generate a deterministic captured manifest.example.json using a sine stub engine."""

from __future__ import annotations

import json
import math
import tempfile
from array import array
from pathlib import Path
from typing import Any

from tts_batch.audio import PCM, sample_bytes, write_wav
from tts_batch.render import render

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_FILE = ROOT / "examples" / "manifest.example.json"
SCRIPT_TEXT = "Hello, world. This is a short narration."


def make_sine(duration_sec: float, rate: int = 16000, freq: float = 440.0) -> PCM:
    frames = round(duration_sec * rate)
    values: array[int] = array("h")
    for i in range(frames):
        sample = round(4000 * math.sin(2 * math.pi * freq * i / rate))
        values.append(sample)
    return PCM(rate, 1, sample_bytes(values))


class SineStubEngine:
    name = "stub"

    def synth(self, text: str, voice: str, speed: float) -> bytes:
        dur = 0.6 if "Hello" in text else 1.2
        return write_wav(make_sine(dur))


def generate_manifest() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="tts-batch-example-") as tmp:
        manifest = render(
            SCRIPT_TEXT,
            Path(tmp),
            SineStubEngine(),
            gap=0.2,
            normalization="rms",
            target_db=-20.0,
        )
    return manifest


def main() -> None:
    manifest = generate_manifest()
    content = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    EXAMPLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    EXAMPLE_FILE.write_text(content, encoding="utf-8")
    summary = (
        f"Rendered {len(manifest['sentences'])} segments ({manifest['duration']:.3f}s) to out/"
    )
    print(summary)
    print(f"Wrote example manifest to {EXAMPLE_FILE}")


if __name__ == "__main__":
    main()
