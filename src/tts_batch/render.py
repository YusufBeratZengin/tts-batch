"""Render parsed scripts, preserving frame-based sentence timing."""

import json
import math
import os
import re
import tempfile
import wave
from pathlib import Path
from typing import Any

from .audio import normalize, read_wav, silence_frames, write_wav
from .cache import Cache, cache_key
from .engines import Engine
from .script import Pause, Speech, parse_script

# CJK characters are individual caption units; space-delimited words elsewhere.
_WORDS = re.compile(
    r"[\u3400-\u9fff\u3040-\u30ff]|"
    r"[^\W_\u3400-\u9fff\u3040-\u30ff]+(?:['’\-][^\W_\u3400-\u9fff\u3040-\u30ff]+)*",
    re.UNICODE,
)


def word_timings(text: str, start_frame: int, frames: int, rate: int) -> list[dict[str, Any]]:
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
) -> dict[str, Any]:
    """Write numbered WAVs, narration.wav and manifest.json; return manifest.

    Pauses and gaps are additive. Staging prevents synthesis/format failures
    from overwriting an earlier render. Narration audio is streamed frame-by-frame,
    holding only the current segment in memory.
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
    if output.is_file():
        raise ValueError(f"Output directory cannot be a file: {output}")
    cache = Cache(cache_dir if cache_dir is not None else output / ".cache") if use_cache else None
    identity = getattr(engine, "cache_identity", engine.name)

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".render-", dir=output) as staging:
        stage = Path(staging)
        narration_path = stage / "narration.wav"
        narration_file: wave.Wave_write | None = None
        rate: int | None = None
        channels: int | None = None
        cursor = 0
        pending_pauses: list[float] = []
        speech_count = 0
        sentences: list[dict[str, Any]] = []

        try:
            for event in events:
                if isinstance(event, Pause):
                    if narration_file is None:
                        pending_pauses.append(event.seconds)
                    else:
                        assert rate is not None and channels is not None
                        pframes = silence_frames(event.seconds, rate)
                        if pframes > 0:
                            cursor += pframes
                            narration_file.writeframes(bytes(pframes * channels * 2))
                    continue

                # Speech event
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

                if narration_file is None:
                    rate = pcm.rate
                    channels = pcm.channels
                    narration_file = wave.open(str(narration_path), "wb")
                    narration_file.setnchannels(channels)
                    narration_file.setsampwidth(2)
                    narration_file.setframerate(rate)
                    for psec in pending_pauses:
                        pframes = silence_frames(psec, rate)
                        if pframes > 0:
                            cursor += pframes
                            narration_file.writeframes(bytes(pframes * channels * 2))
                    pending_pauses.clear()
                else:
                    assert rate is not None and channels is not None
                    if (pcm.rate, pcm.channels) != (rate, channels):
                        raise ValueError(
                            "All segments must have the same sample rate and channel count"
                        )
                    if speech_count > 0 and gap > 0:
                        gframes = silence_frames(gap, rate)
                        if gframes > 0:
                            cursor += gframes
                            narration_file.writeframes(bytes(gframes * channels * 2))

                speech_count += 1
                filename = f"{speech_count:04d}.wav"
                (stage / filename).write_bytes(write_wav(pcm))
                start = cursor
                cursor += pcm.frames
                narration_file.writeframes(pcm.data)

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

            assert rate is not None and channels is not None and narration_file is not None
            narration_file.close()
            narration_file = None

            manifest = {
                "schema_version": 1,
                "engine": engine.name,
                "audio": "narration.wav",
                "sample_rate": rate,
                "channels": channels,
                "duration": cursor / rate,
                "frames": cursor,
                "gap_seconds": gap,
                "normalization": normalization,
                "target_dbfs": target_db,
                "word_timing": "estimated_character_weight",
                "sentences": sentences,
            }
            (stage / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            for filename in [s["file"] for s in sentences] + ["narration.wav", "manifest.json"]:
                os.replace(stage / filename, output / filename)
        finally:
            if narration_file is not None:
                narration_file.close()

    return manifest
