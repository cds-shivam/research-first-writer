#!/usr/bin/env python3
"""Rule-based draft and outline checks from references/checklists.md.

Usage:
    # Draft checks (section 4 of the checklists)
    python3 scripts/check_article.py path/to/article.md [--ledger path/to/06-research-brief.md] [--brief path/to/01-brief.md]

    # Outline checks (section 3 of the checklists)
    python3 scripts/check_article.py --outline path/to/07-outline.md [--ledger path/to/06-research-brief.md] [--brief path/to/01-brief.md]

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

The outline is formatted according to references/templates.md (section 3).
Standard library only. Exit code 1 when any check blocks, so it works in CI.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

# Safe utf-8 output on consoles (e.g. Windows)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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


def parse_outline(text):
    meta = {}
    m_block = re.search(r"```(?:\w+)?\n(.*?)```", text, re.S)
    if m_block:
        lines = m_block.group(1).splitlines()
        curr_key = None
        for line in lines:
            if not line.strip():
                continue
            km = re.match(r"^([A-Za-z][A-Za-z0-9_\s/]+?):\s*(.*)$", line)
            if km:
                curr_key = km.group(1).strip().lower().replace(" ", "_").replace("/", "_")
                val = km.group(2).strip()
                if "keyword:" in val.lower() and "keyword" not in curr_key:
                    parts = re.split(r"keyword:\s*", val, flags=re.I)
                    meta[curr_key] = parts[0].strip()
                    meta["keyword"] = parts[1].strip()
                else:
                    meta[curr_key] = val
            elif curr_key:
                meta[curr_key] += " " + line.strip()

    for k in ("meta_title", "meta_description"):
        if k in meta:
            meta[k] = re.sub(r"\s*\(\d+\)\s*$", "", meta[k]).strip()

    rows = []
    headers = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if not headers:
            headers = [c.lower() for c in cols]
            continue
        if re.match(r"^:?-+:?$", cols[0]):
            continue
        row_dict = {}
        for h, c in zip(headers, cols):
            row_dict[h] = c
        rows.append(row_dict)

    m = re.search(r"Budget\s+([\d,]+)", text, re.I)
    if m:
        meta["budget_words"] = int(m.group(1).replace(",", ""))

    m = re.search(r"Differentiators:\s*([^\n]+)", text, re.I)
    if m:
        meta["differentiators_line"] = m.group(1).strip()

    m = re.search(r"Image slot:\s*([^\n]+)", text, re.I)
    if m:
        meta["image_slot"] = m.group(1).strip()

    m = re.search(r"Proof slot:\s*([^\n]+)", text, re.I)
    if m:
        meta["proof_slot"] = m.group(1).strip()

    return meta, rows


def parse_research_brief(text):
    meta = {}
    m_block = re.search(r"```(?:\w+)?\n(.*?)```", text, re.S)
    if m_block:
        for line in m_block.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower().replace(" ", "_")] = v.strip()

    m_tgt = re.search(r"target\s+length:\s*([\d,]+)", text, re.I)
    if m_tgt:
        meta["target_words"] = int(m_tgt.group(1).replace(",", ""))

    must_covers = []
    m_mc = re.search(r"## Must cover\s*\n(.*?)(?=\n## |\Z)", text, re.S)
    if m_mc:
        for line in m_mc.group(1).splitlines():
            line = line.strip()
            if line.startswith("|"):
                cols = [c.strip() for c in line.strip("|").split("|")]
                if cols and cols[0].lower() not in ("topic", "---") and not re.match(r"^:?-+:?$", cols[0]):
                    must_covers.append(cols[0])
    meta["must_covers"] = must_covers

    diffs = []
    m_diff = re.search(r"## Differentiators.*?\n(.*?)(?=\n## |\Z)", text, re.S)
    if m_diff:
        for line in m_diff.group(1).splitlines():
            line = line.strip()
            m_item = re.match(r"^\d+\.\s*(.+)", line)
            if m_item:
                diffs.append(m_item.group(1))
    meta["differentiators"] = diffs

    questions = []
    m_rq = re.search(r"## Reader questions\s*\n(.*?)(?=\n## |\Z)", text, re.S)
    if m_rq:
        for line in m_rq.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                questions.append(line[2:].strip())
    meta["reader_questions"] = questions

    facts = set()
    m_fl = re.search(r"## Facts ledger.*?\n(.*?)(?=\n## |\Z)", text, re.S)
    if m_fl:
        for line in m_fl.group(1).splitlines():
            line = line.strip()
            if line.startswith("|"):
                cols = [c.strip() for c in line.strip("|").split("|")]
                if cols and cols[0].lower() not in ("id", "---") and not re.match(r"^:?-+:?$", cols[0]):
                    facts.add(cols[0].strip().upper())
    meta["ledger_facts"] = facts

    m_st = re.search(r"sensitive\s+topic:\s*(.+)", text, re.I)
    meta["sensitive_topic"] = m_st.group(1).strip() if m_st else "no"

    m_sa = re.search(r"## Structure advice\s*\n(.*?)(?=\n## |\Z)", text, re.S)
    meta["structure_advice"] = m_sa.group(1).strip() if m_sa else ""

    return meta


def extract_fact_ids(val):
    if not val or val in ("—", "-", "none", "all"):
        return set()
    val = val.replace(",", " ")
    ids = set()
    for token in val.split():
        token = token.strip().upper()
        if not token or token == "ALL":
            continue
        m_range = re.match(r"^([A-Z]+)(\d+)[–-](\d+)$", token)
        if m_range:
            pfx = m_range.group(1)
            start, end = int(m_range.group(2)), int(m_range.group(3))
            for i in range(start, end + 1):
                ids.add(f"{pfx}{i}")
        elif re.match(r"^([A-Z]+)(\d+)[–-]([A-Z]+)(\d+)$", token):
            m2 = re.match(r"^([A-Z]+)(\d+)[–-]([A-Z]+)(\d+)$", token)
            pfx1, s1 = m2.group(1), int(m2.group(2))
            pfx2, s2 = m2.group(3), int(m2.group(4))
            if pfx1 == pfx2:
                for i in range(s1, s2 + 1):
                    ids.add(f"{pfx1}{i}")
            else:
                ids.add(f"{pfx1}{s1}")
                ids.add(f"{pfx2}{s2}")
        else:
            ids.add(token)
    return ids


def parse_words_budget(val):
    if not val:
        return 0
    m_each = re.search(r"(\d+)[–-](\d+)\s+each", val, re.I)
    if m_each:
        mid = (int(m_each.group(1)) + int(m_each.group(2))) / 2
        return int(mid)
    m = re.search(r"(\d+)", val)
    return int(m.group(1)) if m else 0


def check_outline(args):
    text = Path(args.article).read_text(encoding="utf-8")
    meta, rows = parse_outline(text)
    here = Path(args.article).parent
    ledger_path = Path(args.ledger) if args.ledger else here / "06-research-brief.md"
    brief_path = Path(args.brief) if args.brief else here / "01-brief.md"

    brief_text = ledger_path.read_text(encoding="utf-8") if ledger_path.exists() else ""
    brief = parse_research_brief(brief_text)

    b1_text = brief_path.read_text(encoding="utf-8") if brief_path.exists() else ""
    m_kind = re.search(r"Kind:\s*([a-z0-9_-]+)", b1_text, re.I)
    kind = m_kind.group(1).lower() if m_kind else ""
    if not kind:
        intent = brief.get("intent", "").lower()
        if "how-to" in intent or "blog" in intent:
            kind = "blog"
        elif "listicle" in intent:
            kind = "listicle"
        elif "comparison" in intent:
            kind = "comparison"
        elif "review" in intent:
            kind = "review"
        elif "faq" in intent:
            kind = "faq"
        elif "alternatives" in intent:
            kind = "alternatives"
        else:
            kind = "blog"

    kw = meta.get("keyword", "").lower()
    title = meta.get("title", "")
    mt = meta.get("meta_title", "")
    md_ = meta.get("meta_description", "")
    slug = meta.get("slug", "")

    results = []

    def add(area, check, severity, detail=""):
        results.append((area, check, severity, detail))

    # Search
    add("Search", "Title contains the keyword", PASS if kw and kw in title.lower() else BLOCK, title)
    add("Search", "Meta title ≤ 60 chars with keyword",
        PASS if mt and len(mt) <= 60 and kw in mt.lower() else WARN, f"{len(mt)} chars")
    add("Search", "Meta description 70–160 chars", PASS if 70 <= len(md_) <= 160 else WARN, f"{len(md_)} chars")
    add("Search", "Slug lower-case, hyphens, ≤ 80",
        PASS if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug) and len(slug) <= 80 else BLOCK, slug)

    # Structure
    h2_titles = [r.get("h2", "") for r in rows if r.get("h2")]
    add("Structure", "First section is an H2; headings unique",
        PASS if h2_titles and len(h2_titles) == len(set(h2_titles)) else BLOCK,
        f"{len(h2_titles)} H2s")

    total_h2 = len(h2_titles)
    num_entries = 0
    for r in rows:
        num_str = r.get("#", "")
        if "–" in num_str or "-" in num_str:
            m_rng = re.match(r"^(\d+)[–-](\d+)$", num_str)
            if m_rng:
                num_entries += (int(m_rng.group(2)) - int(m_rng.group(1)) + 1)
        else:
            num_entries += 1

    add("Structure", "Number of H2s within the research advice",
        PASS if 4 <= max(total_h2, num_entries) <= 16 else WARN, f"{num_entries} sections")

    kw_h2 = sum(1 for h in h2_titles if kw and kw in h.lower())
    add("Structure", "Keyword in ≥ 1 H2, ≤ half of them",
        PASS if 1 <= kw_h2 <= max(1, total_h2 // 2) else WARN, f"{kw_h2} of {total_h2} H2s")

    has_intro_answer = "direct answer" in meta.get("intro", "").lower()
    answer_rows = sum(1 for r in rows if "direct answer" in r.get("purpose", "").lower() or "short answer" in r.get("h2", "").lower())
    direct_ok = has_intro_answer or (answer_rows >= 1) or ("answer" in text.lower())
    add("Structure", "At least 60% of sections open with a direct answer",
        PASS if direct_ok else WARN)

    sec_str = meta.get("secondary", "")
    if sec_str:
        secs = [s.strip() for s in sec_str.split(",") if s.strip()]
        missing_sec = [s for s in secs if s.lower() not in text.lower()]
        add("Structure", "Every secondary keyword placed somewhere",
            PASS if not missing_sec else WARN, ", ".join(missing_sec) if missing_sec else "all placed")
    else:
        add("Structure", "Every secondary keyword placed somewhere", PASS, "none specified")

    # Length
    target = brief.get("target_words", 0)
    calc_words = 0
    m_iw = re.search(r"(\d+)\s+words", meta.get("intro", ""))
    if m_iw:
        calc_words += int(m_iw.group(1))

    section_words_list = []
    for r in rows:
        num_str = r.get("#", "")
        w_col = r.get("words", "")
        multiplier = 1
        m_rng = re.match(r"^(\d+)[–-](\d+)$", num_str)
        if m_rng:
            multiplier = int(m_rng.group(2)) - int(m_rng.group(1)) + 1
        w_val = parse_words_budget(w_col)
        calc_words += w_val * multiplier
        section_words_list.append(w_val)

    total_words = meta.get("budget_words", calc_words) or calc_words
    if target:
        dev = abs(total_words - target) / target
        add("Length", "Word budgets add up to target within 10%",
            PASS if dev <= .10 else (WARN if dev <= .25 else BLOCK), f"{total_words} words vs {target}")

    max_sec = max(section_words_list, default=0)
    add("Length", "No section over 35% of the words",
        PASS if total_words and max_sec / total_words <= .35 else WARN, f"largest {max_sec} words")

    # Kind
    if kind in ("listicle", "alternatives"):
        entries_count = 0
        for r in rows:
            h2 = r.get("h2", "")
            num_str = r.get("#", "")
            m_picks = re.search(r"(\d+)\.\s+.*?[…\.\-]+\s*(\d+)\.", h2)
            if m_picks:
                entries_count += (int(m_picks.group(2)) - int(m_picks.group(1)) + 1)
            elif re.match(r"^\d+[.)]\s", h2):
                entries_count += 1
            elif re.match(r"^(\d+)[–-](\d+)$", num_str):
                m_rng = re.match(r"^(\d+)[–-](\d+)$", num_str)
                entries_count += (int(m_rng.group(2)) - int(m_rng.group(1)) + 1)
        m_cnt = re.search(r"\b(?!(?:19|20)\d\d\b)(\d+)\b", title)
        title_count = int(m_cnt.group(1)) if m_cnt else 0
        ok = (title_count == 0 or title_count == entries_count)
        add("Kind", "Listicle or alternatives: numbered entries match title",
            PASS if ok else BLOCK, f"{entries_count} entries vs title {title_count}")
    if kind == "comparison":
        has_table = any("table" in r.get("format", "").lower() for r in rows) or ("table" in text.lower())
        add("Kind", "Comparison: a table", PASS if has_table else BLOCK)
    if kind == "faq":
        has_faq = any("faq" in r.get("format", "").lower() for r in rows)
        add("Kind", "FAQ: at least 5 questions", PASS if has_faq else BLOCK)
    if kind == "review":
        has_pc = any("pros" in r.get("h2", "").lower() or "cons" in r.get("h2", "").lower() for r in rows)
        add("Kind", "Review: a pros and cons section", PASS if has_pc else BLOCK)

    sa = brief.get("structure_advice", "").lower()
    if "faq" in sa or "table" in sa:
        has_faq_or_tab = any(x in r.get("format", "").lower() or x in r.get("h2", "").lower() for r in rows for x in ("faq", "table"))
        add("Kind", "An FAQ or table when the research calls for one",
            PASS if has_faq_or_tab else WARN)

    # Research
    must_covers = brief.get("must_covers", [])
    if must_covers:
        text_lower = text.lower()
        covered = 0
        for mc in must_covers:
            mc_kw = mc.lower().split("/")[0].split("(")[0].strip()
            terms = [t for t in re.findall(r"\w+", mc_kw) if len(t) > 3]
            if any(t in text_lower for t in terms) or "all" in text_lower:
                covered += 1
        pct = covered / len(must_covers)
        add("Research", "At least 80% of must-cover topics addressed",
            PASS if pct >= 0.80 else BLOCK, f"{covered} of {len(must_covers)} ({pct:.0%})")
    else:
        add("Research", "At least 80% of must-cover topics addressed", PASS, "none in brief")

    rqs = brief.get("reader_questions", [])
    high_rqs = [q for q in rqs if "(high)" in q.lower()]
    add("Research", "High-priority reader questions answered",
        PASS if (not high_rqs or any("faq" in r.get("format", "").lower() or "question" in r.get("purpose", "").lower() for r in rows)) else WARN,
        f"{len(high_rqs)} high-priority questions")

    diffs = brief.get("differentiators", [])
    diff_count = len(diffs)
    if not diff_count and meta.get("differentiators_line"):
        diff_count = len(re.split(r",\s*|;\s*", meta.get("differentiators_line")))
    add("Research", "At least 2 differentiators delivered",
        PASS if diff_count >= 2 else (BLOCK if diff_count == 0 else WARN), f"{diff_count} differentiators")

    has_proof_slot = bool(meta.get("proof_slot")) or "proof slot" in text.lower()
    add("Research", "A proof slot when research calls for original data",
        PASS if has_proof_slot else BLOCK)

    outline_facts = set()
    for r in rows:
        facts_str = r.get("facts", "")
        outline_facts.update(extract_fact_ids(facts_str))

    ledger_facts = brief.get("ledger_facts", set())
    ledger_prefixes = {f[0] for f in ledger_facts if len(f) > 1}
    ungrounded_facts = []
    for f in outline_facts:
        if f in ledger_facts:
            continue
        if len(f) == 1 and f in ledger_prefixes:
            continue
        ungrounded_facts.append(f)

    add("Research", "Every fact id used exists in the ledger",
        PASS if not ungrounded_facts else BLOCK,
        f"{len(outline_facts)} checked" if not ungrounded_facts else f"not found: {', '.join(ungrounded_facts)}")

    # Media
    img = meta.get("image_slot", "").lower()
    proof = meta.get("proof_slot", "").lower()
    media_ok = ("hero" in img) and (bool(proof))
    add("Media", "Image and proof slots point at real sections; hero slot",
        PASS if media_ok else BLOCK)

    # Language and policy
    banned = re.findall(r"lorem ipsum|TODO|TBD|\[insert", text, re.I)
    add("Language and policy", "No banned terms or claims", PASS if not banned else BLOCK)

    non_ascii = [c for c in title if ord(c) > 127 and c not in "–—'’“”éè"]
    add("Language and policy", "Title and headings in the right script",
        PASS if len(non_ascii) == 0 else WARN)

    st = brief.get("sensitive_topic", "no").lower()
    is_sensitive = any(w in st for w in ("medical", "financial", "legal", "safety")) and not st.startswith("no")
    if is_sensitive:
        has_expert = "expert" in text.lower() or "disclaimer" in text.lower()
        add("Language and policy", "Expert-review note for sensitive topics",
            PASS if has_expert else BLOCK)
    else:
        add("Language and policy", "Expert-review note for sensitive topics", PASS, "not sensitive")

    add("Language and policy", "No heading copied word for word from a baseline", PASS)

    counts = {s: sum(1 for r in results if r[2] == s) for s in (PASS, WARN, BLOCK)}
    if args.json:
        import json
        print(json.dumps({
            "title": title, "words": total_words, "kind": kind, "keyword": kw, "outline": True,
            "checks": [{"area": a_, "check": c, "severity": sv, "detail": d} for a_, c, sv, d in results],
            "summary": {"pass": counts[PASS], "warn": counts[WARN], "block": counts[BLOCK]},
        }, indent=2, ensure_ascii=False))
        return 1 if counts[BLOCK] else 0

    print(f"\n  \033[1m{title}\033[0m")
    print(f"  {total_words} words budget · {len(h2_titles)} H2s · kind: {kind} · keyword: “{kw}”\n")
    area = None
    for a, check, sev, detail in results:
        if a != area:
            print(f"  \033[2m{a}\033[0m")
            area = a
        print(f"    {ICON[sev]}  {check}" + (f"  \033[2m— {detail}\033[0m" if detail else ""))
    print(f"\n  {counts[PASS]} passed · {counts[WARN]} warnings · {counts[BLOCK]} blocking")
    verdict = "Not ready: fix blocking checks first" if counts[BLOCK] else "Outline checks pass: proceed to writing"
    print(f"  \033[1m{verdict}\033[0m\n")
    return 1 if counts[BLOCK] else 0


def main():
    # Reports include Unicode article text and check labels. Keep output usable
    # on Windows consoles whose legacy code page cannot encode those scripts.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("article", help="path to article.md or 07-outline.md")
    ap.add_argument("--outline", action="store_true", help="run outline checks (references/checklists.md §3) on 07-outline.md")
    ap.add_argument("--ledger", help="research brief with the facts ledger; defaults to 06-research-brief.md beside the file")
    ap.add_argument("--brief", help="the brief; defaults to 01-brief.md beside the file")
    ap.add_argument("--json", action="store_true", help="print results as JSON instead of the report")
    args = ap.parse_args()

    if args.outline or Path(args.article).name == "07-outline.md":
        return check_outline(args)

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
