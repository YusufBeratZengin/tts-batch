import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tts_batch.audio import read_wav, write_wav
from tts_batch.cli import main
from tts_batch.engines import EngineError, EspeakEngine, KokoroEngine, PiperEngine, _run, get_engine

from .helpers import FakeEngine, sine


class EngineTests(unittest.TestCase):
    def test_piper_arguments_and_wav_file(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "voice.onnx"
            model.write_bytes(b"mock")
            Path(str(model) + ".json").write_text("{}", encoding="utf-8")
            raw = write_wav(sine())

            def run(command, text):
                self.assertEqual(command[:3], ["piper", "--model", str(model.resolve())])
                self.assertEqual(command[command.index("--length_scale") + 1], "0.5")
                self.assertEqual(text, "Hello\n")
                Path(command[command.index("--output_file") + 1]).write_bytes(raw)

            with patch("tts_batch.engines._run", side_effect=run):
                self.assertEqual(PiperEngine().synth("Hello", str(model), 2), raw)

    def test_missing_piper_model_and_sidecar(self):
        with self.assertRaises(EngineError):
            PiperEngine().synth("Hello", "", 1)
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "voice.onnx"
            model.write_bytes(b"mock")
            with self.assertRaisesRegex(EngineError, "configuration"):
                PiperEngine().synth("Hello", str(model), 1)

    def test_espeak_voice_and_stdin(self):
        with (
            patch("tts_batch.engines.shutil.which", return_value="espeak-ng"),
            patch("tts_batch.engines._run", return_value=b"mock") as run,
        ):
            self.assertEqual(EspeakEngine().synth("Hello $(ignored)", "tr", 1.2), b"mock")
            command, text = run.call_args.args
            self.assertEqual(command[-2:], ["-v", "tr"])
            self.assertIn("210", command)
            self.assertEqual(text, "Hello $(ignored)")
        with (
            patch("tts_batch.engines.shutil.which", return_value=None),
            self.assertRaisesRegex(EngineError, "Install"),
        ):
            EspeakEngine().synth("Hello", "", 1)

    def test_subprocess_errors_and_safe_input(self):
        with patch(
            "tts_batch.engines.subprocess.run", return_value=SimpleNamespace(stdout=b"wav")
        ) as run:
            self.assertEqual(_run(["engine"], "Merhaba"), b"wav")
            self.assertEqual(run.call_args.kwargs["input"], b"Merhaba")
            self.assertNotIn("shell", run.call_args.kwargs)
            self.assertEqual(run.call_args.kwargs["timeout"], 120)
        for error in [
            FileNotFoundError(),
            subprocess.TimeoutExpired("engine", 120),
            subprocess.CalledProcessError(2, "engine", stderr=b"private text"),
        ]:
            with (
                patch("tts_batch.engines.subprocess.run", side_effect=error),
                self.assertRaises(EngineError) as raised,
            ):
                _run(["engine"], "Hello")
            self.assertNotIn("private text", str(raised.exception))

    def test_kokoro_local_assets_and_mocked_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model, config, voice = [
                root / name for name in ["model.pth", "config.json", "voice.pt"]
            ]
            for asset in (model, config, voice):
                asset.write_bytes(b"mock")
            audio = MagicMock()
            audio.detach.return_value.cpu.return_value.reshape.return_value.tolist.return_value = [
                0.0,
                0.5,
                -0.5,
                2.0,
            ]
            pipeline = MagicMock(return_value=[SimpleNamespace(audio=audio)])
            package = SimpleNamespace(
                KModel=MagicMock(), KPipeline=MagicMock(return_value=pipeline)
            )
            spacy = SimpleNamespace(util=SimpleNamespace(is_package=MagicMock(return_value=True)))
            with (
                patch.dict(sys.modules, {"kokoro": package, "spacy": spacy}),
                patch.dict(os.environ, {}, clear=False),
            ):
                engine = KokoroEngine(str(model), str(config))
                pcm = read_wav(engine.synth("Hello", str(voice), 1))
                self.assertEqual((pcm.rate, pcm.frames), (24000, 4))
                engine.synth("Again", str(voice), 1)
                package.KPipeline.assert_called_once()
                self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
                self.assertEqual(
                    package.KModel.call_args.kwargs,
                    {"config": str(config.resolve()), "model": str(model.resolve())},
                )
                with self.assertRaisesRegex(EngineError, "local .pt"):
                    engine.synth("Hello", "af_heart", 1)
                spacy.util.is_package.return_value = False
                with self.assertRaisesRegex(EngineError, "preinstalled"):
                    KokoroEngine(str(model), str(config)).synth("Hello", str(voice), 1)
            with patch.dict(sys.modules, {"kokoro": None}), patch.dict(os.environ):
                with self.assertRaisesRegex(EngineError, "optional extra"):
                    KokoroEngine(str(model), str(config)).synth("Hello", str(voice), 1)

    def test_factory_and_missing_kokoro_assets(self):
        self.assertIsInstance(get_engine("espeak"), EspeakEngine)
        self.assertIsInstance(get_engine("piper"), PiperEngine)
        with self.assertRaises(EngineError):
            get_engine("kokoro")
        with self.assertRaises(ValueError):
            get_engine("unknown")


class CliTests(unittest.TestCase):
    def test_cli_render_with_mock_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            script.write_text("\ufeff# heading\nHello world. Next!", encoding="utf-8")
            output = root / "out"
            with (
                patch("tts_batch.cli.get_engine", return_value=FakeEngine()),
                contextlib.redirect_stdout(io.StringIO()) as stdout,
            ):
                status = main(["render", str(script), "-o", str(output), "--engine", "espeak"])
            self.assertEqual(status, 0)
            self.assertIn("Rendered 2 segments", stdout.getvalue())
            self.assertTrue((output / "manifest.json").is_file())

    def test_cli_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["missing.txt", "bad.csv"]:
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    self.assertEqual(main(["render", str(root / name), "-o", str(root / "out")]), 1)
                self.assertIn("tts-batch:", stderr.getvalue())
            script = root / "bad.md"
            script.write_text("[speed zero]Hello", encoding="utf-8")
            with (
                contextlib.redirect_stderr(io.StringIO()),
                patch("tts_batch.cli.get_engine", return_value=FakeEngine()),
            ):
                self.assertEqual(main(["render", str(script), "-o", str(root / "out")]), 1)
