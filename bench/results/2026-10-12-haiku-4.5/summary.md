| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| fix-test | baseline | 5 | 5/5 | $0.080 ($0.076-0.128) | 332.1k | 2.1k | 7 | 5.3% |
| fix-test | tokenleak | 5 | 5/5 | $0.093 ($0.081-0.131) | 430.7k | 2.2k | 9 | 4.9% |
| fix-test | guard | 5 | 5/5 | $0.086 ($0.077-0.111) | 386.0k | 2.3k | 8 | 5.2% |
| find-answer | baseline | 5 | 5/5 | $0.120 ($0.116-0.150) | 466.5k | 1.6k | 9 | 24.6% |
| find-answer | tokenleak | 5 | 5/5 | $0.117 ($0.103-0.202) | 366.8k | 1.5k | 8 | 26.1% |
| find-answer | guard | 5 | 5/5 | $0.110 ($0.101-0.117) | 627.7k | 2.4k | 13 | 7.6% |
| fix-build | baseline | 5 | 5/5 | $0.084 ($0.078-0.138) | 375.1k | 1.8k | 8 | 5.2% |
| fix-build | tokenleak | 5 | 5/5 | $0.081 ($0.068-0.086) | 375.1k | 1.7k | 8 | 5.3% |
| fix-build | guard | 5 | 5/5 | $0.087 ($0.078-0.119) | 425.6k | 1.9k | 9 | 5.5% |
| add-feature | baseline | 5 | 5/5 | $0.228 ($0.145-0.295) | 986.6k | 3.7k | 12 | 22.4% |
| add-feature | tokenleak | 5 | 5/5 | $0.214 ($0.131-0.263) | 948.1k | 3.9k | 15 | 22.1% |
| add-feature | guard | 5 | 5/5 | $0.124 ($0.115-0.143) | 733.3k | 4.0k | 16 | 3.6% |

**Sum of medians, tokenleak vs baseline**: cost $0.513 → $0.505 (-1%), context tokens 2.2M → 2.1M (-2%), output tokens 9.2k → 9.2k (-0%).
**Sum of medians, guard vs baseline**: cost $0.513 → $0.408 (-20%), context tokens 2.2M → 2.2M (+1%), output tokens 9.2k → 10.6k (+15%).
Median wall time per run: baseline 27s, tokenleak 28s, guard 37s.
Output share of cost (median per run, relative price units): baseline 9.6%, tokenleak 10.5%, guard 12.7%.
Passed: baseline 20/20, tokenleak 20/20, guard 20/20. Model: claude-haiku-4-5-20251001. Runs that tried to leave the repo: 0.
