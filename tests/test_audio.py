import io
import math
import unittest
import wave
from array import array

from tts_batch.audio import (
    PCM,
    concatenate,
    normalize,
    read_wav,
    sample_bytes,
    samples,
    write_wav,
)

from .helpers import sine


class AudioTests(unittest.TestCase):
    def test_round_trip_and_exact_concat_frames(self):
        first = sine(frames=1600)
        second = sine(frames=800)
        joined = concatenate([0.01, first, 0.125, second, 0.02])
        self.assertEqual(joined.frames, 80 + 1600 + 1000 + 800 + 160)
        self.assertEqual(joined.data[1680 * 2 : 2680 * 2], bytes(2000))
        self.assertEqual(read_wav(write_wav(joined)), joined)
        self.assertEqual(joined.duration, joined.frames / 8000)

    def test_stereo_silence_and_format_mismatch(self):
        pcm = sine(channels=2)
        self.assertEqual(concatenate([pcm, 0.1, pcm]).frames, 2400)
        for other in [sine(rate=16000), sine(channels=2)]:
            with self.assertRaisesRegex(ValueError, "same sample rate"):
                concatenate([sine(), other])

    def test_peak_and_rms_normalization(self):
        pcm = sine(frames=8000)
        normalized = normalize(pcm, "peak", -6)
        peak = max(abs(v) for v in samples(normalized.data))
        self.assertAlmostEqual(peak, 32767 * 10 ** (-6 / 20), delta=1)
        normalized = normalize(pcm, "rms", -20)
        values = samples(normalized.data)
        rms = math.sqrt(sum(v * v for v in values) / len(values))
        self.assertAlmostEqual(rms, 3276.7, delta=1)
        self.assertEqual(normalized.frames, pcm.frames)

    def test_peak_limiting_silence_and_negative_full_scale(self):
        pcm = PCM(8000, 1, sample_bytes(array("h", [-32768, 0, 1, 0])))
        result = normalize(pcm, "rms", 0)
        self.assertLessEqual(max(abs(v) for v in samples(result.data)), 32767)
        silent = PCM(8000, 1, bytes(160))
        self.assertEqual(normalize(silent), silent)

    def test_invalid_audio(self):
        with self.assertRaises(ValueError):
            read_wav(b"not wav")
        with self.assertRaises(ValueError):
            PCM(8000, 1, b"x")
        for width in [1, 3, 4]:
            stream = io.BytesIO()
            with wave.open(stream, "wb") as target:
                target.setparams((1, width, 8000, 0, "NONE", "not compressed"))
                target.writeframes(bytes(width * 8))
            with self.assertRaisesRegex(ValueError, "16-bit"):
                read_wav(stream.getvalue())
        with self.assertRaisesRegex(ValueError, "empty audio"):
            read_wav(write_wav(PCM(8000, 1, b"")))

    def test_invalid_controls(self):
        for gap in [-1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                concatenate([sine(), gap])
        for mode, target in [("bad", -20), ("rms", 1), ("peak", float("nan"))]:
            with self.assertRaises(ValueError):
                normalize(sine(), mode, target)
        with self.assertRaises(ValueError):
            concatenate([0.2])
