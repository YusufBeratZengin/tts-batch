"""Engine plugins. No model or voice downloads are initiated here."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from array import array
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .audio import PCM, sample_bytes, write_wav
from .cache import asset_stamp
from .script import positive_speed

if TYPE_CHECKING:
    from kokoro import KPipeline


class EngineError(RuntimeError):
    """An engine is unavailable or failed to synthesize speech."""


class Engine(Protocol):
    name: str

    def synth(self, text: str, voice: str, speed: float) -> bytes:
        """Return a complete 16-bit PCM WAV file."""
        ...


def _run(command: list[str], text: str) -> bytes:
    try:
        result = subprocess.run(
            command, input=text.encode("utf-8"), capture_output=True, timeout=120, check=True
        )
        return result.stdout
    except FileNotFoundError as exc:
        raise EngineError(f"Executable not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise EngineError(f"{command[0]} exceeded the 120-second synthesis timeout") from exc
    except subprocess.CalledProcessError as exc:
        # Avoid echoing scripts or environment information from external stderr.
        raise EngineError(f"{command[0]} failed with exit code {exc.returncode}") from exc


def list_espeak_voices() -> str:
    executable = shutil.which("espeak-ng") or shutil.which("espeak")
    if not executable:
        raise EngineError("Install espeak-ng or espeak and add it to PATH")
    try:
        result = subprocess.run(
            [executable, "--voices"], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as exc:
        raise EngineError(f"{executable} failed with exit code {exc.returncode}") from exc


class PiperEngine:
    name = "piper"

    def synth(self, text: str, voice: str, speed: float) -> bytes:
        positive_speed(speed)
        model = Path(voice).resolve()
        if not voice or not model.is_file():
            raise EngineError("Piper requires --voice pointing to a local .onnx model")
        if not Path(str(model) + ".json").is_file():
            raise EngineError("Piper requires the model's adjacent .onnx.json configuration")
        with tempfile.TemporaryDirectory(prefix="tts-batch-") as directory:
            output = Path(directory) / "speech.wav"
            _run(
                [
                    "piper",
                    "--model",
                    str(model),
                    "--length_scale",
                    str(1 / speed),
                    "--output_file",
                    str(output),
                ],
                text + "\n",
            )
            if not output.is_file():
                raise EngineError("Piper did not produce a WAV file")
            return output.read_bytes()


class EspeakEngine:
    name = "espeak"

    def synth(self, text: str, voice: str, speed: float) -> bytes:
        positive_speed(speed)
        executable = shutil.which("espeak-ng") or shutil.which("espeak")
        if not executable:
            raise EngineError("Install espeak-ng or espeak and add it to PATH")
        command = [executable, "--stdout", "--stdin", "-b", "1", "-s", str(round(175 * speed))]
        if voice:
            command.extend(["-v", voice])
        return _run(command, text)


class KokoroEngine:
    name = "kokoro"

    def __init__(self, model: str, config: str, lang: str = "a"):
        if not model or not config or not Path(model).is_file() or not Path(config).is_file():
            raise EngineError("Kokoro requires local --kokoro-model and --kokoro-config files")
        if lang not in {"a", "b", "e", "f", "h", "i", "p", "z"}:
            raise EngineError(
                "Unsupported Kokoro language code (Japanese is not supported offline)"
            )
        self.model = str(Path(model).resolve())
        self.config = str(Path(config).resolve())
        self.lang = lang
        self._pipeline: KPipeline | None = None

    @property
    def cache_identity(self) -> str:
        return json.dumps([self.name, self.lang, asset_stamp(self.model), asset_stamp(self.config)])

    def synth(self, text: str, voice: str, speed: float) -> bytes:
        positive_speed(speed)
        if not voice or not Path(voice).is_file() or Path(voice).suffix != ".pt":
            raise EngineError("Kokoro --voice must be a local .pt voice tensor")
        # Fail closed for Hugging Face/Transformers. G2P assets must also have
        # been provisioned separately; no online fallback is enabled here.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        try:
            from kokoro import KModel, KPipeline
        except ImportError as exc:
            raise EngineError(
                "Install the optional extra: pip install 'tts-batch[kokoro]'"
            ) from exc
        try:
            if self._pipeline is None:
                if self.lang in {"a", "b"}:
                    import spacy

                    if not spacy.util.is_package("en_core_web_sm"):
                        raise EngineError(
                            "Kokoro English requires a preinstalled en_core_web_sm spaCy model"
                        )
                model = KModel(config=self.config, model=self.model).eval()
                self._pipeline = KPipeline(lang_code=self.lang, model=model, device="cpu")
            values = array("h")
            for result in self._pipeline(text, voice=str(Path(voice).resolve()), speed=speed):
                if result.audio is not None:
                    values.extend(
                        max(-32768, min(32767, round(float(value) * 32767)))
                        for value in result.audio.detach().cpu().reshape(-1).tolist()
                    )
            if not values:
                raise EngineError("Kokoro returned no audio")
            return write_wav(PCM(24000, 1, sample_bytes(values)))
        except EngineError:
            raise
        except Exception as exc:
            raise EngineError(
                "Kokoro synthesis failed; check local model, voice and G2P assets"
            ) from exc


def get_engine(name: str, *, model: str = "", config: str = "", lang: str = "a") -> Engine:
    if name == "piper":
        return PiperEngine()
    if name == "espeak":
        return EspeakEngine()
    if name == "kokoro":
        return KokoroEngine(model, config, lang)
    raise ValueError(f"Unknown engine: {name}")
