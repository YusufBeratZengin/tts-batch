"""Render parsed scripts, preserving frame-based sentence timing."""

import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .audio import PCM, concatenate, normalize, read_wav, silence_frames, write_wav
from .cache import Cache, cache_key
from .engines import Engine
from .script import Pause, Speech, parse_script

# CJK characters are individual caption units; space-delimited words elsewhere.
_WORDS = re.compile(
    r"[\u3400-\u9fff\u3040-\u30ff]|"
    r"[^\W_\u3400-\u9fff\u3040-\u30ff]+(?:['’\-][^\W_\u3400-\u9fff\u3040-\u30ff]+)*",
    re.UNICODE,
)


def word_timings(text: str, start_frame: int, frames: int, rate: int) -> list[dict]:
    """Estimate word spans by character weight, without acoustic alignment."""
    words = _WORDS.findall(text)
    total = sum(len(word) for word in words)
    consumed = 0
    result = []
    for word in words:
        start = start_frame + round(frames * consumed / total)
        consumed += len(word)
        end = start_frame + round(frames * consumed / total)
        result.append({"text": word, "start": start / rate, "end": end / rate})
    return result


def render(
    script: str,
    output: Path,
    engine: Engine,
    *,
    voice: str = "",
    speed: float = 1.0,
    gap: float = 0.2,
    normalization: str = "rms",
    target_db: float = -20.0,
    cache_dir: Path | None = None,
    use_cache: bool = True,
) -> dict:
    """Write numbered WAVs, narration.wav and manifest.json; return manifest.

    Pauses and gaps are additive. Staging prevents synthesis/format failures
    from overwriting an earlier render. Memory usage scales with audio length.
    """
    if not math.isfinite(gap) or gap < 0:
        raise ValueError("Gap must be finite and nonnegative")
    if normalization not in {"none", "rms", "peak"}:
        raise ValueError("Normalization must be none, rms or peak")
    if not math.isfinite(target_db) or not -120 <= target_db <= 0:
        raise ValueError("Normalization target must be between -120 and 0 dBFS")
    events = parse_script(script, voice, speed)
    if not any(isinstance(event, Speech) for event in events):
        raise ValueError("Script contains no speech")
    output = Path(output)
    cache = Cache(cache_dir if cache_dir is not None else output / ".cache") if use_cache else None
    parts: list[PCM | float] = []
    segments: list[tuple[Speech, PCM, bool, str, int]] = []
    identity = getattr(engine, "cache_identity", engine.name)
    for event in events:
        if isinstance(event, Pause):
            parts.append(event.seconds)
            continue
        key = cache_key(identity, event.voice, event.speed, event.text)
        raw = cache.get(key) if cache else None
        hit = raw is not None
        if raw is None:
            raw = engine.synth(event.text, event.voice, event.speed)
            read_wav(raw)
            if cache:
                cache.put(key, raw)
        pcm = read_wav(raw)
        if normalization != "none":
            pcm = normalize(pcm, normalization, target_db)
        if segments:
            parts.append(gap)
        parts.append(pcm)
        segments.append((event, pcm, hit, key, len(parts) - 1))

    combined = concatenate(parts)
    offsets = {}
    cursor = 0
    for index, part in enumerate(parts):
        offsets[index] = cursor
        cursor += part.frames if isinstance(part, PCM) else silence_frames(part, combined.rate)
    sentences: list[dict[str, Any]] = []
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".render-", dir=output) as staging:
        stage = Path(staging)
        for index, (event, pcm, hit, key, part_index) in enumerate(segments, 1):
            filename = f"{index:04d}.wav"
            (stage / filename).write_bytes(write_wav(pcm))
            start = offsets[part_index]
            sentences.append(
                {
                    "text": event.text,
                    "file": filename,
                    "voice": event.voice,
                    "speed": event.speed,
                    "start": start / pcm.rate,
                    "end": (start + pcm.frames) / pcm.rate,
                    "start_frame": start,
                    "end_frame": start + pcm.frames,
                    "duration": pcm.duration,
                    "cache_hit": hit,
                    "cache_key": key,
                    "words": word_timings(event.text, start, pcm.frames, pcm.rate),
                }
            )
        manifest = {
            "schema_version": 1,
            "engine": engine.name,
            "audio": "narration.wav",
            "sample_rate": combined.rate,
            "channels": combined.channels,
            "duration": combined.duration,
            "frames": combined.frames,
            "gap_seconds": gap,
            "normalization": normalization,
            "target_dbfs": target_db,
            "word_timing": "estimated_character_weight",
            "sentences": sentences,
        }
        (stage / "narration.wav").write_bytes(write_wav(combined))
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        for filename in [s["file"] for s in sentences] + ["narration.wav", "manifest.json"]:
            os.replace(stage / filename, output / filename)
    return manifest
