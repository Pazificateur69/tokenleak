| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| chain | baseline | 1 | 1/1 | $0.846 ($0.846-0.846) | 1.6M | 5.3k | 14 | 18.1% |
| chain | compact | 3 | 3/3 | $1.292 ($1.091-1.393) | 748.8k | 5.4k | 12 | 0.0% |

**Sum of medians, compact vs baseline**: cost $0.846 → $1.292 (+53%), context tokens 1.6M → 748.8k (-52%), output tokens 5.3k → 5.4k (+2%).
Median wall time per run: baseline 83s, compact 353s.
Output share of cost (median per run, relative price units): baseline 6.3%, compact 6.9%.
Passed: baseline 1/1, compact 3/3. Model: claude-sonnet-5. Runs that tried to leave the repo: 0.
