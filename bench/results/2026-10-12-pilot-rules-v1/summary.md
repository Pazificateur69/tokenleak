| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| fix-test | baseline | 5 | 5/5 | $0.158 ($0.139-0.159) | 397.4k | 1.3k | 7 | 0.0% |
| fix-test | tokenleak | 5 | 5/5 | $0.149 ($0.137-0.158) | 397.3k | 1.1k | 7 | 0.0% |
| find-answer | baseline | 5 | 5/5 | $0.203 ($0.121-0.221) | 314.6k | 874 | 5 | 20.6% |
| find-answer | tokenleak | 5 | 5/5 | $0.181 ($0.137-0.262) | 460.8k | 1.2k | 8 | 6.0% |
| fix-build | baseline | 5 | 5/5 | $0.268 ($0.245-0.280) | 635.9k | 2.7k | 10 | 8.6% |
| fix-build | tokenleak | 5 | 5/5 | $0.152 ($0.149-0.167) | 397.8k | 1.1k | 7 | 0.0% |

**Sum of medians, tokenleak vs baseline**: cost $0.629 → $0.482 (-23%), context tokens 1.3M → 1.3M (-7%), output tokens 4.8k → 3.3k (-31%).
Median wall time per run: baseline 28s, tokenleak 25s.
Output share of cost (median per run, relative price units): baseline 8.3%, tokenleak 6.9%.
Passed: baseline 15/15, tokenleak 15/15. Model: claude-sonnet-5. Runs that tried to leave the repo: 2.
