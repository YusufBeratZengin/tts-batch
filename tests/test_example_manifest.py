import json
import unittest

from scripts.make_example import EXAMPLE_FILE, ROOT, generate_manifest


class ExampleManifestTests(unittest.TestCase):
    def test_example_manifest_matches_generated(self) -> None:
        self.assertTrue(EXAMPLE_FILE.is_file(), "manifest.example.json does not exist")
        on_disk = json.loads(EXAMPLE_FILE.read_text(encoding="utf-8"))
        fresh = generate_manifest()
        self.assertEqual(on_disk, fresh)

    def test_readme_files_contain_manifest_excerpt(self) -> None:
        readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_tr = (ROOT / "README.tr.md").read_text(encoding="utf-8")

        summary_line = "Rendered 2 segments (2.000s) to out/"
        self.assertIn(summary_line, readme_en)
        self.assertIn(summary_line, readme_tr)

        # Check key fields from manifest in READMEs
        for key in ['"schema_version": 1', '"audio": "narration.wav"', '"0001.wav"', '"0002.wav"']:
            self.assertIn(key, readme_en)
            self.assertIn(key, readme_tr)

    def test_demo_svg_exists_and_embedded_in_readmes(self) -> None:
        demo_svg = ROOT / "docs" / "demo.svg"
        self.assertTrue(demo_svg.is_file(), "docs/demo.svg does not exist")
        content = demo_svg.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("<svg"), "demo.svg must be an SVG file")
        self.assertIn("</svg>", content)

        readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_tr = (ROOT / "README.tr.md").read_text(encoding="utf-8")
        self.assertIn("docs/demo.svg", readme_en)
        self.assertIn("docs/demo.svg", readme_tr)
