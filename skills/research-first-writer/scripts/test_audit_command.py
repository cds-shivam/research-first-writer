#!/usr/bin/env python3
"""Contract tests for the explicit audit command."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import os


ROOT = Path(__file__).resolve().parents[3]
COMMAND = ROOT / "commands" / "audit.md"
CHECKER = ROOT / "skills" / "research-first-writer" / "scripts" / "check_article.py"


def command_text():
    return COMMAND.read_text(encoding="utf-8")


def test_frontmatter_and_discovery_contract():
    text = command_text()
    assert re.match(r"^---\ndescription: .+\nargument-hint: <path/to/article\.md>\n---\n", text, re.S)
    assert COMMAND.parent.name == "commands"
    assert "do not invent a second audit methodology" in text.lower()


def test_input_and_safe_report_contract():
    text = command_text()
    for phrase in (
        "Require exactly one article path",
        "has a `.md` extension",
        "preserving spaces",
        "Do not overwrite the article",
        "refuse to overwrite an existing file",
    ):
        assert phrase in text


def test_check_runs_before_judge_and_reports_failures():
    text = command_text()
    checker_call = "python3 skills/research-first-writer/scripts/check_article.py"
    assert checker_call in text
    assert text.index(checker_call) < text.index("## Perform the qualitative judge audit")
    for phrase in ("exit status", "non-zero status", "exact execution error", "still complete the judge review"):
        assert phrase in text


def test_missing_ledger_and_numbers_are_explicitly_handled():
    text = command_text()
    for phrase in (
        "06-research-brief.md",
        "If `06-research-brief.md` is missing",
        "percentages, money, decimals, statistics, dates",
        "List each claim requiring human verification",
        "matching number alone is not verification",
    ):
        assert phrase in text


def test_template_and_judge_contract():
    text = command_text()
    for phrase in (
        "SKILL.md",
        "checklists.md",
        "templates.md",
        "existing seven-dimension judge table",
        "quoted article evidence",
        "Verdict:",
        "What needs a person:",
        "Checks failing:",
        "What it rests on:",
    ):
        assert phrase in text


def test_existing_checker_reports_missing_ledger_numbers():
    with tempfile.TemporaryDirectory(dir=ROOT) as directory:
        article = Path(directory) / "article with spaces.md"
        article.write_text(
            "---\n"
            "title: \"Example\"\nmeta_title: \"Example article with enough words for a test\"\n"
            "meta_description: \"An article description that is long enough for the metadata check to inspect.\"\n"
            "slug: example-article\nkeyword: example\nkind: blog\ntarget_words: 10\n---\n"
            "## Example\n\nThis article reports 42% without a ledger.\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(article), "--json"],
            capture_output=True,
            cwd=ROOT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )
        output = (result.stdout or b"").decode("utf-8", errors="replace") + (result.stderr or b"").decode("utf-8", errors="replace")
        assert result.returncode != 0
        assert "42" in output
        assert "no ledger or brief found beside the article" in output


if __name__ == "__main__":
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} audit command tests passed")
