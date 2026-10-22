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

    def test_cli_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for ext in [".md", ".txt"]:
                script = root / f"test{ext}"
                script.write_text("Sentence one. [speed 1.5]Sentence two.", encoding="utf-8")
                with (
                    patch("tts_batch.cli.get_engine") as mock_engine,
                    contextlib.redirect_stdout(io.StringIO()) as stdout,
                ):
                    status = main(["render", str(script), "--dry-run"])
                self.assertEqual(status, 0)
                mock_engine.assert_not_called()
                out = stdout.getvalue()
                self.assertIn("Segment 0001", out)
                self.assertIn("Sentence one.", out)
                self.assertIn("Segment 0002", out)
                self.assertIn("Sentence two.", out)
                self.assertIn("speed: 1.50", out)

    def test_cli_list_voices(self):
        mock_output = (
            "  Pty Language Age/Gender VoiceName          File          Other Languages\n"
            " 5  en            M  default             default\n"
        )
        with (
            patch("tts_batch.engines.shutil.which", return_value="espeak-ng"),
            patch(
                "tts_batch.engines.subprocess.run",
                return_value=SimpleNamespace(stdout=mock_output),
            ),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(main(["--list-voices"]), 0)
            self.assertIn("VoiceName", stdout.getvalue())

        with (
            patch("tts_batch.engines.shutil.which", return_value="espeak-ng"),
            patch(
                "tts_batch.engines.subprocess.run",
                return_value=SimpleNamespace(stdout=mock_output),
            ),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(main(["render", "--list-voices"]), 0)
            self.assertIn("VoiceName", stdout.getvalue())

        with (
            patch("tts_batch.engines.shutil.which", return_value=None),
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            self.assertEqual(main(["--list-voices"]), 1)
            err = stderr.getvalue()
            self.assertIn("tts-batch: Install espeak-ng or espeak and add it to PATH", err)
            self.assertEqual(len(err.strip().splitlines()), 1)
            self.assertNotIn("Traceback", err)

    def test_error_handling_invalid_directives_and_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out_dir = root / "out"

            # 1. Invalid directives
            for directive in ["[pause abc]", "[speed 0]", "[speed -1]", "[pause -5ms]"]:
                script = root / "invalid_directive.md"
                script.write_text(f"{directive}Hello world.", encoding="utf-8")
                with (
                    contextlib.redirect_stderr(io.StringIO()) as stderr,
                    patch("tts_batch.cli.get_engine", return_value=FakeEngine()),
                ):
                    code = main(["render", str(script), "-o", str(out_dir)])
                self.assertEqual(code, 1, f"Failed for {directive}")
                err = stderr.getvalue()
                self.assertTrue(err.startswith("tts-batch: "), err)
                self.assertEqual(len(err.strip().splitlines()), 1, err)
                self.assertNotIn("Traceback", err)

            # 2. Empty script
            empty_script = root / "empty.md"
            empty_script.write_text("", encoding="utf-8")
            with (
                contextlib.redirect_stderr(io.StringIO()) as stderr,
                patch("tts_batch.cli.get_engine", return_value=FakeEngine()),
            ):
                code = main(["render", str(empty_script), "-o", str(out_dir)])
            self.assertEqual(code, 1)
            err = stderr.getvalue()
            self.assertIn("tts-batch: Script contains no speech", err)
            self.assertEqual(len(err.strip().splitlines()), 1)
            self.assertNotIn("Traceback", err)

            # 3. Script with only comments
            comment_script = root / "comments.md"
            comment_script.write_text("# Line 1\n# Line 2\n", encoding="utf-8")
            with (
                contextlib.redirect_stderr(io.StringIO()) as stderr,
                patch("tts_batch.cli.get_engine", return_value=FakeEngine()),
            ):
                code = main(["render", str(comment_script), "-o", str(out_dir)])
            self.assertEqual(code, 1)
            err = stderr.getvalue()
            self.assertIn("tts-batch: Script contains no speech", err)
            self.assertEqual(len(err.strip().splitlines()), 1)
            self.assertNotIn("Traceback", err)

            # 4. Output directory is a file
            dummy_file = root / "file_not_dir.txt"
            dummy_file.write_text("I am a file", encoding="utf-8")
            valid_script = root / "valid.md"
            valid_script.write_text("Hello world.", encoding="utf-8")
            with (
                contextlib.redirect_stderr(io.StringIO()) as stderr,
                patch("tts_batch.cli.get_engine", return_value=FakeEngine()),
            ):
                code = main(["render", str(valid_script), "-o", str(dummy_file)])
            self.assertEqual(code, 1)
            err = stderr.getvalue()
            self.assertTrue(err.startswith("tts-batch: "), err)
            self.assertIn("Output directory cannot be a file", err)
            self.assertEqual(len(err.strip().splitlines()), 1)
            self.assertNotIn("Traceback", err)

            # 5. Engine returns non-WAV bytes
            class NonWavEngine:
                name = "non_wav"

                def synth(self, text, voice, speed):
                    return b"not a valid wav file header"

            with (
                contextlib.redirect_stderr(io.StringIO()) as stderr,
                patch("tts_batch.cli.get_engine", return_value=NonWavEngine()),
            ):
                code = main(["render", str(valid_script), "-o", str(out_dir), "--no-cache"])
            self.assertEqual(code, 1)
            err = stderr.getvalue()
            self.assertTrue(err.startswith("tts-batch: "), err)
            self.assertIn("Invalid WAV audio", err)
            self.assertEqual(len(err.strip().splitlines()), 1)
            self.assertNotIn("Traceback", err)

            # 6. Engine returns 8-bit WAV bytes
            import wave

            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(1)
                w.setframerate(8000)
                w.writeframes(b"\x80" * 100)
            eight_bit_bytes = buf.getvalue()

            class EightBitEngine:
                name = "eight_bit"

                def synth(self, text, voice, speed):
                    return eight_bit_bytes

            with (
                contextlib.redirect_stderr(io.StringIO()) as stderr,
                patch("tts_batch.cli.get_engine", return_value=EightBitEngine()),
            ):
                code = main(["render", str(valid_script), "-o", str(out_dir), "--no-cache"])
            self.assertEqual(code, 1)
            err = stderr.getvalue()
            self.assertTrue(err.startswith("tts-batch: "), err)
            self.assertIn("Only uncompressed 16-bit PCM WAV is supported", err)
            self.assertEqual(len(err.strip().splitlines()), 1)
            self.assertNotIn("Traceback", err)

            # 7. Engine returns mixed sample rates
            two_sentence_script = root / "two_sentences.md"
            two_sentence_script.write_text("First sentence. Second sentence.", encoding="utf-8")

            class MixedRateEngine:
                name = "mixed_rate"

                def __init__(self):
                    self.call_count = 0

                def synth(self, text, voice, speed):
                    self.call_count += 1
                    rate = 8000 if self.call_count == 1 else 16000
                    return write_wav(sine(rate=rate))

            with (
                contextlib.redirect_stderr(io.StringIO()) as stderr,
                patch("tts_batch.cli.get_engine", return_value=MixedRateEngine()),
            ):
                code = main(["render", str(two_sentence_script), "-o", str(out_dir), "--no-cache"])
            self.assertEqual(code, 1)
            err = stderr.getvalue()
            self.assertTrue(err.startswith("tts-batch: "), err)
            self.assertIn("All segments must have the same sample rate and channel count", err)
            self.assertEqual(len(err.strip().splitlines()), 1)
            self.assertNotIn("Traceback", err)
