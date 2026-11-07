---
name: checker-executed
type: regex
target: transcript
pattern: '(?i)(check_article\.py|blocking (checks?|failures?)|rule checker)'
weight: 1.0
---
Verifies that check_article.py was executed or its automated rule checks were applied.
