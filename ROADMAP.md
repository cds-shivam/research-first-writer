# Roadmap

The goal: **the most trusted open method for writing articles with AI**, one that people fork to build their own content agents.

Status key: ✅ done · 🚧 in progress · 🔜 next · 💡 idea, open for discussion. Want something? 👍 the issue or open one. Items marked **good first issue** are a good place to start.

---

## v0.1: Open-source release ✅ (November 2026)

- ✅ The method as a portable skill: `SKILL.md`, checklists and templates
- ✅ Claude Code plugin and marketplace manifests (`/plugin install`)
- ✅ `check_article.py`: rule-based draft checks, including number grounding and fake first-hand claims
- ✅ `score_pages.py`: transparent page scoring with coverage
- ✅ 3 full example runs (blog, listicle, comparison) plus a weak-draft audit, all step files included
- ✅ Real-run screenshots, reproducible with `docs/render_screenshots.py`
- ✅ CI that runs the checks on every example

## v0.2: Easier to use 🔜

- ✅ Slash command: `/research-first-writer:write <keyword>` (with optional `--kind` and `--market`)
- 🔜 `check_article.py --outline` for the outline checks (section 3 of the checklists)
- ✅ `--json` output from both scripts, for pipelines and dashboards
- ✅ `new_run.py` scaffold that creates `articles/<slug>/01-brief.md … 07-outline.md` from the templates
- 🔜 An example run for each remaining kind: **FAQ**, **review**, **alternatives** (**good first issue**: pick a keyword you know)
- 🔜 A short GIF or asciinema of a full run for the README

## v0.3: Provably better 💡

- ✅ **An eval suite** (`claude plugin eval`): does the skill trigger on "write an article about X"? Does it refuse to write "we tested" without notes? Does every number reach the ledger? Scored runs and plain-markdown graders in `evals/`.
- ✅ **An originality checker**: verbatim runs (block at 14 words, warn at 10) and shared 5-word phrases against the pages read, with credited-quote and required-FAQ exemptions
- 💡 **A citation verifier**: re-fetch each ledger URL and confirm the quote still appears; flag link rot and changed prices
- 💡 A benchmark: the same 10 keywords, with and without the skill, scored by the judge rubric, results published

## v0.4: More markets and formats 💡

- 💡 Examples in German, Spanish, Hindi and Japanese (research in each market, not translation)
- 💡 Language rules for the checker: script detection, spelling variants, reading ease per language
- 💡 Output adapters: clean CMS HTML, WordPress block markup, Astro/Next MDX front matter, and JSON-LD (Article, FAQPage)

## v1.0: A reference implementation 💡

- 💡 An optional MCP server exposing `score_pages`, `check_article` and `verify_ledger` as tools for any agent
- 💡 Optional SERP and engagement data sources (bring your own API key), still reported with coverage, never guessed
- 💡 An AI-citation signal: track whether pages are cited in answer engines, feeding the `ai_citation` bonus
- 💡 Stable file formats (brief, ledger, outline) documented as a small spec others can build on

## Not planned

- Auto-publishing. "Ready" will always mean ready for a human read-through.
- Spinning, paraphrasing competitors, or bulk-generating thin pages.
- Paid-only features. The method and the tools stay MIT.

---

Have an idea that isn't here? Open a [feature request](https://github.com/jayanti-prajapati/research-first-writer/issues/new?template=feature_request.md).
