---
name: identifies-ungrounded-numbers
type: regex
target: last_message
pattern: '(?i)(87%|23\.8%|\$25|28%|41%|ledger|grounding)'
weight: 1.0
---
Verifies that the audit catches the ungrounded statistics and numbers lacking ledger sources.
