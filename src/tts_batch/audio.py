"""16-bit PCM WAV processing using only the standard library."""

import io
import math
import sys
import wave
from array import array
from dataclasses import dataclass


@dataclass(frozen=True)
class PCM:
    rate: int
    channels: int
    data: bytes

    def __post_init__(self) -> None:
        if self.rate <= 0 or self.channels <= 0 or len(self.data) % (2 * self.channels):
            raise ValueError("Invalid 16-bit PCM frames")

    @property
    def frames(self) -> int:
        return len(self.data) // (2 * self.channels)

    @property
    def duration(self) -> float:
        return self.frames / self.rate


def read_wav(data: bytes) -> PCM:
    try:
        with wave.open(io.BytesIO(data), "rb") as source:
            if source.getsampwidth() != 2 or source.getcomptype() != "NONE":
                raise ValueError("Only uncompressed 16-bit PCM WAV is supported")
            pcm = PCM(
                source.getframerate(), source.getnchannels(), source.readframes(source.getnframes())
            )
            # espeak --stdout can use an oversized streaming header. Actual PCM
            # frames, rather than the advertised count, determine its duration.
            if not pcm.frames:
                raise ValueError("Engine returned empty audio")
            return pcm
    except (wave.Error, EOFError) as exc:
        raise ValueError("Invalid WAV audio") from exc


def write_wav(pcm: PCM) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as target:
        target.setnchannels(pcm.channels)
        target.setsampwidth(2)
        target.setframerate(pcm.rate)
        target.writeframes(pcm.data)
    return buffer.getvalue()


def samples(data: bytes) -> array:
    values = array("h")
    values.frombytes(data)
    if sys.byteorder != "little":
        values.byteswap()
    return values


def sample_bytes(values: array) -> bytes:
    values = array("h", values)
    if sys.byteorder != "little":
        values.byteswap()
    return values.tobytes()


def normalize(pcm: PCM, mode: str = "rms", target_db: float = -20.0) -> PCM:
    """Apply constant gain, limiting peaks to prevent clipping; not LUFS."""
    if mode not in {"rms", "peak"}:
        raise ValueError("Normalization mode must be rms or peak")
    if not math.isfinite(target_db) or not -120 <= target_db <= 0:
        raise ValueError("Normalization target must be between -120 and 0 dBFS")
    values = samples(pcm.data)
    peak = max((abs(value) for value in values), default=0)
    if not peak:
        return pcm
    level = peak if mode == "peak" else math.sqrt(sum(v * v for v in values) / len(values))
    gain = min(32767 * 10 ** (target_db / 20) / level, 32767 / peak)
    normalized = array("h", (max(-32768, min(32767, round(v * gain))) for v in values))
    return PCM(pcm.rate, pcm.channels, sample_bytes(normalized))


def silence_frames(seconds: float, rate: int) -> int:
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Silence duration must be finite and nonnegative")
    return round(seconds * rate)


def concatenate(parts: list[PCM | float]) -> PCM:
    """Floats represent silence in seconds; require identical audio formats."""
    reference = next((part for part in parts if isinstance(part, PCM)), None)
    if reference is None:
        raise ValueError("At least one speech segment is required")
    chunks = []
    for part in parts:
        if isinstance(part, PCM):
            if (part.rate, part.channels) != (reference.rate, reference.channels):
                raise ValueError("All segments must have the same sample rate and channel count")
            chunks.append(part.data)
        else:
            chunks.append(bytes(silence_frames(part, reference.rate) * reference.channels * 2))
    return PCM(reference.rate, reference.channels, b"".join(chunks))
