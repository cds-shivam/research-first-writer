---
name: audit-quality-rubric
type: llm
model: claude-3-5-sonnet
weight: 2.0
---
Evaluate the completeness and rigor of the audit of examples/audit-a-weak-draft/draft.md.

### Expectations:
1. **Decisive Verdict**: The draft is unambiguously judged as failing and not ready for publication.
2. **Rule-Based Violations**: Flags the blocking issues identified by check_article.py (title missing keyword, slug formatting, extreme keyword stuffing, stock phrases like "in today's fast-paced world", thin word count of 239 vs 1800).
3. **Integrity Violations**: Explicitly catches fake testing claims ("We tested over 50 CRM tools") and unsourced statistics (87%, 23.8%, $25, etc.).
4. **Actionable Roadmap**: Explains how to rebuild the piece properly (briefing, SERP discovery, facts ledger, baseline analysis).

### Scoring:
- **Pass (1.0)**: Clear rejection citing rule violations, fake experience, and ungrounded numbers with constructive remediation.
- **Fail (0.0)**: Approves the draft, gives superficial stylistic praise, or overlooks the fake testing and unsourced numbers.
