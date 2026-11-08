#!/usr/bin/env python3
"""Small regression tests for language-neutral article checks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from check_article import non_latin_script, words


ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / "skills" / "research-first-writer" / "scripts" / "check_article.py"


class UnicodeChecksTest(unittest.TestCase):
    def test_hindi_words_are_counted(self):
        self.assertGreaterEqual(len(words("छोटे व्यवसाय के लिए काम व्यवस्थित करें")), 6)

    def test_english_words_still_work(self):
        self.assertEqual(words("Choose a tool for a small business."),
                         ["Choose", "a", "tool", "for", "a", "small", "business"])

    def test_script_detection_distinguishes_hindi(self):
        self.assertTrue(non_latin_script("छोटे व्यवसाय के लिए काम व्यवस्थित करें"))
        self.assertFalse(non_latin_script("Choose a project management tool"))


    def test_four_target_languages_are_tokenized(self):
        samples = (
            ("Deutsch: Wählen Sie ein Werkzeug für kleine Unternehmen.", 4),
            ("Español: Elige una herramienta para pequeñas empresas.", 4),
            ("\u0939\u093f\u0928\u094d\u0926\u0940: \u091b\u094b\u091f\u0947 \u0935\u094d\u092f\u0935\u0938\u093e\u092f \u0915\u0947 \u0932\u093f\u090f \u090f\u0915 \u0909\u092a\u0915\u0930\u0923 \u091a\u0941\u0928\u0947\u0902\u0964", 4),
            ("\u65e5\u672c\u8a9e: \u4e2d\u5c0f\u4f01\u696d\u5411\u3051\u306e\u30c4\u30fc\u30eb\u3092\u9078\u3073\u307e\u3059\u3002", 1),
        )
        for sample, minimum in samples:
            with self.subTest(sample=sample):
                self.assertGreaterEqual(len(words(sample)), minimum)

    def test_latin_and_non_latin_target_scripts_are_distinguished(self):
        self.assertFalse(non_latin_script("Wählen Sie una herramienta für kleine empresas"))
        self.assertTrue(non_latin_script("\u4e2d\u5c0f\u4f01\u696d\u5411\u3051\u306e\u30c4\u30fc\u30eb\u3092\u9078\u3073\u307e\u3059"))

    def test_checker_runs_end_to_end_for_four_target_languages(self):
        fixtures = {
            "german": ("Werkzeug für kleine Unternehmen", "Kleine Teams profitieren von einer klaren Auswahl."),
            "spanish": ("herramienta para pequeñas empresas", "Los equipos pequeños necesitan una elección clara."),
            "hindi": ("छोटे व्यवसाय के लिए उपकरण", "छोटी टीमों के लिए स्पष्ट विकल्प उपयोगी हैं।"),
            "japanese": ("中小企業向けのツール", "小さなチームには明確な選択肢が役立ちます。"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            for slug, (keyword, sentence) in fixtures.items():
                article = Path(directory) / f"{slug}.md"
                article.write_text(
                    "---\n"
                    f"title: \"{keyword}\"\n"
                    f"meta_title: \"{keyword}\"\n"
                    f"meta_description: \"{sentence} {sentence} {sentence} {sentence}\"\n"
                    f"slug: {slug}-article\n"
                    f"keyword: {keyword}\n"
                    "kind: blog\n"
                    "target_words: 0\n"
                    "---\n\n"
                    f"## {keyword}\n\n{(sentence + ' ') * 30}\n",
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [sys.executable, str(CHECKER), str(article), "--json"],
                    cwd=ROOT,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, f"{slug}: {result.stdout.decode('utf-8', errors='replace')} {result.stderr.decode('utf-8', errors='replace')}")
                report = json.loads(result.stdout.decode("utf-8"))
                self.assertEqual(report["summary"]["block"], 0, slug)


if __name__ == "__main__":
    unittest.main()
