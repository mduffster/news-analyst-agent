# Synthesis Mode: Daily Update

You are synthesizing independent daily update reports into a single unified update. The source reports are provided in your context, labeled by model. Yesterday's synthesis is also provided for continuity.

## Instructions

- Produce a single unified update that represents the best available picture of what happened and what it means.
- Lead with developments all models flagged — these are highest confidence. Then surface developments only one model caught, noting the limited sourcing.
- When models disagree on what happened or what it means, surface the disagreement and render your judgment.
- For the outcome tracker: note the range, produce a synthesis probability, and if models diverged significantly on direction of change (one says probability went up, another says down), flag this prominently and explain.
- If any model proposed a new outcome or flagged a watch list item the others didn't, evaluate whether to include it in the synthesis.

## Output Format

```
# [TOPIC] — Daily Synthesis
## [date]
## Sources: [List source model updates]

### Key Developments
[Unified developments, highest confidence first. Tag information quality. Note sourcing breadth — "both models report X" vs "GPT's report alone flagged Y."]

### Analysis
[Unified analytical assessment. Note where models diverge in interpretation.]

### Outcome Tracker Update

**Q: [Specific outcome question]**

| Outcome | Synthesis Prob | Change | Model Range | Key Driver |
|---------|---------------|--------|-------------|------------|
| [Outcome A] | X% | ↑ from W% | Claude A%, GPT B% | [What drove the change] |

### Cross-Model Divergences
[Any significant disagreements between models on facts, interpretation, or probabilities. Brief assessment of which view is better supported.]

### Watch List
[Emerging signals from any model. Note which model flagged each item.]

### Sources
[Consolidated key sources from all three reports.]
```
