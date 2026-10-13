# Benchmark

Everything tokenleak's numbers rest on: how the runs were made, every result with its run count and 95% confidence interval, the results that went against it, and what the numbers can't tell you. Each of the 286 published runs is a JSON file in [bench/results](bench/results); every interval below comes out of [bench/stats.py](bench/stats.py).

## In short

| what was tested | model | runs per task and arm | cost change | 95% CI | passed |
|---|---|---|---|---|---|
| `autoCompactWindow` 300000 on a 1M-context session | Sonnet 5 | 4 | **−16%** | −36% to −6% | 4/4 · 4/4 |
| the rules, four small tasks | Sonnet 5 | 10 | **−32%** | −42% to −20% | 40/40 · 40/40 |
| rules + read guard with outline (v1.5), four tasks, batch 2 | Haiku 4.5 | 5 | **−28%** | −35% to −13% | 20/20 · 20/20 |
| rules + read guard (v1.4), four tasks, batch 1 | Haiku 4.5 | 5 | −20% | −31% to −4% | 20/20 · 20/20 |
| the rules alone, four tasks, batch 1 | Haiku 4.5 | 5 | −1% | −20% to +21% | 20/20 · 20/20 |
| `autoCompactWindow` 100000 on short sessions | Haiku 4.5 | 3 to 5 | **+26%** | +8% to +38% | 12/12 · 12/12 |

Two things the intervals make plain:

- **On the four small tasks, one task carries a large share of the saving.** Drop `add-feature` and the rules save 19% on Sonnet (−36% to −14%), and the v1.4 read guard saves nothing on Haiku batch 1 (−0%, −18% to +12%).
- **An early auto-compact loses money on short sessions.** It paid on the one long-session test (1M context). On the short sessions (peaks of 83k to 126k tokens without it) it cost more every time but once, where it broke even (+2%).

## How the numbers are computed

- **Cost** is the API-equivalent cost of a run as Claude Code reports it (`total_cost_usd` from `claude -p --output-format json`). It is not what a subscription bills.
- **The metric** (here, in the README and in each folder's `summary.md`): for each arm, take the median cost per run of each task, then add those medians up over the tasks. The change is the variant's total against the baseline's. A median per task keeps one wild run from dominating; the sum weighs each task by what it costs.
- **The 95% confidence interval** is a bootstrap: resample the runs with replacement within each task and arm, recompute the metric, 10,000 times with a fixed seed (2026), and keep the middle 95%. `python3 bench/stats.py bench/results/<folder> baseline <variant> [--batch b1] [--from <folder>] [--field context_tokens]`; `python3 bench/stats.py --selftest` checks it on synthetic data.
- **"Without <task>"** drops the task with the largest saving in dollars, to show whether one task carries the result.
- **Treat the intervals as optimistic.** With 3 to 10 runs per arm, a percentile bootstrap tends to come out too narrow rather than too wide, and an arm with a single run contributes no spread at all. They separate the results that are clearly away from zero from the ones that aren't; they don't turn 5 runs into 50.

## Method

Every run is one `claude -p` session on a fresh copy of the same small repo, with the same prompt. Claude Code runs isolated from the machine: no user or global settings, CLAUDE.md, plugins, skills or MCP servers (`--setting-sources project --strict-mcp-config --disable-slash-commands`), and a sandbox that denies reads of personal folders such as `~/Documents`, `~/.claude` and `~/.ssh`. Every run is then checked by a script, not by the model.

The only difference between arms:

| arm | what it adds |
|---|---|
| `baseline` | nothing |
| `tokenleak` | the rules appended to the system prompt (`--append-system-prompt-file`), which is what the plugin injects at session start |
| `guard` | the rules, plus the plugin's PreToolUse hook on Read, which refuses whole reads of big files (from v1.5 the refusal includes an outline of the file with line numbers) |
| `compact` | Claude Code's own `autoCompactWindow` at 100000, the lowest it accepts; no rules |
| `compact300` | `autoCompactWindow` at 300000; no rules |

The exact rules used by each series are saved next to its runs (`rules*.md`).

The repo ([bench/fixture.py](bench/fixture.py)) is a small synthetic Python shop built to contain what leaks in real repos: a big data module (600 products), chatty tests, a build script whose output is long and noisy, a CSV of 2,400 orders, and for one task 36 large legacy modules.

| task | what the agent must do | how the script checks it |
|---|---|---|
| `fix-test` | fix the root cause of a failing test suite in the application code | `python3 -m unittest` passes, test files unchanged |
| `find-answer` | count the products in the heavy shipping tariff that are out of stock | the reply contains exactly the right number |
| `fix-build` | make `./build.sh` pass | the build passes with its full report, `build.sh` unchanged |
| `add-feature` | add `--category NAME` to `tools/report.py` | two categories filter correctly and the default report is unchanged. **Held out**: written before the rules' one round of changes (v1.1), never used to tune them |
| `chain` | the four tasks above in one session | all four checks, in the same repo |
| `chain-long` | read three big files in full, then `chain` | as `chain` |
| `marathon` | seven tasks in a row: the four, plus `--min-qty`, `--json`, and tests for the new options | every task checked, including the filters combined |
| `marathon-1m` | read all 36 legacy modules in full (one Read each), then `marathon`, then name the legacy file that defines a given function | as `marathon`, plus the right file |

## The rules and the read guard (four small tasks)

### Sonnet 5, 10 runs per task and arm, two batches

[Runs](bench/results/2026-10-12-sonnet-5). Median cost per run:

| task | runs | without | with the rules | change | 95% CI | passed |
|---|---|---|---|---|---|---|
| fix a failing test (chatty test logs) | 10 · 10 | $0.148 | $0.140 | −6% | −15% to +5% | 10/10 · 10/10 |
| answer a question about data in a big module | 10 · 10 | $0.205 | $0.160 | −22% | −28% to −18% | 10/10 · 10/10 |
| fix a build buried in noisy output | 10 · 10 | $0.270 | $0.206 | −24% | −55% to −14% | 10/10 · 10/10 |
| add a feature *(held out)* | 10 · 10 | $0.450 | $0.222 | −51% | −60% to −20% | 10/10 · 10/10 |
| **total** | 40 · 40 | **$1.073** | **$0.727** | **−32%** | −42% to −20% | 40/40 · 40/40 |
| total without add-feature | 30 · 30 | $0.623 | $0.505 | −19% | −36% to −14% | 30/30 · 30/30 |

Context tokens (summed medians): −17% (−27% to −2%). Output tokens: −11% (−20% to +1%).

By batch (runs tagged `b1` and `b2`, 5 per task and arm):

| batch | without | with the rules | change | 95% CI | without add-feature |
|---|---|---|---|---|---|
| b1 | $1.072 | $0.643 | −40% | −49% to −28% | −25% (−42% to −12%) |
| b2 | $1.074 | $0.851 | −21% | −45% to −4% | −18% (−50% to −1%) |

Rules + read guard, run in batch 2 only, against the batch 2 baseline: $1.074 → $0.831, **−23% (−41% to +10%)**, 20/20 passed both ways. By task: add-feature −46% (−56% to −10%), find-answer −16% (−55% to +80%), fix-build −2% (−54% to +43%), fix-test +0% (−70% to +83%); without add-feature, −6% (−40% to +33%). The guard did about as well as the rules alone in the same batch (−21%), but its interval includes no change at all. (`summary.md` shows −22% for the guard because it compares with both baseline batches pooled.)

### Haiku 4.5, batch 1: rules alone, and rules + read guard (v1.4)

[Runs](bench/results/2026-10-12-haiku-4.5), 5 per task and arm:

| task | without | rules only | rules + read guard (v1.4) |
|---|---|---|---|
| fix-test | $0.080 | $0.093: +16% (−28% to +64%) | $0.086: +7% (−33% to +38%) |
| find-answer | $0.120 | $0.117: −3% (−22% to +68%) | $0.110: −8% (−26% to −1%) |
| fix-build | $0.084 | $0.081: −4% (−41% to +6%) | $0.087: +4% (−37% to +42%) |
| add-feature | $0.228 | $0.214: −6% (−42% to +48%) | $0.124: −46% (−58% to −14%) |
| **total** | **$0.513** | **$0.505: −1% (−20% to +21%)** | **$0.408: −20% (−31% to −4%)** |
| total without add-feature | $0.284 | $0.291: +2% (−16% to +33%) | $0.283: −0% (−18% to +12%) |
| passed | 20/20 | 20/20 | 20/20 |

### Haiku 4.5, batch 2: read guard v1.4 vs v1.5 (with outline)

[Runs](bench/results/2026-10-12-haiku-4.5-b2); the v1.4 guard arm ran alongside batch 2 and is in [its own folder](bench/results/2026-10-12-haiku-4.5-b2-guard-v1.4) (`bench/stats.py ... --from`). 5 runs per task and arm:

| task | without | rules + guard v1.4 | rules + guard v1.5 (outline) |
|---|---|---|---|
| fix-test | $0.087 | $0.082: −6% (−12% to +5%) | $0.079: −9% (−15% to +2%) |
| find-answer | $0.116 | $0.086: −25% (−42% to +37%) | $0.077: −33% (−45% to −28%) |
| fix-build | $0.088 | $0.087: −1% (−16% to +14%) | $0.082: −7% (−17% to +0%) |
| add-feature | $0.239 | $0.141: −41% (−50% to −2%) | $0.141: −41% (−53% to −3%) |
| **total** | **$0.530** | **$0.396: −25% (−31% to −7%)** | **$0.379: −28% (−35% to −13%)** |
| total without add-feature | $0.291 | $0.256: −12% (−21% to +12%) | $0.238: −18% (−24% to −13%) |
| passed | 20/20 | 20/20 | 20/20 |

### The pilot: rules v1 on Sonnet 5

[Runs](bench/results/2026-10-12-pilot-rules-v1), three tasks, 5 runs per task and arm, before the rules were changed:

| task | without | rules v1 | change | 95% CI |
|---|---|---|---|---|
| fix-test | $0.158 | $0.149 | −6% | −14% to +9% |
| find-answer | $0.203 | $0.181 | −11% | −32% to +49% |
| fix-build | $0.268 | $0.152 | −43% | −46% to −38% |
| **total** | **$0.629** | **$0.482** | **−23%** | −30% to −6% |
| total without fix-build | $0.361 | $0.330 | −8% | −21% to +21% |

15/15 passed both ways.

## The auto-compact window

These arms add no rules: they only set Claude Code's own `autoCompactWindow`. In the four-task benchmark above, the cost Claude Code reports matches each run's recorded token usage exactly, at one fixed price per token type. With compaction it doesn't: the compaction summary calls (and, in two runs, a subagent) are billed but are not in the main session's record, so **context tokens below count the main session only, while cost counts everything**. In the compaction arms, 16% to 28% (Haiku), 31% to 40% (Sonnet, 100k) and 29% to 68% (Sonnet, 1M) of the reported cost is outside the main session's usage. Cost is the honest comparison.

### 1M context: Sonnet 5, `marathon-1m`, 4 runs per arm

[Runs](bench/results/2026-10-13-sonnet-5-1m-compaction). Read 36 large legacy modules, then seven tasks, then a question that needs what was read first.

| | runs | default | `autoCompactWindow` 300000 | change | 95% CI | passed |
|---|---|---|---|---|---|---|
| cost (median) | 4 · 4 | $5.399 | $4.555 | **−16%** | −36% to −6% | 4/4 · 4/4 |
| context tokens re-sent, main session (median) | 4 · 4 | 12.4M | 2.5M | −80% | −85% to −73% | |

- Every compact300 run cost less than the cheapest default run ($3.459 to $4.819, against $4.954 to $5.606).
- **Slower**: 315 s median against 245 s.
- Context peaked at 735k to 757k by default, and at 179k to 656k with the setting (see the 656k run below).
- **By batch** (2 runs per arm each, too few for an interval): batch 1 (runs 1 and 2) −26%, $5.26 → $3.90; batch 2 (runs 3 and 4) −11%, $5.42 → $4.80.
- **Batch 1 is not a clean test of the setting.** In both batch 1 compact300 runs, Sonnet handed most of the reading to a subagent, which no default run did; one of those two runs never compacted at all (peak 179k). Their subagents also re-sent 0.51M and 0.83M tokens of context that the context figure leaves out; counted in, the median is 2.7M and the change −78%. Batch 2, where Sonnet read everything itself and compacted 2 and 3 times, is the cleaner −11%.
- These sessions are 14 to 22 calls long, so each compaction weighs a lot. A real 1M session runs to hundreds of calls; that is what the audit's replay prices, not what was measured here.

#### Why one run reached 656k with the window at 300k

Run 4 (`marathon-1m--compact300--4.json`, session `bc983981`), from its transcript:

1. Its second API call (context 54k) asked for all 36 legacy reads at once: 36 Read calls in one response, one of them with a mistyped path that failed. Each successful read returned roughly 35k characters. Nothing happens between those reads: the first compaction comes only after all of them are in context.
2. Claude Code then auto-compacted. Its record: 346,219 tokens before, 292,868 after, 53,351 dropped, 54 s.
3. The next call carried **656,413 tokens** of context, the run's peak. The transcript doesn't say why that is more than twice Claude Code's own after-compaction count.
4. That call re-read the module whose read had failed. A second auto-compaction followed (665,710 → 13,987 tokens, 89 s), and from there to the end the context stayed between 76k and 136k.

The other batch 2 run read the same 36 modules in three calls of 12 and peaked at 264k. So the window can't stop a single call that pulls in hundreds of thousands of tokens at once. Even so, run 4 cost $4.777, less than every default run.

### Short sessions, at 100k: Haiku 4.5

[Runs](bench/results/2026-10-13-haiku-4.5-compaction):

| task | runs | default | `autoCompactWindow` 100000 | change | 95% CI | compactions per run | passed |
|---|---|---|---|---|---|---|---|
| `chain` (peak 83k–102k by default) | 5 · 5 | $0.289 | $0.460 | +59% | −2% to +90% | 2–3 | 5/5 · 5/5 |
| `chain-long` (peak 119k–123k) | 4 · 4 | $0.413 | $0.421 | +2% | −6% to +10% | 1 | 4/4 · 4/4 |
| `marathon` (peak 85k–89k) | 3 · 3 | $0.321 | $0.405 | +26% | +20% to +51% | 2 | 3/3 · 3/3 |
| **total** | 12 · 12 | $1.023 | $1.287 | **+26%** | +8% to +38% | | 12/12 · 12/12 |

Context re-sent (main session): `chain` −24% (−43% to −1%), `chain-long` −44% (−54% to −34%), `marathon` −20% (−23% to +9%). Wall time (medians): `chain` 81 s → 159 s, `chain-long` 83 s → 129 s, `marathon` 101 s → 168 s. Each compaction took 20 to 48 s (median 30 s, 23 compactions, from the run transcripts).

### Short sessions, at 100k: Sonnet 5

[Runs](bench/results/2026-10-13-sonnet-5-compaction), `chain` only, **1 run without and 3 with**: $0.846 → $1.292 (+53%), context re-sent 1.56M → 0.75M (−52%), wall time 83 s → 353 s, 1/1 and 3/3 passed with 2 to 3 compactions. With a single baseline run, no interval is worth printing.

### Quality under compaction

Every compaction run passed every check: 12/12 Haiku at 100k with 1 to 3 compactions mid-task, 3/3 Sonnet at 100k, 4/4 Sonnet at 300k on 1M, as did every run without the setting.

### How well the audit's replay predicted these

The audit replays your own sessions with an earlier auto-compact (`tokenleak compact`). It charges every extra compaction its summary call (the whole context read uncached, 4k tokens written), 15k tokens of fresh summary and kept turns, and 10k of re-reads. When it was calibrated on the three Haiku series it predicted +60% (measured +59%) for `chain`, +46% (measured +2%) for `chain-long` and +36% (measured +26%) for `marathon`: it errs against compacting. Today's replay code, run on the same baseline transcripts, gives +58%, +41% and +36%. Those transcripts hold local paths and aren't published, so this check can't be redone from `bench/results` alone.

## What went against tokenleak

- **The rules alone did nothing on Haiku 4.5**: −1% (−20% to +21%), and +16% on `fix-test`. Haiku didn't follow them on its own; the read guard (which stops whole reads of big files) is what moved Haiku. That's why the plugin ships with the guard on.
- **On Sonnet the guard added nothing measurable over the rules**: −23% (−41% to +10%) in batch 2, against −21% for the rules alone in the same batch.
- **`fix-test` barely moved on Sonnet**: −6% (−15% to +5%).
- **Haiku batch 1, rules + guard, without add-feature: −0%** (−18% to +12%).
- **Compacting early cost more on short sessions**: +59%, +26% and +2% on Haiku, +53% on Sonnet, and it made runs 1.6 to 2x slower on Haiku and over 4x slower on Sonnet (median wall time).
- **Speed is mixed.** A refused read costs a round-trip. Median wall time per run: Sonnet 35 s without, 31 s with the rules, 38 s with rules + guard; Haiku batch 1 went from 27 s to 37 s with the guard, batch 2 from 32 s to 29 s (v1.5) and 33 s (v1.4).

## Read it honestly

- **Runs vary a lot.** Single runs of the same task and arm swing by up to 4x (Sonnet without the rules: `fix-test` $0.126 to $0.525, `find-answer` $0.096 to $0.387). The two Sonnet batches, run the same day, gave −40% and −21%. Read every figure here as a range.
- **One task carries a lot.** `add-feature` is the held-out task and shows the biggest gain, which argues against tuning to the test; it also means the totals lean on it.
- **The outline is a small gain, not a big one.** In batch 2 both guards ran side by side: −28% with the outline, −25% without, mostly on the data question (9 API calls instead of 12, $0.077 vs $0.086). The two intervals (−31% to −7%, −35% to −13%) overlap widely. It ships because it saves a search round-trip when the agent knows what it's looking for.
- **One task was re-run.** In Haiku batch 2, `fix-build` first failed in every arm alike (3/5 each) because the sandbox blocked Apple's Python bytecode cache in `~/Library`. The harness now points that cache inside the run's folder, and the 15 `fix-build` runs were redone for all three arms; the tables use the redone runs. The first runs aren't published.
- **Tuning was kept apart from testing.** The rules were piloted first (v1, 30 runs: −23%) and changed once: one new rule (compute, don't read data) and two additions (check a file's size first; chain shell steps). `add-feature` was written before that change and never used to tune them.
- **The checker got stricter after the fact.** In October 2026 the `add-feature` check gained a second category and a check that the default report is unchanged; all 55 published `add-feature` runs were re-checked against it and still pass.
- **Six runs were flagged as reaching outside their repo** (blocked by the sandbox): 2 pilot runs with the rules, and on Sonnet 2 runs without and 2 with. All six passed.
- **Small and synthetic.** Four small tasks on a repo built to contain the leaks tokenleak targets, one or two models, 1 to 10 runs per arm (one series has a single baseline run). It shows the mechanism works on that repo; it doesn't predict your saving. Run the audit on your own sessions before and after (`tokenleak --compare`).

## Reproduce

```bash
python3 bench/run.py --runs 5 --tasks fix-test,find-answer,fix-build,add-feature --variants baseline,tokenleak,guard   # 60 runs on Sonnet: about $15 of API-equivalent usage
python3 bench/stats.py bench/results/<new folder> baseline tokenleak
```

The intervals in this file:

```bash
python3 bench/stats.py bench/results/2026-10-12-sonnet-5 baseline tokenleak [--batch b1|b2] [--field context_tokens|output_tokens]
python3 bench/stats.py bench/results/2026-10-12-sonnet-5 baseline guard --batch b2
python3 bench/stats.py bench/results/2026-10-12-haiku-4.5 baseline tokenleak     # and: baseline guard
python3 bench/stats.py bench/results/2026-10-12-haiku-4.5-b2 baseline guard
python3 bench/stats.py bench/results/2026-10-12-haiku-4.5-b2 baseline guard --from bench/results/2026-10-12-haiku-4.5-b2-guard-v1.4
python3 bench/stats.py bench/results/2026-10-12-pilot-rules-v1 baseline tokenleak
python3 bench/stats.py bench/results/2026-10-13-haiku-4.5-compaction baseline compact [--field context_tokens]
python3 bench/stats.py bench/results/2026-10-13-sonnet-5-compaction baseline compact
python3 bench/stats.py bench/results/2026-10-13-sonnet-5-1m-compaction baseline compact300 [--field context_tokens]
```
