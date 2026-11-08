---
name: audit-of-the-weak-draft
description: Tests whether the skill correctly audits examples/audit-a-weak-draft/draft.md, runs check_article.py, identifies blocking failures (fake testing, ungrounded numbers, stock phrases), and blocks publication.
runs: 3
max_turns: 8
timeout_seconds: 300
allowed_tools: [Skill, Read, Write, Bash]
tags: [audit, checker, grounding, honesty]
---
Audit examples/audit-a-weak-draft/draft.md — is it good enough to publish?
