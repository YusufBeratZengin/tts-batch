import json
import tempfile
import unittest
from pathlib import Path

from tts_batch.audio import read_wav
from tts_batch.cache import Cache, cache_key
from tts_batch.render import render, word_timings

from .helpers import FakeEngine, sine


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "out"

    def test_timing_manifest_and_output_files(self):
        engine = FakeEngine()
        manifest = render(
            "[pause 10ms]Hi there. [pause 50ms]Goodbye![pause 20ms]",
            self.out,
            engine,
            gap=0.025,
            normalization="none",
        )
        first, second = manifest["sentences"]
        self.assertEqual((first["start_frame"], first["end_frame"]), (80, 880))
        self.assertEqual((second["start_frame"], second["end_frame"]), (1480, 2280))
        self.assertEqual(manifest["frames"], 2440)
        self.assertEqual(manifest["duration"], 0.305)
        self.assertEqual(manifest, json.loads((self.out / "manifest.json").read_text("utf-8")))
        for sentence in manifest["sentences"]:
            audio = read_wav((self.out / sentence["file"]).read_bytes())
            self.assertEqual(audio.duration, sentence["duration"])
            self.assertEqual(sentence["words"][0]["start"], sentence["start"])
            self.assertEqual(sentence["words"][-1]["end"], sentence["end"])
        self.assertEqual(read_wav((self.out / "narration.wav").read_bytes()).frames, 2440)

    def test_cache_reuse_and_normalization_independence(self):
        engine = FakeEngine()
        first = render("Repeat. Repeat.", self.out, engine, normalization="none")
        second = render("Repeat. Repeat.", self.out, engine, normalization="peak", gap=0.5)
        self.assertEqual(len(engine.calls), 1)
        self.assertFalse(first["sentences"][0]["cache_hit"])
        self.assertTrue(first["sentences"][1]["cache_hit"])
        self.assertTrue(all(s["cache_hit"] for s in second["sentences"]))
        render("Repeat.", self.out, engine, voice="other", speed=1.1)
        self.assertEqual(len(engine.calls), 2)

    def test_no_cache_and_custom_directory(self):
        engine = FakeEngine()
        render("Repeat. Repeat.", self.out, engine, use_cache=False)
        self.assertEqual(len(engine.calls), 2)
        self.assertFalse((self.out / ".cache").exists())
        cache = Path(self.temp.name) / "custom-cache"
        render("Repeat.", self.out, engine, cache_dir=cache)
        self.assertEqual(len(list(cache.glob("*.wav"))), 1)

    def test_failure_preserves_previous_render(self):
        render("First.", self.out, FakeEngine())
        previous = (self.out / "manifest.json").read_bytes()

        class ChangingEngine(FakeEngine):
            name = "changing"

            def synth(self, text, voice, speed):
                self.pcm = sine(rate=8000 if not self.calls else 16000)
                return super().synth(text, voice, speed)

        with self.assertRaisesRegex(ValueError, "same sample rate"):
            render("First. Second.", self.out, ChangingEngine())
        self.assertEqual((self.out / "manifest.json").read_bytes(), previous)
        self.assertFalse(any(self.out.glob(".render-*")))

    def test_invalid_inputs(self):
        for script, options in [
            ("# comment", {}),
            ("[pause 50ms]", {}),
            ("A", {"gap": -1}),
            ("A", {"normalization": "bad"}),
            ("A", {"target_db": 10}),
        ]:
            with self.subTest(script=script, options=options), self.assertRaises(ValueError):
                render(script, self.out, FakeEngine(), **options)

    def test_word_estimates_unicode_and_order(self):
        for text in ["Hello, world!", "Merhaba dünya.", "你好。", "Hello世界", "don't stop"]:
            words = word_timings(text, 100, 800, 8000)
            self.assertEqual(words[0]["start"], 100 / 8000)
            self.assertEqual(words[-1]["end"], 900 / 8000)
            self.assertTrue(
                all(a["end"] == b["start"] for a, b in zip(words, words[1:], strict=False))
            )
        self.assertEqual(
            [w["text"] for w in word_timings("Hello世界", 0, 800, 8000)], ["Hello", "世", "界"]
        )
        self.assertEqual(word_timings("!!!", 0, 100, 8000), [])


class CacheTests(unittest.TestCase):
    def test_key_dimensions(self):
        base = cache_key("fake", "en", 1, "Hello")
        self.assertEqual(base, cache_key("fake", "en", 1.0, "Hello"))
        for args in [
            ("other", "en", 1, "Hello"),
            ("fake", "fr", 1, "Hello"),
            ("fake", "en", 2, "Hello"),
            ("fake", "en", 1, "Bye"),
        ]:
            self.assertNotEqual(base, cache_key(*args))

    def test_cache_round_trip_corruption_and_local_asset_invalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = Cache(root / "cache")
            voice = root / "voice.onnx"
            voice.write_bytes(b"model")
            key = cache_key("fake", str(voice), 1, "Hello")
            self.assertIsNone(cache.get(key))
            raw = FakeEngine().synth("Hello", "", 1)
            cache.put(key, raw)
            self.assertEqual(cache.get(key), raw)
            (cache.directory / f"{key}.wav").write_bytes(b"broken")
            self.assertIsNone(cache.get(key))
            cache.put(key, raw)
            voice.write_bytes(b"different model")
            self.assertNotEqual(key, cache_key("fake", str(voice), 1, "Hello"))
            self.assertFalse(list(cache.directory.glob(".cache-*")))
