| task | variant | pass | cost (median) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|
| fix-test | baseline | 5/5 | $0.158 | 397.4k | 1.3k | 7 | 0.0% |
| fix-test | tokenleak | 5/5 | $0.149 | 397.3k | 1.1k | 7 | 0.0% |
| find-answer | baseline | 5/5 | $0.203 | 314.6k | 874 | 5 | 20.6% |
| find-answer | tokenleak | 5/5 | $0.181 | 460.8k | 1.2k | 8 | 6.0% |
| fix-build | baseline | 5/5 | $0.268 | 635.9k | 2.7k | 10 | 8.6% |
| fix-build | tokenleak | 5/5 | $0.152 | 397.8k | 1.1k | 7 | 0.0% |

**Sum of medians** — cost: $0.629 → $0.482 (-23%), context tokens: 1.3M → 1.3M (-7%), output tokens: 4.8k → 3.3k (-31%). Passed: baseline 15/15, tokenleak 15/15. Model: claude-sonnet-5. Runs that tried to leave the repo: 2.
