---
name: blocks-publication
type: regex
target: last_message
pattern: '(?i)(not (ready|good enough)|cannot (be|publish)|not publishable|blocking|fix blocking|fails?)'
weight: 1.0
---
Verifies that the audit clearly states the draft is not ready to publish.
