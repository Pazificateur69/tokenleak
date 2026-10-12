| task | variant | pass | cost (median) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|
| fix-test | baseline | 5/5 | $0.080 | 332.1k | 2.1k | 7 | 5.3% |
| fix-test | tokenleak | 5/5 | $0.093 | 430.7k | 2.2k | 9 | 4.9% |
| find-answer | baseline | 5/5 | $0.120 | 466.5k | 1.6k | 9 | 24.6% |
| find-answer | tokenleak | 5/5 | $0.117 | 366.8k | 1.5k | 8 | 26.1% |
| fix-build | baseline | 5/5 | $0.084 | 375.1k | 1.8k | 8 | 5.2% |
| fix-build | tokenleak | 5/5 | $0.081 | 375.1k | 1.7k | 8 | 5.3% |
| add-feature | baseline | 5/5 | $0.228 | 986.6k | 3.7k | 12 | 22.4% |
| add-feature | tokenleak | 5/5 | $0.214 | 948.1k | 3.9k | 15 | 22.1% |

**Sum of medians** — cost: $0.513 → $0.505 (-1%), context tokens: 2.2M → 2.1M (-2%), output tokens: 9.2k → 9.2k (-0%). Passed: baseline 20/20, tokenleak 20/20. Model: claude-haiku-4-5-20251001. Runs that tried to leave the repo: 0.
