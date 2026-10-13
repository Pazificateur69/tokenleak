| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| chain | baseline | 5 | 5/5 | $0.289 ($0.253-0.338) | 1.4M | 5.2k | 23 | 16.6% |
| chain | compact | 5 | 5/5 | $0.460 ($0.308-0.495) | 1.1M | 5.1k | 21 | 8.6% |

**Sum of medians, compact vs baseline**: cost $0.289 → $0.460 (+59%), context tokens 1.4M → 1.1M (-24%), output tokens 5.2k → 5.1k (-3%).
Median wall time per run: baseline 81s, compact 159s.
Output share of cost (median per run, relative price units): baseline 8.9%, compact 8.6%.
Passed: baseline 5/5, compact 5/5. Model: claude-haiku-4-5-20251001. Runs that tried to leave the repo: 0.
