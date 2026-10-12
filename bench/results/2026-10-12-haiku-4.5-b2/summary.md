| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| fix-test | baseline | 5 | 5/5 | $0.087 ($0.078-0.093) | 382.5k | 2.3k | 8 | 5.0% |
| fix-test | guard | 5 | 5/5 | $0.079 ($0.078-0.088) | 375.7k | 2.0k | 8 | 5.2% |
| find-answer | baseline | 5 | 5/5 | $0.116 ($0.107-0.138) | 465.6k | 1.5k | 9 | 26.2% |
| find-answer | guard | 5 | 5/5 | $0.077 ($0.067-0.081) | 410.9k | 1.6k | 9 | 5.5% |
| fix-build | baseline | 5 | 5/5 | $0.088 ($0.083-0.097) | 455.7k | 2.1k | 10 | 4.8% |
| fix-build | guard | 5 | 5/5 | $0.082 ($0.074-0.088) | 376.9k | 1.6k | 8 | 5.0% |
| add-feature | baseline | 5 | 5/5 | $0.239 ($0.144-0.263) | 1.1M | 3.7k | 13 | 22.9% |
| add-feature | guard | 5 | 5/5 | $0.141 ($0.112-0.162) | 834.7k | 3.8k | 18 | 2.9% |

**Sum of medians, guard vs baseline**: cost $0.530 → $0.379 (-28%), context tokens 2.4M → 2.0M (-17%), output tokens 9.6k → 8.9k (-7%).
Passed: baseline 20/20, guard 20/20. Model: claude-haiku-4-5-20251001. Runs that tried to leave the repo: 0.
