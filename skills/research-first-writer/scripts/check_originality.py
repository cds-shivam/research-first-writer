#!/usr/bin/env python3
"""Check an article for verbatim runs and repeated five-word phrases.

Usage:
    python3 check_originality.py article.md source-1.md [source-2.md ...]
    python3 check_originality.py article.md source.md --outline 07-outline.md [--json]

The checker uses only the Python standard library. Exit code 1 means at least
one source triggered a blocking originality rule.
"""
import argparse
import json
import re
import sys
from pathlib import Path

TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+|-[^\W_]+)*", re.UNICODE)
FRONT_MATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---[ \t]*\r?\n", re.S)
INLINE_QUOTE_RE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”')
CREDIT_RE = re.compile(
    r"\baccording to\b|\b(?:says|said|states|stated|writes|wrote|notes|noted|"
    r"reports|reported|calls|called|describes|described|explains|explained|"
    r"confirms|confirmed|warns|warned|quoted|credits?)\b",
    re.I,
)
FAQ_HEADING_RE = re.compile(r"^(?:faq|frequently asked questions?)\b", re.I)
BLOCKQUOTE_RE = re.compile(r"(?m)(?:^>[ \t]?.*(?:\r?\n|$))+")


def tokens(text):
    """Return case-folded word tokens, ignoring Markdown punctuation."""
    return [match.group(0).casefold() for match in TOKEN_RE.finditer(text)]


def plain_markdown(text):
    """Remove front matter and Markdown syntax while retaining prose."""
    text = FRONT_MATTER_RE.sub("", text, count=1)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[#>*_`|]", " ", text)


def question_key(text):
    return tuple(tokens(text))


def outline_questions(outline):
    """Collect explicitly written questions from the outline."""
    questions = set()
    for line in outline.splitlines():
        if "?" not in line:
            continue
        cells = line.split("|")
        for cell in cells:
            for candidate in re.findall(r"[^?]*\?", cell):
                candidate = re.split(r"(?<=[.!;])\s+", candidate)[-1]
                key = question_key(candidate)
                if key:
                    questions.add(key)
    return questions


def required_faq_ranges(article, outline):
    """Find article FAQ question headings that are listed in the outline."""
    if not outline:
        return []
    required = outline_questions(outline)
    ranges = []
    headings = list(re.finditer(r"(?m)^(#{2,6})[ \t]+(.+?)\s*$", article))
    faq_level = None
    for heading in headings:
        level = len(heading.group(1))
        title = heading.group(2).strip()
        if level == 2:
            faq_level = level if FAQ_HEADING_RE.match(title) else None
            continue
        if faq_level and level > faq_level and title.endswith("?"):
            if question_key(title) in required:
                end = article.find("\n", heading.start())
                ranges.append((heading.start(), len(article) if end < 0 else end))
    return ranges


def _is_credited_quote(text, start, end):
    paragraph_start = text.rfind("\n\n", 0, start) + 2
    paragraph_end = text.find("\n\n", end)
    if paragraph_end < 0:
        paragraph_end = len(text)
    context = text[paragraph_start:paragraph_end]
    return bool(CREDIT_RE.search(context) or re.search(r"\[[^\]]+\]\([^)]+\)", context))


def exempt_ranges(article):
    """Return ranges for credited short quotes and required FAQ questions."""
    ranges = []
    for match in BLOCKQUOTE_RE.finditer(article):
        quote_text = re.sub(r"(?m)^>[ \t]?", "", match.group(0))
        following = article[match.end():].splitlines()
        attribution = following[0].strip() if following else ""
        credited = bool(
            CREDIT_RE.search(quote_text)
            or re.search(r"\[[^\]]+\]\([^)]+\)", quote_text)
            or re.search(r"(?m)^\s*[—–-]\s+\S", quote_text)
            or re.match(r"^(?:[-—–]\s+|\*{1,2})", attribution)
            or CREDIT_RE.search(attribution)
        )
        if credited and len(tokens(quote_text)) <= 25:
            ranges.append((match.start(), match.end()))

    for match in INLINE_QUOTE_RE.finditer(article):
        quote_text = match.group(1) or match.group(2)
        if len(tokens(quote_text)) <= 25 and _is_credited_quote(article, match.start(), match.end()):
            ranges.append((match.start(), match.end()))
    return ranges


def mask_ranges(text, ranges):
    chars = list(text)
    for start, end in ranges:
        chars[start:end] = " " * (end - start)
    return "".join(chars)


def longest_common_run(article_tokens, source_tokens):
    """Find the longest common contiguous token sequence."""
    upper = min(len(article_tokens), len(source_tokens))
    low, high = 0, upper

    def find(size):
        source_phrases = {}
        for start in range(len(source_tokens) - size + 1):
            source_phrases.setdefault(tuple(source_tokens[start:start + size]), start)
        for start in range(len(article_tokens) - size + 1):
            phrase = tuple(article_tokens[start:start + size])
            if phrase in source_phrases:
                return start, source_phrases[phrase]
        return None

    while low < high:
        size = (low + high + 1) // 2
        if find(size) is not None:
            low = size
        else:
            high = size - 1
    if not low:
        return 0, ""
    match = find(low)
    return low, " ".join(article_tokens[match[0]:match[0] + low])


def shared_phrase_stats(article_tokens, source_tokens, phrase_size=5):
    article_count = max(0, len(article_tokens) - phrase_size + 1)
    if not article_count:
        return 0, 0, 0.0
    source_phrases = {
        tuple(source_tokens[start:start + phrase_size])
        for start in range(max(0, len(source_tokens) - phrase_size + 1))
    }
    shared = sum(
        tuple(article_tokens[start:start + phrase_size]) in source_phrases
        for start in range(article_count)
    )
    return shared, article_count, shared / article_count * 100


def check_source(article_tokens, source_tokens, source):
    run_length, run_text = longest_common_run(article_tokens, source_tokens)
    shared, total, percentage = shared_phrase_stats(article_tokens, source_tokens)
    run_status = "block" if run_length >= 14 else "warn" if run_length >= 10 else "pass"
    phrase_status = "block" if percentage > 20 else "warn" if percentage >= 10 else "pass"
    severity = "block" if "block" in (run_status, phrase_status) else (
        "warn" if "warn" in (run_status, phrase_status) else "pass"
    )
    return {
        "source": str(source),
        "longest_run": {"words": run_length, "text": run_text, "severity": run_status},
        "shared_phrases": {
            "shared": shared,
            "total": total,
            "percentage": round(percentage, 2),
            "severity": phrase_status,
        },
        "severity": severity,
    }


def analyze(article_path, source_paths, outline_path=None):
    article = Path(article_path).read_text(encoding="utf-8")
    outline = Path(outline_path).read_text(encoding="utf-8") if outline_path else ""
    ranges = exempt_ranges(article) + required_faq_ranges(article, outline)
    article_tokens = tokens(plain_markdown(mask_ranges(article, ranges)))
    results = []
    for source_path in source_paths:
        source = Path(source_path).read_text(encoding="utf-8")
        source_tokens = tokens(plain_markdown(source))
        results.append(check_source(article_tokens, source_tokens, source_path))
    return {
        "article": str(article_path),
        "sources": results,
        "summary": {
            "block": sum(result["severity"] == "block" for result in results),
            "warn": sum(result["severity"] == "warn" for result in results),
            "pass": sum(result["severity"] == "pass" for result in results),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("article", type=Path)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument(
        "--outline",
        type=Path,
        help="outline listing required FAQ questions; defaults to 07-outline.md beside the article",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    outline_path = args.outline or args.article.with_name("07-outline.md")
    if not args.article.is_file():
        parser.error(f"article file not found: {args.article}")
    missing_sources = [path for path in args.sources if not path.is_file()]
    if missing_sources:
        parser.error("source file(s) not found: " + ", ".join(map(str, missing_sources)))
    if args.outline and not args.outline.is_file():
        parser.error(f"outline file not found: {args.outline}")
    if not args.outline and not outline_path.is_file():
        outline_path = None

    report = analyze(args.article, args.sources, outline_path)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for result in report["sources"]:
            run = result["longest_run"]
            phrases = result["shared_phrases"]
            excerpt = f' ("{run["text"]}")' if run["text"] else ""
            print(f'{result["source"]}: {result["severity"].upper()}')
            print(f'  Longest verbatim run: {run["words"]} words{excerpt} [{run["severity"]}]')
            print(
                f'  Shared 5-word phrases: {phrases["percentage"]:.2f}% '
                f'({phrases["shared"]}/{phrases["total"]}) [{phrases["severity"]}]'
            )
        summary = report["summary"]
        print(
            f'\n{summary["pass"]} passed · {summary["warn"]} warnings · '
            f'{summary["block"]} blocking'
        )
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    sys.exit(main())
