| task | variant | runs | pass | cost: median (range) | context tokens (median) | output tokens (median) | API calls (median) | leak score (median) |
|---|---|---|---|---|---|---|---|---|
| chain | baseline | 5 | 5/5 | $0.289 ($0.253-0.338) | 1.4M | 5.2k | 23 | 16.6% |
| chain | compact | 5 | 5/5 | $0.460 ($0.308-0.495) | 1.1M | 5.1k | 21 | 8.6% |
| marathon | baseline | 3 | 3/3 | $0.321 ($0.279-0.335) | 1.8M | 7.0k | 28 | 15.5% |
| marathon | compact | 3 | 3/3 | $0.405 ($0.403-0.419) | 1.5M | 7.8k | 29 | 2.9% |
| chain-long | baseline | 4 | 4/4 | $0.413 ($0.392-0.432) | 2.1M | 6.0k | 19 | 25.2% |
| chain-long | compact | 4 | 4/4 | $0.421 ($0.398-0.446) | 1.2M | 6.0k | 21 | 17.5% |

**Sum of medians, compact vs baseline**: cost $1.023 → $1.287 (+26%), context tokens 5.4M → 3.7M (-30%), output tokens 18.2k → 18.9k (+3%).
Median wall time per run: baseline 88s, compact 150s.
Output share of cost (median per run, relative price units): baseline 8.5%, compact 9.3%.
Passed: baseline 12/12, compact 12/12. Model: claude-haiku-4-5-20251001. Runs that tried to leave the repo: 0.
