#!/usr/bin/env python3
"""Rule-based draft checks from references/checklists.md (section 4).

Usage:
    python3 scripts/check_article.py path/to/article.md [--ledger path/to/06-research-brief.md] [--brief path/to/01-brief.md]

The article starts with YAML-style front matter:

    ---
    title: ...
    meta_title: ...
    meta_description: ...
    slug: ...
    keyword: ...
    kind: blog | listicle | comparison | alternatives | faq | review
    target_words: 1500
    ---

Standard library only. Exit code 1 when any check blocks, so it works in CI.
The judge (helpfulness, information gain, ...) is not here: that needs a reader.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

STOCK_PHRASES = [
    "in today's fast-paced world", "in today's digital landscape", "in the ever-evolving",
    "unlock the power", "game-changer", "delve into", "it's important to note",
    "look no further", "a testament to", "navigate the complexities", "in conclusion",
    "elevate your", "seamlessly", "harness the power",
]
NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"}

PASS, WARN, BLOCK = "pass", "warn", "block"
ICON = {PASS: "\033[32m✔ pass \033[0m", WARN: "\033[33m▲ warn \033[0m", BLOCK: "\033[31m✖ block\033[0m"}


def parse(path):
    text = Path(path).read_text(encoding="utf-8")
    meta, body = {}, text
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        body = m.group(2)
    return meta, body


def plain(md):
    """Markdown to rough plain text for counting."""
    md = re.sub(r"```.*?```", " ", md, flags=re.S)
    md = re.sub(r"\[\[NEEDS_HUMAN:[^\]]*\]\]", " ", md)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md)
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)
    md = re.sub(r"^\s*\|?[-:| ]+\|?\s*$", " ", md, flags=re.M)
    md = re.sub(r"[#>*_`|]", " ", md)
    return md


def words(s):
    # Unicode-aware tokenisation keeps combining marks (for example, Hindi
    # vowel signs) attached to their word instead of splitting one word into
    # several consonant-sized tokens.
    tokens, current = [], []
    for i, char in enumerate(s):
        category = unicodedata.category(char)
        is_word_char = category[0] in ("L", "M", "N")
        next_is_word = i + 1 < len(s) and unicodedata.category(s[i + 1])[0] in ("L", "M", "N")
        if is_word_char:
            current.append(char)
        elif char in "'’.-" and current and next_is_word:
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def non_latin_script(text):
    """Return True when alphabetic text is predominantly outside Latin."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    non_latin = sum(1 for c in letters if not ('A' <= c <= 'Z' or 'a' <= c <= 'z'))
    return non_latin / len(letters) >= 0.30


def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups) - (1 if w.endswith("e") and len(groups) > 1 else 0)
    return max(1, n)


def flesch(text):
    sents = [s for s in re.split(r"[.!?]+\s", text) if words(s)]
    ws = words(text)
    if not sents or not ws:
        return 100.0, 0.0
    syl = sum(syllables(w) for w in ws)
    wps, spw = len(ws) / len(sents), syl / len(ws)
    return 206.835 - 1.015 * wps - 84.6 * spw, 0.39 * wps + 11.8 * spw - 15.59


def numbers_needing_source(body):
    """Percentages, money and decimals always need a source (checklists §5)."""
    text = plain(body)
    found = set()
    for m in re.finditer(r"[$€£]\s?\d[\d,]*(?:\.\d+)?\s?[kKmMbB]?|\d[\d,]*(?:\.\d+)?\s?%|\b\d+\.\d+\b", text):
        found.add(m.group(0).strip())
    return sorted(found)


def norm_num(s):
    return re.sub(r"[\s,]", "", s).lower()


def main():
    # Reports include Unicode article text and check labels. Keep output usable
    # on Windows consoles whose legacy code page cannot encode those scripts.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("article")
    ap.add_argument("--ledger", help="research brief with the facts ledger; defaults to 06-research-brief.md beside the article")
    ap.add_argument("--brief", help="the brief; defaults to 01-brief.md beside the article")
    ap.add_argument("--json", action="store_true", help="print results as JSON instead of the report")
    args = ap.parse_args()

    meta, body = parse(args.article)
    here = Path(args.article).parent
    ledger_path = Path(args.ledger) if args.ledger else here / "06-research-brief.md"
    brief_path = Path(args.brief) if args.brief else here / "01-brief.md"
    sources = ""
    for p in (ledger_path, brief_path):
        if p.exists():
            sources += p.read_text(encoding="utf-8")

    kw = meta.get("keyword", "").lower()
    kind = meta.get("kind", "blog")
    target = int(meta.get("target_words", "0") or 0)
    text = plain(body)
    ws = words(text)
    n = len(ws)
    results = []

    def add(area, check, severity, detail=""):
        results.append((area, check, severity, detail))

    # Search
    title = meta.get("title", "")
    add("Search", "Title contains the keyword", PASS if kw and kw in title.lower() else BLOCK, title)
    mt = meta.get("meta_title", "")
    add("Search", "Meta title ≤ 60 chars with keyword",
        PASS if mt and len(mt) <= 60 and kw in mt.lower() else WARN, f"{len(mt)} chars")
    md_ = meta.get("meta_description", "")
    add("Search", "Meta description 70–160 chars", PASS if 70 <= len(md_) <= 160 else WARN, f"{len(md_)} chars")
    slug = meta.get("slug", "")
    add("Search", "Slug lower-case, hyphens, ≤ 80", PASS if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug) and len(slug) <= 80 else BLOCK, slug)

    # Structure
    heads = re.findall(r"^(#{2,3})\s+(.+)$", body, re.M)
    h2s = [h for lvl, h in heads if lvl == "##"]
    first_heading = heads[0][0] if heads else ""
    add("Structure", "First section is an H2", PASS if first_heading == "##" else BLOCK)
    dupes = {h for h in [h for _, h in heads] if [x for _, x in heads].count(h) > 1}
    add("Structure", "Headings unique", PASS if not dupes else BLOCK, ", ".join(dupes))
    kw_h2 = sum(1 for h in h2s if kw and kw in h.lower())
    add("Structure", "Keyword in ≥ 1 H2, ≤ half of them",
        PASS if 1 <= kw_h2 <= max(1, len(h2s) // 2) else WARN, f"{kw_h2} of {len(h2s)} H2s")

    # Length
    if target:
        dev = abs(n - target) / target
        add("Length", "Total within 10% of target", PASS if dev <= .10 else (WARN if dev <= .25 else BLOCK), f"{n} words vs {target}")
    sections = re.split(r"^##\s+.+$", body, flags=re.M)[1:]
    biggest = max((len(words(plain(s))) for s in sections), default=0)
    add("Length", "No section over 35% of words", PASS if n and biggest / n <= .35 else WARN, f"largest {biggest} words")

    # Kind
    if kind in ("listicle", "alternatives"):
        entries = [h for h in h2s if re.match(r"^\d+[.)]\s", h)]
        m = re.search(r"\b(?!(?:19|20)\d\d\b)(\d+)\b", title)  # a count, not a year
        ok = entries and (not m or int(m.group(1)) == len(entries))
        add("Kind", "Numbered entries match the title", PASS if ok else BLOCK, f"{len(entries)} entries")
    if kind == "comparison":
        add("Kind", "Has a comparison table", PASS if re.search(r"^\|.+\|\s*$", body, re.M) else BLOCK)
    if kind == "faq" or re.search(r"^##\s+(FAQ|Frequently asked)", body, re.M | re.I):
        qs = re.findall(r"^###\s+.+\?\s*$", body, re.M)
        need = 5 if kind == "faq" else 3
        add("Kind", f"FAQ has ≥ {need} questions", PASS if len(qs) >= need else BLOCK, f"{len(qs)} questions")
    if kind == "review":
        add("Kind", "Pros and cons section", PASS if re.search(r"pros|cons", body, re.I) else BLOCK)

    # Keywords
    first100 = " ".join(ws[:100]).lower()
    add("Keywords", "Keyword in first 100 words", PASS if kw and kw in first100 else WARN)
    kw_n = len(re.findall(re.escape(kw), text.lower())) if kw else 0
    density = (kw_n * len(kw.split()) / n * 100) if n else 0
    add("Keywords", "Exact-keyword density ≤ 2.5%", PASS if density <= 2.5 else (WARN if density <= 4 else BLOCK), f"{density:.2f}% ({kw_n}×)")

    # Grounding
    nums = numbers_needing_source(body)
    src_norm = norm_num(sources)
    ungrounded = [x for x in nums if norm_num(x) not in src_norm]
    if not sources:
        ungrounded = nums
    detail = ("not found: " + ", ".join(ungrounded)) if ungrounded else f"{len(nums)} checked"
    if not sources:
        detail += f"  (no ledger or brief found beside the article)"
    add("Grounding", "Every %, money, decimal is in the ledger or brief", PASS if not ungrounded else BLOCK, detail)
    placeholders = re.findall(r"lorem ipsum|TODO|TBD|\[insert", body, re.I)
    add("Grounding", "No placeholder text", PASS if not placeholders else BLOCK)

    # Honesty
    needs = re.findall(r"\[\[NEEDS_HUMAN:\s*([^\]]+)\]\]", body)
    add("Honesty", "NEEDS_HUMAN markers listed", PASS if not needs else WARN,
        f"{len(needs)} open" + ("".join(f"\n        · {x}" for x in needs) if needs else ""))

    first_hand = sorted(set(m.group(0).lower() for m in re.finditer(
        r"\bwe (?:tested|tried|reviewed|used|ran|found|saw)\b|\bour (?:testing|team found|tests?)\b|\bin our (?:testing|experience)\b|\bwe've (?:tested|used)\b", text, re.I)))
    m = re.search(r"First-hand notes:\s*(.+)", sources)
    has_notes = bool(m) and not re.match(r"\s*(none|n/a|-)", m.group(1), re.I)
    add("Honesty", "First-hand claims backed by first-hand notes",
        PASS if not first_hand or has_notes else BLOCK, ", ".join(first_hand) if first_hand else "")

    # Style
    if non_latin_script(text):
        add("Style", "Reading ease ≥ 45, grade ≤ 12", WARN,
            "not evaluated for predominantly non-Latin text")
        add("Style", "Fewer than two stock phrases", PASS,
            "English stock-phrase check not applicable")
    else:
        ease, grade = flesch(text)
        add("Style", "Reading ease ≥ 45, grade ≤ 12", PASS if ease >= 45 and grade <= 12 else WARN, f"ease {ease:.0f}, grade {grade:.1f}")
        stock = [p for p in STOCK_PHRASES if p in text.lower()]
        add("Style", "Fewer than two stock phrases", PASS if len(stock) < 2 else WARN, ", ".join(stock))
    paras = [p for p in re.split(r"\n\s*\n", body) if p.strip() and not p.lstrip().startswith(("#", "|", "-", "*", ">", "1."))]
    long_paras = [p for p in paras if len(words(plain(p))) > 130]
    add("Style", "Paragraphs under 130 words", PASS if not long_paras else WARN, f"{len(long_paras)} long")

    counts = {s: sum(1 for r in results if r[2] == s) for s in (PASS, WARN, BLOCK)}
    if args.json:
        import json
        print(json.dumps({
            "title": title, "words": n, "kind": kind, "keyword": kw,
            "checks": [{"area": a_, "check": c, "severity": sv, "detail": d} for a_, c, sv, d in results],
            "summary": {"pass": counts[PASS], "warn": counts[WARN], "block": counts[BLOCK], "needs_human": len(needs)},
        }, indent=2, ensure_ascii=False))
        return 1 if counts[BLOCK] else 0

    # Report
    print(f"\n  \033[1m{title}\033[0m")
    print(f"  {n} words · {len(h2s)} H2s · kind: {kind} · keyword: “{kw}”\n")
    area = None
    for a, check, sev, detail in results:
        if a != area:
            print(f"  \033[2m{a}\033[0m")
            area = a
        print(f"    {ICON[sev]}  {check}" + (f"  \033[2m— {detail}\033[0m" if detail else ""))
    print(f"\n  {counts[PASS]} passed · {counts[WARN]} warnings · {counts[BLOCK]} blocking")
    verdict = "Not ready: fix blocking checks first" if counts[BLOCK] else (
        "Not ready: items wait for a person" if needs else "Rules pass: send to the judge")
    print(f"  \033[1m{verdict}\033[0m\n")
    return 1 if counts[BLOCK] else 0


if __name__ == "__main__":
    sys.exit(main())
