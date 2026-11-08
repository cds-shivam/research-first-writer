---
name: no-generic-dump
type: regex
target: last_message
pattern: '(?i)(in today''s fast-paced world|delve into|game-changer|testament to|elevate your|harness the power)'
invert: true
weight: 1.0
---
Ensures the agent did not bypass research and immediately emit a generic article filled with standard AI filler stock phrases.
