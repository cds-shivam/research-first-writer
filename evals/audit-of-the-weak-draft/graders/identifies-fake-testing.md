---
name: identifies-fake-testing
type: regex
target: last_message
pattern: '(?i)(we tested|our team found|in our testing|first-hand)'
weight: 1.0
---
Verifies that the audit flags the fake testing claims ("We tested over 50 CRM tools", "Our team found", "We tested it with a team of 12").
