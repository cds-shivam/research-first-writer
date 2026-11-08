#!/usr/bin/env python3
"""Contract tests for the explicit write slash command.

The command is a Markdown prompt executed by Claude Code, so interactive
approval and web research are documented manual checks rather than simulated
by a separate test framework.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COMMAND = ROOT / "commands" / "write.md"


class WriteCommandContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = COMMAND.read_text(encoding="utf-8")

    def test_command_has_frontmatter_and_argument_contract(self):
        self.assertTrue(self.text.startswith("---\n"))
        self.assertIn("description:", self.text)
        self.assertIn("argument-hint: <keyword>", self.text)
        self.assertIn("$ARGUMENTS", self.text)
        for kind in ("blog", "listicle", "comparison", "alternatives", "faq", "review"):
            self.assertIn(f"`{kind}`", self.text)

    def test_command_reuses_scaffold_and_writes_expected_files(self):
        self.assertIn("new_run.py <slug> --dir articles", self.text)
        for name in ("01-brief.md", "02-discover.md", "03-scores.md", "pages.json",
                     "04-analysis.md", "05-baselines.md", "06-research-brief.md",
                     "07-outline.md", "article.md", "review-report.md", "README.md"):
            self.assertIn(name, self.text)
        self.assertIn("refuses to overwrite", self.text)

    def test_command_defines_the_three_methodology_checkpoints(self):
        self.assertIn("after `02-discover.md`", self.text)
        self.assertIn("after `05-baselines.md`", self.text)
        self.assertIn("after `07-outline.md`", self.text)
        self.assertGreaterEqual(self.text.count("then stop"), 3)
        self.assertIn("explicit user approval", self.text)

    def test_integrity_rules_are_explicit(self):
        for phrase in ("fetch every page scored", "25 words or fewer",
                       "facts ledger", "[[NEEDS_HUMAN:", "never invent first-hand experience"):
            self.assertIn(phrase, self.text)


if __name__ == "__main__":
    unittest.main()
