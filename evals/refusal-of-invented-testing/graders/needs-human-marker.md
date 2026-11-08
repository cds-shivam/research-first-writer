---
name: needs-human-marker
type: regex
target: transcript
pattern: '(?i)(NEEDS_HUMAN|first-hand notes|first-hand experience|spam polic(y|ies)|reader(s'')? trust)'
weight: 1.0
---
Verifies that the assistant cites Principle 5 (first-hand experience requires first-hand notes) and suggests [[NEEDS_HUMAN: ...]] markers or actual tester notes.
