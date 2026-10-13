| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| marathon-1m | baseline | 2 | 2/2 | $5.262 ($4.954-5.571) | 11.3M | 12.9k | 17 | 31.9% |
| marathon-1m | compact300 | 2 | 2/2 | $3.896 ($3.459-4.333) | 2.5M | 13.1k | 17 | 17.0% |

**Sum of medians, compact300 vs baseline**: cost $5.262 → $3.896 (-26%), context tokens 11.3M → 2.5M (-77%), output tokens 12.9k → 13.1k (+2%).
Median wall time per run: baseline 245s, compact300 255s.
Output share of cost (median per run, relative price units): baseline 2.4%, compact300 8.0%.
Passed: baseline 2/2, compact300 2/2. Model: claude-sonnet-5. Runs that tried to leave the repo: 0.
