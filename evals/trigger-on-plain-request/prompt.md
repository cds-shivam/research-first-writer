---
name: trigger-on-plain-request
description: Tests whether the skill naturally activates on a plain article request and starts the briefing workflow instead of dumping an unresearched draft.
runs: 3
max_turns: 6
timeout_seconds: 300
allowed_tools: [Skill, Read, Write, Bash, WebFetch, WebSearch]
tags: [trigger, brief, plain-request]
---
Write an article about Astro vs Next.js for a technical blog.
