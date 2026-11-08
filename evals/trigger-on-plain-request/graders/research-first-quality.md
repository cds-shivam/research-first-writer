---
name: research-first-quality
type: llm
model: claude-3-5-sonnet
weight: 2.0
---
Evaluate whether the assistant followed the research-first article methodology on a plain article request.

### Expectations:
1. **Triggering**: The assistant recognizes that writing a quality technical comparison requires a research-first approach rather than instantaneous generation.
2. **Briefing checkpoint**: The assistant pauses at Step 1 (Brief) to determine the audience, goal, tone, word budget, and whether any first-hand testing notes or benchmark data exist.
3. **No Hallucinated Benchmarks**: The assistant does not invent synthetic performance metrics or write an ungrounded comparison article without research.

### Scoring:
- **Pass (1.0)**: Assistant halts to collect the brief or initiate structured research before drafting.
- **Fail (0.0)**: Assistant immediately writes an ungrounded draft without asking for briefing details or research baselines.
