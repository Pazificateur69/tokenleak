# Reproduce the benchmark

Every benchmark number in the README comes from a folder in [bench/results](bench/results). This page is how you rerun it on your own account and publish what you get, whether it agrees or not. A rerun that contradicts the README is the most useful kind.

## What you need

- Claude Code on your `PATH` as `claude`, logged in. Every run is a real `claude -p` session billed to that login.
- Python 3.8+ (stdlib only, nothing to install) and `bash` (the fixture repo has a `build.sh`).
- macOS, where the published runs were made. Linux should work wherever Claude Code's sandbox does; untested.
- A clone at a release tag, so your harness commit is one others can name:

```bash
git clone https://github.com/Pazificateur69/tokenleak && cd tokenleak
git checkout "$(git describe --tags --abbrev=0)"
git rev-parse --short HEAD   # your harness commit
```

Free dry check, no API call: `python3 bench/fixture.py /tmp/tl-fixture` writes the test repo and prints the expected answers.

## Run it

`bench/run.py --help` lists the flags: `--model`, `--runs` (per task and arm, default 3), `--tasks`, `--variants`, `--parallel` (default 3), `--max-turns` (default 40), `--timeout` (seconds per run, default 1200), `--workdir`, `--out`, `--summarize`, `--export`.

Always pass `--tasks`: the default is every task, including `marathon-1m` at about $5 a run. Pass full model ids, not aliases (aliases move to newer models); the `Model:` line of `summary.md` says what really ran. Keep `--out` outside the repo: the raw folder holds local paths.

**The rules A/B** (the README's Sonnet A/B, 4 tasks × 3 arms × 5 runs = 60 runs, about $13):

```bash
python3 bench/run.py --model claude-sonnet-5 --runs 5 \
  --tasks fix-test,find-answer,fix-build,add-feature \
  --variants baseline,tokenleak,guard --out /tmp/tl-raw/sonnet
```

Same command with `--model claude-haiku-4-5-20251001` for the Haiku table (about $7).

**The 1M compaction A/B** (2 arms × 4 runs, about $40):

```bash
python3 bench/run.py --model "sonnet[1m]" --runs 4 --max-turns 150 --timeout 3600 \
  --tasks marathon-1m --variants baseline,compact300 --out /tmp/tl-raw/1m
```

It needs the 1M-token window, which `--model "sonnet[1m]"` turns on (the published runs were `claude-sonnet-5[1m]` and reached 757k tokens of context). If the **baseline** records' `max_context` never passes 200k, the window wasn't on and the run measures something else; a compact300 run can legitimately stay under 200k. They also logged up to 65 turns, above the default `--max-turns 40`.

`python3 bench/run.py --summarize <dir>` rebuilds a folder's `summary.md` from its JSON records.

### Expected cost

Medians of `cost_usd` (Claude Code's API-equivalent cost per run) in the committed records, per task, summed over a pass. One pass = one run of each task, so `--runs N` costs about N × the sum of the arms you pick.

The four small tasks (`fix-test,find-answer,fix-build,add-feature`), one pass:

| model | baseline | tokenleak | guard | from |
|---|---|---|---|---|
| claude-sonnet-5 | $1.073 | $0.727 | $0.831 | [2026-10-12-sonnet-5](bench/results/2026-10-12-sonnet-5) |
| claude-haiku-4-5-20251001, batch 1 | $0.513 | $0.505 | $0.408 | [2026-10-12-haiku-4.5](bench/results/2026-10-12-haiku-4.5) |
| claude-haiku-4-5-20251001, batch 2 | $0.530 | | $0.379 | [2026-10-12-haiku-4.5-b2](bench/results/2026-10-12-haiku-4.5-b2) |

The long sessions, one run:

| model | task | baseline | compact (100k) | compact300 | from |
|---|---|---|---|---|---|
| claude-sonnet-5 | `marathon-1m` | $5.399 | | $4.555 | [2026-10-13-sonnet-5-1m-compaction](bench/results/2026-10-13-sonnet-5-1m-compaction) |
| claude-sonnet-5 | `chain` | $0.846 (1 run) | $1.292 | | [2026-10-13-sonnet-5-compaction](bench/results/2026-10-13-sonnet-5-compaction) |
| claude-haiku-4-5-20251001 | `chain` | $0.289 | $0.460 | | [2026-10-13-haiku-4.5-compaction](bench/results/2026-10-13-haiku-4.5-compaction) |
| claude-haiku-4-5-20251001 | `chain-long` | $0.413 | $0.421 | | same |
| claude-haiku-4-5-20251001 | `marathon` | $0.321 | $0.405 | | same |

There is no committed tokenleak or guard run of the long tasks yet, so no estimate for those. Runs vary: within one task and arm, the priciest committed run costs 1.04 to 4.2 times the cheapest (1.4x median). Use 5 runs per arm or more; one or two say little. Runs take about 25 to 50 s each on the small tasks and 4 to 5 min on `marathon-1m` (medians).

## How a run is isolated

- **Same repo every time.** `bench/fixture.py` generates it (deterministic: same files, same answers), into a fresh temp folder per run under `--workdir`.
- **None of your setup.** `claude -p` runs with `--setting-sources project --strict-mcp-config --disable-slash-commands`: no user settings, CLAUDE.md, plugins, skills or MCP servers.
- **Sandboxed.** `--permission-mode bypassPermissions`, but inside Claude Code's sandbox with no unsandboxed commands, reads denied on `~/Desktop`, `~/Documents`, `~/Downloads`, `~/Developer`, `~/.claude`, `~/.codex`, `~/.ssh` and `~/Library`, extra writes only to `/tmp`. Your personal files live elsewhere? Add them to `HOME_DIRS` in `bench/run.py` (same for every arm, so it doesn't bias the A/B). A run that reaches outside its repo anyway is counted in `summary.md` ("Runs that tried to leave the repo").
- **One difference per arm.** `tokenleak`: the rules, passed with `--append-system-prompt-file` (the `rules.md` written to `--out` from the current `SKILL.md`, i.e. what the plugin injects). `guard`: the rules plus the plugin's `PreToolUse` read guard. `compact` / `compact300`: Claude Code's own `autoCompactWindow` at 100000 / 300000. The other tools' arms (`--help` lists them) append that tool's skill text, pinned in [bench/competitors](bench/competitors).
- **Checked by a script, not by eye.** Tests pass with the test files unchanged, build passes with `build.sh` unchanged, the exact number, the feature working on two categories; see `check()` in `bench/run.py`.

Each run is also a normal Claude Code session saved in `~/.claude/projects`, so your own `tokenleak` audit will see it.

## Share your results

1. Export the raw folder once. This drops the work dir and transcript paths and rewrites `summary.md`:

```bash
python3 bench/run.py --export /tmp/tl-raw/sonnet bench/results/2026-10-20-sonnet-5-<your-github-handle>
grep -rl "$USER" bench/results/2026-10-20-sonnet-5-<your-github-handle>   # must print nothing
```

2. Either open a PR that adds only that folder, or zip it and attach it to a [Benchmark rerun](https://github.com/Pazificateur69/tokenleak/issues/new?template=benchmark-rerun.yml) issue. Give the model, arms, runs, tasks and harness commit, and say if you changed anything in `bench/`. Failed runs stay in: dropping them is how a benchmark lies.

## Measure it on your own sessions

The benchmark is four small tasks on a synthetic repo. What counts is your own work.

1. Note the day you installed tokenleak (plugin, rules in `AGENTS.md`, or a setting the audit recommended).
2. Work as usual for a week, at least. Don't run the benchmark in that week: its sessions land in your transcripts too.
3. Run (`tokenleak` is the CLI, or the curl one-liner from the README's [audit](README.md#the-audit) section):

```bash
tokenleak --compare 2026-10-06 --redact               # the table to paste
tokenleak --compare 2026-10-06 --json --redact > before-after.json
```

`--compare` takes a window of the same length before the date, so a week after install gives a week before vs a week after. `--share` and `--html` don't combine with `--compare`; the table is the shareable output. `--redact` hides commands, paths and project names; read what you paste anyway.

4. Post it with the [My before/after](https://github.com/Pazificateur69/tokenleak/issues/new?template=compare-result.yml) form: dates, agent, model, leak score and cost per call before and after, and anything else that changed that week (model, other tools, projects). The task mix differs between periods, so one report is a data point, not a verdict. No change, or worse, is worth reporting too.
