| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| chain | baseline | 5 | 5/5 | $0.289 ($0.253-0.338) | 1.4M | 5.2k | 23 | 16.6% |
| chain | compact | 5 | 5/5 | $0.460 ($0.308-0.495) | 1.1M | 5.1k | 21 | 8.6% |
| chain-long | baseline | 4 | 4/4 | $0.413 ($0.392-0.432) | 2.1M | 6.0k | 19 | 25.2% |
| chain-long | compact | 4 | 4/4 | $0.421 ($0.398-0.446) | 1.2M | 6.0k | 21 | 17.5% |

**Sum of medians, compact vs baseline**: cost $0.702 → $0.881 (+26%), context tokens 3.5M → 2.3M (-36%), output tokens 11.2k → 11.1k (-1%).
Median wall time per run: baseline 81s, compact 134s.
Output share of cost (median per run, relative price units): baseline 7.9%, compact 8.6%.
Passed: baseline 9/9, compact 9/9. Model: claude-haiku-4-5-20251001. Runs that tried to leave the repo: 0.
