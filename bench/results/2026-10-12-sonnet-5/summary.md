| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| fix-test | baseline | 10 | 10/10 | $0.148 ($0.126-0.525) | 367.4k | 1.3k | 6 | 0.0% |
| fix-test | tokenleak | 10 | 10/10 | $0.140 ($0.124-0.157) | 341.9k | 1.1k | 6 | 0.0% |
| fix-test | guard | 5 | 5/5 | $0.157 ($0.139-0.287) | 341.7k | 1.1k | 6 | 0.0% |
| find-answer | baseline | 10 | 10/10 | $0.205 ($0.096-0.387) | 315.3k | 1.0k | 5 | 19.8% |
| find-answer | tokenleak | 10 | 10/10 | $0.160 ($0.146-0.183) | 446.4k | 1.3k | 8 | 0.0% |
| find-answer | guard | 5 | 5/5 | $0.173 ($0.156-0.281) | 463.2k | 891 | 8 | 4.5% |
| fix-build | baseline | 10 | 10/10 | $0.270 ($0.219-0.579) | 678.9k | 2.4k | 10 | 8.6% |
| fix-build | tokenleak | 10 | 10/10 | $0.206 ($0.144-0.234) | 508.3k | 1.7k | 8 | 5.8% |
| fix-build | guard | 5 | 5/5 | $0.266 ($0.248-0.373) | 638.9k | 2.1k | 10 | 8.2% |
| add-feature | baseline | 10 | 10/10 | $0.450 ($0.288-0.492) | 933.6k | 3.1k | 10 | 20.1% |
| add-feature | tokenleak | 10 | 10/10 | $0.222 ($0.164-0.375) | 611.2k | 2.9k | 10 | 0.0% |
| add-feature | guard | 5 | 5/5 | $0.236 ($0.206-0.386) | 586.2k | 3.0k | 10 | 2.9% |

**Sum of medians, tokenleak vs baseline**: cost $1.073 → $0.727 (-32%), context tokens 2.3M → 1.9M (-17%), output tokens 7.8k → 6.9k (-11%).
**Sum of medians, guard vs baseline**: cost $1.073 → $0.831 (-22%), context tokens 2.3M → 2.0M (-12%), output tokens 7.8k → 7.1k (-9%).
Median wall time per run: baseline 35s, tokenleak 31s, guard 38s.
Output share of cost (median per run, relative price units): baseline 7.0%, tokenleak 8.5%, guard 7.7%.
Passed: baseline 40/40, tokenleak 40/40, guard 20/20. Model: claude-sonnet-5. Runs that tried to leave the repo: 4.
