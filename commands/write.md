---
description: Run the research-first article workflow from a keyword, saving an auditable run under articles/<slug> and stopping at the three human checkpoints.
argument-hint: <keyword> [--kind <blog|listicle|comparison|alternatives|faq|review>] [--market <country, language>]
---

# Write with research first

Run the existing `research-first-writer` skill end to end from the supplied arguments. This command is an explicit entry point to that skill; it is not a second writing method.

## Parse the arguments

Use the text after the command as `$ARGUMENTS`.

- The required keyword is the remaining text after removing the optional `--kind <kind>` and `--market <market>` options. Preserve the keyword's wording and language.
- Accepted kinds are `blog`, `listicle`, `comparison`, `alternatives`, `faq`, and `review`.
- Treat the value after `--market` as free text, so values such as `United States, English (en-US)` and `India, Hindi (hi-IN)` are valid.
- If the keyword is missing, ask for it and stop. If an option is malformed or the kind is unsupported, explain the expected syntax and stop.
- Do not ask again for a kind or market already supplied in the arguments.
- If brief information is missing, ask only the next small group of questions needed to complete the brief: goal and readers first, then kind-specific requirements, then tone/length/brand/first-hand notes. Skip anything already supplied and accept “none supplied” where appropriate.

Examples:

```text
/research-first-writer:write best crm for small business
/research-first-writer:write best crm for small business --kind listicle
/research-first-writer:write best crm for small business --market "United States, English (en-US)"
/research-first-writer:write best crm for small business --kind listicle --market "United States, English (en-US)"
```

## Create the run safely

1. Read `skills/research-first-writer/SKILL.md`, `references/templates.md`, and `references/checklists.md` before acting. Use those files as the methodology and validation source of truth.
2. Generate a lower-case hyphenated slug from the keyword. Use the repository's `skills/research-first-writer/scripts/new_run.py <slug> --dir articles` scaffold so the standard step files and templates are reused. The scaffold refuses to overwrite an existing directory; if `articles/<slug>/` already exists, stop and ask for explicit approval before changing it.
3. Complete and save the run as separate files in this order:

   `01-brief.md`, `02-discover.md`, `03-scores.md`, `pages.json`, `04-analysis.md`, `05-baselines.md`, `06-research-brief.md`, `07-outline.md`, `article.md`, `review-report.md`, and `README.md`.

4. Keep research in the reader's market and language. Search with real queries, fetch every page scored in `pages.json`, record the date read, use only verified quotes of 25 words or fewer, put every percentage/price/decimal in the facts ledger, and never invent first-hand experience. Use `[[NEEDS_HUMAN: ...]]` where proof or a human decision is required.
5. Preserve the context in the files: later steps must use the facts, gaps, baseline roles, and decisions recorded earlier. Do not replace research with a generic article or a product list unless the brief requires that format.

## Checkpoints

The command must stop and wait for explicit user approval at each checkpoint, even when the initial request asks for the whole article. On resume, inspect the saved files and continue from the next incomplete step rather than restarting.

- **Checkpoint 1 — after `02-discover.md`:** summarize the reader questions, queries, and candidate pages; list the files saved; explain that the next stage reads and scores the pages. Ask whether the direction and market are right, then stop.
- **Checkpoint 2 — after `05-baselines.md`:** summarize the scored pages and the role assigned to each selected baseline; list the files saved; explain that the next stage builds the research brief and facts ledger. Ask whether the baselines are right, then stop.
- **Checkpoint 3 — after `07-outline.md`:** summarize the must-covers, differentiators, title, sections, and word budgets; list the files saved; explain that the next stage writes, edits, checks, and judges the article. Ask whether the structure works, then stop.

Do not invent additional checkpoints and do not treat the final review as a checkpoint.

## Finish the run

After the user approves the third checkpoint, write and edit the article section by section. Run `skills/research-first-writer/scripts/check_article.py` against the saved article, fix blocking checks without weakening the rules, and run the page scorer against `pages.json`. Then write `review-report.md` using the existing review template and a `README.md` that records the keyword, kind, market, research date, files, validation commands, unresolved human work, and the final verdict.

Report the output directory, files created, checks run, warnings or `[[NEEDS_HUMAN]]` items, and whether the run is ready for a human read-through. Never claim that sources were fetched, tests passed, or a human approved a checkpoint unless that actually happened.
