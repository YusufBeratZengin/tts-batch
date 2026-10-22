import shutil
import tempfile
import unittest
from pathlib import Path

from tts_batch.audio import read_wav
from tts_batch.engines import EspeakEngine
from tts_batch.render import render

ESPEAK_BIN = shutil.which("espeak-ng") or shutil.which("espeak")


@unittest.skipUnless(ESPEAK_BIN, "espeak-ng or espeak not found on PATH")
class EspeakIntegrationTests(unittest.TestCase):
    def test_real_espeak_render_invariants(self) -> None:
        script_path = Path(__file__).resolve().parent.parent / "examples" / "script.md"
        script_text = script_path.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="tts-batch-test-espeak-") as tmp:
            out_dir = Path(tmp)
            engine = EspeakEngine()
            gap = 0.2
            manifest = render(script_text, out_dir, engine, gap=gap, normalization="rms")

            sentences = manifest["sentences"]
            self.assertGreaterEqual(len(sentences), 3)

            # Invariant 1: Monotonic start and end times / frames
            prev_end_frame = 0
            prev_end_time = 0.0
            sum_sentence_frames = 0
            for s in sentences:
                self.assertGreater(s["end"], s["start"])
                self.assertGreater(s["end_frame"], s["start_frame"])
                self.assertGreaterEqual(s["start"], prev_end_time)
                self.assertGreaterEqual(s["start_frame"], prev_end_frame)
                prev_end_time = s["end"]
                prev_end_frame = s["end_frame"]

                # Check each numbered WAV file
                wav_path = out_dir / s["file"]
                self.assertTrue(wav_path.is_file(), f"Missing file {s['file']}")
                pcm = read_wav(wav_path.read_bytes())
                sentence_frames = s["end_frame"] - s["start_frame"]
                self.assertEqual(pcm.frames, sentence_frames)
                sum_sentence_frames += sentence_frames

                # Invariant 3: Word timestamps within sentence bounds
                prev_word_end = s["start"]
                for w in s["words"]:
                    self.assertGreaterEqual(w["start"], s["start"] - 1e-4)
                    self.assertLessEqual(w["end"], s["end"] + 1e-4)
                    self.assertGreater(w["end"], w["start"])
                    self.assertGreaterEqual(w["start"], prev_word_end - 1e-4)
                    prev_word_end = w["end"]

            # Invariant 2: Numbered WAV frames plus silence equals narration.wav frames
            narration_path = out_dir / "narration.wav"
            self.assertTrue(narration_path.is_file())
            narration_pcm = read_wav(narration_path.read_bytes())
            self.assertEqual(narration_pcm.frames, manifest["frames"])
            self.assertAlmostEqual(narration_pcm.duration, manifest["duration"], places=3)
            silence_frames = manifest["frames"] - sum_sentence_frames
            self.assertGreater(silence_frames, 0)
            self.assertEqual(sum_sentence_frames + silence_frames, narration_pcm.frames)
