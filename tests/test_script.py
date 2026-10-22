import unittest

from tts_batch.script import Pause, Speech, parse_script, split_sentences


class SplitterTests(unittest.TestCase):
    def test_sentences_and_quotes(self):
        self.assertEqual(
            split_sentences('Hello! "Ready?" Yes... Go.'), ["Hello!", '"Ready?"', "Yes...", "Go."]
        )

    def test_abbreviations_initials_and_decimals(self):
        self.assertEqual(
            split_sentences("Dr. Ada met J. Smith at 3.14. It cost 1,234.50 dollars."),
            ["Dr. Ada met J. Smith at 3.14.", "It cost 1,234.50 dollars."],
        )
        self.assertEqual(
            split_sentences("Use e.g. apples and U.S. spelling. Done!"),
            ["Use e.g. apples and U.S. spelling.", "Done!"],
        )

    def test_multilingual(self):
        self.assertEqual(
            split_sentences("Merhaba dünya! Nasılsın? İyiyim."),
            ["Merhaba dünya!", "Nasılsın?", "İyiyim."],
        )
        self.assertEqual(
            split_sentences("你好。世界！元気？はい。"), ["你好。", "世界！", "元気？", "はい。"]
        )
        self.assertEqual(split_sentences("Привет! Как дела?"), ["Привет!", "Как дела?"])

    def test_turkish_abbreviations_decimals_and_ordinals(self):
        text = "Dr. Kaya 22. Ekim 2026 tarihinde saat 3,5 saat süren bir sunum yaptı. İkinci cümle."
        self.assertEqual(
            split_sentences(text),
            [
                "Dr. Kaya 22. Ekim 2026 tarihinde saat 3,5 saat süren bir sunum yaptı.",
                "İkinci cümle.",
            ],
        )
        self.assertEqual(
            split_sentences(
                "Bu çalışma 21. yy. başındaki gelişmeleri ve 3. sıradaki yenilikleri ele alıyor."
            ),
            [
                "Bu çalışma 21. yy. başındaki gelişmeleri ve 3. sıradaki yenilikleri ele alıyor.",
            ],
        )
        self.assertEqual(
            split_sentences(
                "Örn. elma, armut vb. meyveler sepetteydi. Detay için bkz. rapor vs. belgeler."
            ),
            [
                "Örn. elma, armut vb. meyveler sepetteydi.",
                "Detay için bkz. rapor vs. belgeler.",
            ],
        )

    def test_numbers_domains_and_whitespace(self):
        self.assertEqual(
            split_sentences("1. First item. See example.org.\nNext line"),
            ["1.", "First item.", "See example.org.", "Next line"],
        )
        self.assertEqual(split_sentences(" \n\t "), [])


class MarkupTests(unittest.TestCase):
    def test_persistent_settings_emphasis_and_comments(self):
        script = "# Header\nHello *world*. [pause 500ms] [speed 1.1]Next. [voice x]Last!\n #skip"
        self.assertEqual(
            parse_script(script, "base"),
            [
                Speech("Hello world.", "base", 1),
                Pause(0.5),
                Speech("Next.", "base", 1.1),
                Speech("Last!", "x", 1.1),
            ],
        )

    def test_mid_sentence_directives_are_boundaries(self):
        self.assertEqual(
            parse_script("One[pause 20ms]two[speed 2]three"),
            [
                Speech("One", "", 1),
                Pause(0.02),
                Speech("two", "", 1),
                Speech("three", "", 2),
            ],
        )

    def test_voice_path_spaces_and_multiline_text(self):
        self.assertEqual(
            parse_script("[voice voices/my voice.onnx]Hello\nworld."),
            [Speech("Hello world.", "voices/my voice.onnx", 1)],
        )

    def test_invalid_markup_and_speed(self):
        for text in [
            "[speed 0]a",
            "[speed nan]a",
            "[speed inf]a",
            "[pause -1ms]a",
            "[pause 2s]a",
            "[voice ]a",
            "[unknown x]a",
            "[pause 20ms",
            "a]",
            "[[pause 1ms]]",
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_script(text)
        for speed in [0, -1, float("nan"), float("inf")]:
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                parse_script("Hello", speed=speed)
