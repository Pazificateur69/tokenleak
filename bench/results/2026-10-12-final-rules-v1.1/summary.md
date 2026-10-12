| task | variant | pass | cost (median) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|
| fix-test | baseline | 5/5 | $0.140 | 338.5k | 1.2k | 6 | 0.0% |
| fix-test | tokenleak | 5/5 | $0.140 | 341.9k | 1.1k | 6 | 0.0% |
| find-answer | baseline | 5/5 | $0.206 | 315.5k | 928 | 5 | 20.5% |
| find-answer | tokenleak | 5/5 | $0.160 | 448.1k | 1.2k | 8 | 0.0% |
| fix-build | baseline | 5/5 | $0.267 | 682.7k | 2.5k | 10 | 8.9% |
| fix-build | tokenleak | 5/5 | $0.159 | 400.7k | 1.5k | 7 | 0.0% |
| add-feature | baseline | 5/5 | $0.459 | 945.9k | 3.2k | 10 | 20.6% |
| add-feature | tokenleak | 5/5 | $0.184 | 453.0k | 2.7k | 9 | 0.0% |

**Sum of medians** — cost: $1.072 → $0.643 (-40%), context tokens: 2.3M → 1.6M (-28%), output tokens: 7.8k → 6.5k (-17%). Passed: baseline 20/20, tokenleak 20/20. Model: claude-sonnet-5. Runs that tried to leave the repo: 1.
