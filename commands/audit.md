---
description: Audit an existing Markdown article with the rule checks first and the research-first judge second, returning the repository's review-report format.
argument-hint: <path/to/article.md>
---

# Audit an article with research first

Audit the Markdown article supplied after the command. This is an explicit entry point to the existing `research-first-writer` review workflow; do not invent a second audit methodology or scoring system.

## Validate the input

Use the text after the command as `$ARGUMENTS`.

- Require exactly one article path. If it is missing, ask for a path and stop. If extra arguments are present, explain the expected syntax and stop.
- Resolve the path from the current working directory, preserving spaces and quoted path segments. Do not treat user-provided path text as a shell fragment.
- Confirm that the resolved path exists, is a regular file, has a `.md` extension, and is readable. Report the exact problem and stop when any check fails.
- Do not overwrite the article or an existing report. Return the report in the response unless the user explicitly gives a new output path; if saving one, refuse to overwrite an existing file.

Example:

```text
/research-first-writer:audit articles/my-article/article.md
```

## Run automated checks first

Before making any qualitative judgement, run the repository's existing validator:

```bash
python3 skills/research-first-writer/scripts/check_article.py "<resolved article path>"
```

Use the supplied path as one argument so paths containing spaces work. Capture the actual stdout/stderr and exit status. A non-zero status is a validation failure, not a reason to claim that the article passed. If Python or the script cannot run, report the exact execution error and continue only with the qualitative review that remains safe.

The validator looks for `06-research-brief.md` and `01-brief.md` beside the article by default. If the article uses files elsewhere, pass explicit `--ledger` and/or `--brief` paths only when those files exist. Do not replace the validator with custom checks.

## Check the ledger and numerical claims

After the validator has run, inspect the files it used and the article itself.

- If `06-research-brief.md` is missing, say so explicitly. Do not treat the validator's missing-ledger result as a pass or skip number review.
- Identify every relevant numerical claim in the article: percentages, money, decimals, statistics, dates, quantities, and other factual numbers. Exclude numbers that are only part of the title/headings or ordinary prose where the existing number-grounding rules allow them.
- List each claim requiring human verification, with its article passage/location and a recommendation to add a vetted ledger fact, source URL, credited source, and a quote of 25 words or fewer—or remove/mark it with `[[NEEDS_HUMAN: ...]]`.
- When a ledger exists, compare every numerical claim with the ledger and brief. Flag claims with no matching support, inconsistent values, missing source URLs, or quotes that do not support the claim. A matching number alone is not verification.
- Never fabricate a source, value, quote, test result, or first-hand evidence.

## Perform the qualitative judge audit

Only after the automated validation and ledger review, read `skills/research-first-writer/SKILL.md`, `skills/research-first-writer/references/checklists.md`, and `skills/research-first-writer/references/templates.md` as needed. Apply the existing seven-dimension judge table and its existing pass gates. For every dimension, record:

- the assessment and score using the repository's criteria;
- quoted article evidence or a precise section/passage reference;
- the problem demonstrated by that evidence; and
- an actionable recommendation.

Keep automated check failures separate from editorial findings. If automated checks fail, report them honestly and still complete the judge review wherever the article is readable and the evidence is meaningful. Mark limitations and human-review requirements instead of guessing.

## Return the review report

Format the final response using the `Review report` template in `skills/research-first-writer/references/templates.md`, in this order:

```text
Verdict: Ready for a human read-through | Not ready — reasons first
What needs a person: each [[NEEDS_HUMAN]] item and where it goes; missing image; unresolved checks
At a glance: words vs target · sections · reading time · judge score · checks passed
Judge: overall, pass/fail, and per dimension: score — quoted evidence — issues
Must fix (most important first): section — problem — suggestion
Checks failing: id — severity — message
What it rests on: baselines and their roles; facts used with sources
```

Adapt the template only to add the automated validation summary, actual exit status, missing-ledger numerical-claim list, and limitations. Clearly label those additions. Do not report a passing verdict when `check_article.py` failed, the ledger claims remain unsupported, or the judge gates are not met. Do not silently overwrite an existing `review-report.md`.
