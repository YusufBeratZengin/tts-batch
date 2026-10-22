import math
from array import array

from tts_batch.audio import PCM, sample_bytes, write_wav


def sine(frames=800, rate=8000, channels=1, amplitude=4000):
    values = array("h")
    for index in range(frames):
        value = round(amplitude * math.sin(2 * math.pi * 440 * index / rate))
        values.extend([value] * channels)
    return PCM(rate, channels, sample_bytes(values))


class FakeEngine:
    name = "fake"

    def __init__(self, pcm=None):
        self.pcm = pcm if pcm is not None else sine()
        self.calls = []

    def synth(self, text, voice, speed):
        self.calls.append((text, voice, speed))
        return write_wav(self.pcm)
