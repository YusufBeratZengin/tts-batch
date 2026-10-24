"""Tests covering edge-case branches for comprehensive test coverage."""

from __future__ import annotations

import contextlib
import io
import runpy
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tts_batch.cli import main
from tts_batch.engines import (
    EngineError,
    KokoroEngine,
    PiperEngine,
    list_espeak_voices,
)
from tts_batch.script import parse_script, split_sentences


class CoverageBranchTests(unittest.TestCase):
    def test_main_module_execution(self) -> None:
        with patch("sys.argv", ["tts-batch", "--version"]):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_module("tts_batch", run_name="__main__")
            self.assertEqual(cm.exception.code, 0)

    def test_cli_no_subcommand_returns_two(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = main([])
        self.assertEqual(code, 2)
        self.assertIn("usage: tts-batch", stderr.getvalue())

    def test_cli_missing_script_argument(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = main(["render"])
        self.assertEqual(code, 1)
        self.assertIn("Script argument is required", stderr.getvalue())

    def test_cli_dry_run_empty_speech(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.md"
            empty_file.write_text("# Just comments\n# Nothing else\n", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = main(["render", str(empty_file), "--dry-run"])
            self.assertEqual(code, 1)
            self.assertIn("Script contains no speech", stderr.getvalue())

    def test_cli_missing_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "test.md"
            script_file.write_text("Hello world.", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = main(["render", str(script_file)])
            self.assertEqual(code, 1)
            self.assertIn("Output directory (-o/--output) is required", stderr.getvalue())

    def test_list_espeak_voices_called_process_error(self) -> None:
        with (
            patch("tts_batch.engines.shutil.which", return_value="espeak-ng"),
            patch(
                "tts_batch.engines.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, ["espeak-ng", "--voices"]),
            ),
        ):
            with self.assertRaisesRegex(EngineError, "failed with exit code 1"):
                list_espeak_voices()

    def test_piper_engine_missing_output_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            model = Path(tmpdir) / "model.onnx"
            model.write_bytes(b"model")
            Path(str(model) + ".json").write_text("{}", encoding="utf-8")

            # Mock _run so it succeeds but does NOT create output_file
            with patch("tts_batch.engines._run"):
                with self.assertRaisesRegex(EngineError, "Piper did not produce a WAV file"):
                    PiperEngine().synth("Hello", str(model), 1.0)

    def test_kokoro_unsupported_language_and_cache_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            model = Path(tmpdir) / "model.pth"
            model.write_bytes(b"pth")
            config = Path(tmpdir) / "config.json"
            config.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(EngineError, "Unsupported Kokoro language"):
                KokoroEngine(str(model), str(config), lang="xx")

            engine = KokoroEngine(str(model), str(config), lang="a")
            identity = engine.cache_identity
            self.assertIn("kokoro", identity)
            self.assertIn('"a"', identity)

    def test_kokoro_synthesis_no_audio_and_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            model = Path(tmpdir) / "model.pth"
            model.write_bytes(b"pth")
            config = Path(tmpdir) / "config.json"
            config.write_text("{}", encoding="utf-8")
            voice = Path(tmpdir) / "voice.pt"
            voice.write_bytes(b"voice")

            engine = KokoroEngine(str(model), str(config), lang="e")

            # Mock kokoro module with empty audio results
            fake_result = SimpleNamespace(audio=None)
            fake_pipeline = MagicMock(return_value=[fake_result])
            fake_kokoro = SimpleNamespace(
                KModel=MagicMock(return_value=MagicMock(eval=MagicMock())),
                KPipeline=MagicMock(return_value=fake_pipeline),
            )

            with patch.dict("sys.modules", {"kokoro": fake_kokoro}):
                with self.assertRaisesRegex(EngineError, "Kokoro returned no audio"):
                    engine.synth("Hola", str(voice), 1.0)

            # Mock kokoro module raising unexpected exception
            failing_pipeline = MagicMock(side_effect=RuntimeError("GPU fault"))
            fake_kokoro_failing = SimpleNamespace(
                KModel=MagicMock(return_value=MagicMock(eval=MagicMock())),
                KPipeline=MagicMock(return_value=failing_pipeline),
            )
            engine_fail = KokoroEngine(str(model), str(config), lang="e")
            with patch.dict("sys.modules", {"kokoro": fake_kokoro_failing}):
                with self.assertRaisesRegex(EngineError, "Kokoro synthesis failed"):
                    engine_fail.synth("Hola", str(voice), 1.0)

    def test_sentence_split_inline_latin_punctuation(self) -> None:
        # Punctuation inside a word or followed by non-space
        sentences = split_sentences("Wait!what happened?now. That was fast.")
        self.assertEqual(len(sentences), 2)
        self.assertEqual(sentences[0], "Wait!what happened?now.")
        self.assertEqual(sentences[1], "That was fast.")

    def test_pause_directive_validation(self) -> None:
        events = parse_script("[pause 250ms]\nHello.")
        self.assertEqual(len(events), 2)

        with self.assertRaisesRegex(ValueError, "Invalid or unknown directive"):
            parse_script("[pause abc]")

        with self.assertRaisesRegex(ValueError, "Pause must be finite"):
            parse_script(f"[pause {'9' * 400}ms]")
