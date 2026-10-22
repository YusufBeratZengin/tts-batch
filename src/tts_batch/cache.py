"""Content-addressed cache of raw engine WAVs."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from .audio import read_wav


def asset_stamp(path: str) -> list[tuple[str, int, int]]:
    """Invalidate local assets changed in place (size/mtime, not a model checksum)."""
    result = []
    if path:
        for candidate in (Path(path), Path(path + ".json")):
            if candidate.is_file():
                stat = candidate.stat()
                result.append((str(candidate.resolve()), stat.st_size, stat.st_mtime_ns))
    return result


def cache_key(engine: str, voice: str, speed: float, text: str) -> str:
    payload = ["tts-batch-cache-v1", engine, voice, float(speed), text, asset_stamp(voice)]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class Cache:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def get(self, key: str) -> bytes | None:
        path = self.directory / f"{key}.wav"
        if not path.is_file():
            return None
        try:
            data = path.read_bytes()
            read_wav(data)
            return data
        except (ValueError, OSError):
            return None

    def put(self, key: str, data: bytes) -> None:
        read_wav(data)
        self.directory.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".cache-", dir=self.directory)
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(data)
            os.replace(name, self.directory / f"{key}.wav")
        finally:
            Path(name).unlink(missing_ok=True)
