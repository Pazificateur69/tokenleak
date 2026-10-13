| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| marathon-1m | baseline | 4 | 4/4 | $5.399 ($4.954-5.606) | 12.4M | 12.9k | 18 | 32.4% |
| marathon-1m | compact300 | 4 | 4/4 | $4.555 ($3.459-4.819) | 2.5M | 13.7k | 18 | 13.5% |

**Sum of medians, compact300 vs baseline**: cost $5.399 → $4.555 (-16%), context tokens 12.4M → 2.5M (-80%), output tokens 12.9k → 13.7k (+6%).
Median wall time per run: baseline 245s, compact300 315s.
Output share of cost (median per run, relative price units): baseline 2.4%, compact300 6.1%.
Passed: baseline 4/4, compact300 4/4. Model: claude-sonnet-5. Runs that tried to leave the repo: 0.
