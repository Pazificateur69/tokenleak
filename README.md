<p align="center"><img src="https://raw.githubusercontent.com/Pazificateur69/tokenleak/main/assets/logo.png" width="96" alt="tokenleak logo"></p>

<h1 align="center">tokenleak</h1>

<p align="center"><b>Find and plug your coding agent's token leaks.</b><br>
Not leaked API keys: the tokens your AI agent burns on context it didn't need.</p>

<p align="center">
<a href="https://github.com/Pazificateur69/tokenleak/actions/workflows/test.yml"><img src="https://github.com/Pazificateur69/tokenleak/actions/workflows/test.yml/badge.svg" alt="tests"></a>
<a href="https://www.skillsdirectory.com/skills/pazificateur69-tokenleak"><img src="https://www.skillsdirectory.com/api/skills/pazificateur69-tokenleak/badge" alt="Security: A on Skills Directory"></a>
<a href="https://pypi.org/project/tokenleak/"><img src="https://img.shields.io/pypi/v/tokenleak" alt="PyPI"></a>
<img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="zero dependencies">
<img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license">
</p>

<p align="center">
<a href="https://pazificateur69.github.io/tokenleak/">Website</a> · <a href="#install">Install</a> · <a href="#the-audit">Audit</a> · <a href="#benchmark">Benchmark</a> · <a href="#the-rules">Rules</a> · <a href="https://github.com/Pazificateur69/tokenleak/blob/main/README.fr.md">Français</a>
</p>

<p align="center"><img src="https://raw.githubusercontent.com/Pazificateur69/tokenleak/main/assets/stack.svg" alt="Animation: a 12k-token test log read at call 3 is re-sent by every later call (252,000 tokens); with tokenleak it is bounded to 800 tokens (16,800)." width="900"></p>

**tokenleak's rules cut Claude Code's cost by 32% on Sonnet 5** (40 runs per arm, 95% CI −42% to −20%, 40/40 passed in both arms; −19% without the task that gained most). Small, synthetic tasks: [BENCHMARK.md](https://github.com/Pazificateur69/tokenleak/blob/main/BENCHMARK.md) has every number with its interval, including the ones that went the other way.

**Try it first, nothing to install:** see where your own tokens went (Python 3.8+, stdlib only, reads your local transcripts, sends nothing). The script is pinned to a release; check its hash before running it:

```bash
curl -fsSLO https://raw.githubusercontent.com/Pazificateur69/tokenleak/v1.9.0/skills/tokenleak/scripts/tokenleak.py
shasum -a 256 tokenleak.py   # 983cd19a96327d13d75d9fc13bbf75f6ea67e90369dcebe4629dab96e7612b70
python3 tokenleak.py --since 7d
```

## Why

In an agent loop, **every tool result you let into context is re-sent on every later call** until the context is compacted. A 6k-token test log read at call 5 of a 60-call session gets paid ~55 more times. Every extra round-trip re-sends the whole context.

So the bill isn't driven by how chatty the agent is. It's driven by **what it lets into its context, and how early**. In the [benchmark](#benchmark)'s runs without tokenleak, everything the model wrote (replies, tool calls, thinking) was 7% of a run's cost on Sonnet and 10 to 11% on Haiku (medians); the rest was context. Shorter replies save the small part. The audit shows that split on your own sessions.

tokenleak does two things:

1. **Rules** (a skill, ~770 tokens) that make any coding agent let in only what the next decision needs: locate then read, compute instead of reading data, bound every command's output, never re-read, batch independent calls, diffs over files, edit don't rewrite. With guardrails, so it never saves tokens by guessing or skipping verification.
2. **An audit** that reads *your own* Claude Code and Codex transcripts and shows where the tokens actually went: every oversized read, noisy log, wasted call and serial round-trip, priced by the **context tax** it imposed, with the rule that fixes it. Local, read-only, zero dependencies.

## Long sessions: the setting that matters most

On a 1M-token context window, Claude Code auto-compacts only near the limit. Until then everything stays in context and is re-sent on every call: file reads, logs, and the model's own output. That last part is easy to miss: after a call that writes a lot, the next call's context grows by about as much (1.04x, measured over 1,977 such calls in the author's sessions), so thinking, replies and tool calls are re-sent too. In the author's last 30 days of sessions, they were 42% of everything re-sent, about twice all tool results together (20%), and 65% of calls carried more than 200k tokens of context.

Claude Code has a native setting for exactly this, `autoCompactWindow`; tokenleak doesn't change how compaction works, it tells you whether and where to set it. The audit replays your own sessions with an earlier auto-compact and tells you what it would have saved. On the author's last 30 days:

```
  context window  65% of calls carried over 200k tokens of context (max 998.0k)
  replayed on these sessions: "autoCompactWindow": 300000 → -24% cost (109 more compactions)
```

- **Measured live in the 1M regime.** Sonnet 5 with the 1M window, 4 runs per arm in two batches: read 36 large legacy modules, then seven tasks, then a question that needs what was read first. Default: context up to 757k, $5.40 median. With `autoCompactWindow` 300000: **$4.55 median (−16%, 95% CI −36% to −6%)**, context re-sent in the main session −80% (12.4M → 2.5M tokens; −78% counting the first batch's subagents), 4/4 passed in both arms, slower (315 s vs 245 s median). By batch: −26% when Sonnet handed the bulk read to a subagent (first batch, both runs), −11% when it read everything itself and compacted 2 to 3 times (second batch). These sessions are ~20 calls long, so compactions weigh a lot; the hundreds of calls of a real 1M session are what the replay prices. [Runs](https://github.com/Pazificateur69/tokenleak/blob/main/bench/results/2026-10-13-sonnet-5-1m-compaction).
- **Measured live, and it only pays on long sessions.** A session that jumps past 100k early (read three big files, then the four benchmark tasks; Haiku 4.5, 4 runs per arm): one compaction cut the context re-sent by 44% (2.1M → 1.2M tokens), 4/4 passed in both arms, cost even (+2%). Sessions that stay under ~90k (seven tasks in ~28 calls, 3 runs per arm): two compactions, 3/3 passed, but +26% cost. On the hundreds of calls of a long 1M session the saving is what the replay computes; on short ones it is a loss, and the replay says so.
- **Calibrated on those runs; it matches or errs against compacting.** The replay charges every extra compaction its summary call (the whole context read uncached, 4k written), 15k of fresh summary and kept turns, and 10k of re-reads. On the three measured series it predicted +58% (real +59%), +41% (real +2%) and +36% (real +26%); the transcripts it ran on are local, not published.
- **Quality held under the harshest setting.** `autoCompactWindow` at 100k, the lowest Claude Code accepts, with 1 to 3 compactions mid-task: 12/12 Haiku 4.5 runs and 3/3 Sonnet 5 runs passed every check, as did every run without it. Runs: [Haiku](https://github.com/Pazificateur69/tokenleak/blob/main/bench/results/2026-10-13-haiku-4.5-compaction), [Sonnet](https://github.com/Pazificateur69/tokenleak/blob/main/bench/results/2026-10-13-sonnet-5-compaction).
- **It is not free on short sessions.** On the short `chain` task compacting cost +59% and doubled the wall time: compactions took 20 to 48 s on Haiku (median 30 s over 23 compactions, read from the transcripts) and 54 and 89 s for the two of one Sonnet 1M run, and its summary call never shows up in the transcript. So the audit only recommends a value when your own sessions say it pays (5% or more), and picks the largest one within 2 points of the best, to compact as rarely as possible.

A plugin can't turn it on for you: Claude Code only lets a plugin ship the `agent` and `subagentStatusLine` settings. So tokenleak tells you (the audit, and a weekly note at session start when your sessions show a gain of 10% or more) and applies it only when you ask. `tokenleak compact` prints the full replay table for your sessions; `tokenleak compact --apply` writes the recommended value to `~/.claude/settings.json` (with a backup). Or set it yourself with `/config` → Auto-compact window.

## Install

**Claude Code (plugin, recommended).** Rules injected at session start, after compaction, and into every subagent, plus a **read guard**: a whole-file read of a big text file (over ~24 KB) is stopped, and for code and Markdown the agent gets the file's outline instead (definitions or headings with line numbers) so it can read just the part it needs; passing `limit` always goes through. Adds the `/tokenleak` skill. Turn the guard off with `TOKENLEAK_GUARD=0`, or move its threshold with `TOKENLEAK_GUARD_BYTES`. At session start, at most once a day, it also replays this project's recent sessions and, if an earlier auto-compact would have saved 10% or more, tells you once a week (a message to you, never added to the model's context; `TOKENLEAK_TIPS=0` silences it).

```
/plugin marketplace add Pazificateur69/tokenleak
/plugin install tokenleak@tokenleak
```

**Codex (plugin).** Same rules at session start (and in subagents where your Codex version fires that hook), plus the skill:

```bash
codex plugin marketplace add Pazificateur69/tokenleak
codex plugin add tokenleak@tokenleak
```

Then open `/hooks` in Codex to review and trust its lifecycle hook, and start a new thread.

**Any agent that supports Agent Skills** (Codex, Cursor, Gemini CLI, GitHub Copilot, Windsurf, Cline, OpenCode and [50+ more](https://github.com/vercel-labs/skills#supported-agents)):

```bash
npx skills add Pazificateur69/tokenleak -g
```

**Always on, any agent, no install.** Append the rules to your instructions file (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`…):

```bash
curl -fsSL https://raw.githubusercontent.com/Pazificateur69/tokenleak/v1.9.0/skills/tokenleak/SKILL.md | awk '/^## Audit/{exit} f>=2; /^---$/{f++}' >> AGENTS.md
```

## The audit

```bash
# no install: Python 3.8+, stdlib only, reads ~/.claude/projects and ~/.codex/sessions
curl -fsSLO https://raw.githubusercontent.com/Pazificateur69/tokenleak/v1.9.0/skills/tokenleak/scripts/tokenleak.py
shasum -a 256 tokenleak.py   # 983cd19a96327d13d75d9fc13bbf75f6ea67e90369dcebe4629dab96e7612b70
python3 tokenleak.py --since 30d
```

The report starts with where the money went (`cost split`: context, read from the cache or written to it, versus output), then every leak priced by its estimated context tax.

Or install the CLI from [PyPI](https://pypi.org/project/tokenleak/): `uvx tokenleak` (or `pipx install tokenleak`, or `pip install tokenleak`), or run it from a clone: `python3 skills/tokenleak/scripts/tokenleak.py`. Or just ask your agent: *"audit my token leaks"*.

<p align="center"><img src="https://raw.githubusercontent.com/Pazificateur69/tokenleak/main/assets/demo.svg" alt="tokenleak audit output: leak score, leak kinds with the rule that fixes each, top leaks" width="900"></p>

*The screenshot is the audit of 20 benchmark runs without the rules.*

| flag | |
|---|---|
| `--since 24h \| 7d \| 4w \| 2026-10-01 \| all` | time window (default `7d`) |
| `--here` / `--current` | sessions in this directory / only the latest one |
| `PATH…` | audit specific transcript files or folders instead of the defaults |
| `--project TEXT`, `--session ID`, `--agent all\|claude\|codex` | filters |
| `--compare 2026-10-01` | before vs after a date, e.g. the day you installed the rules: leak score and cost per call |
| `--top N` | individual leaks to list (default 10) |
| `--json` | machine-readable, for CI or dashboards |
| `--share` | small anonymized card for posting |
| `--html report.html` | self-contained HTML report to open, screenshot or send (add `--redact` before sharing) |
| `--redact` | hide commands, paths and project names |
| `--no-color` | plain output |

### Project rules from your own leaks

```bash
cd your-project && tokenleak suggest   # or: python3 /path/to/tokenleak.py suggest
```

Reads the last 30 days of sessions in that project and prints a block to paste into its `CLAUDE.md` or `AGENTS.md`, written from what actually leaked there. Illustrative output (yours depends on your sessions):

```markdown
<!-- tokenleak suggest: 23 sessions in shop-api since 2026-09-12, leak score 11.2% -->
## Token hygiene for this repo

Keep tool output out of the context; these are this repo's biggest repeat offenders:

- `npm test` printed ~9.1k tokens per run (23x). Run it as `npm test --silent 2>&1 | tail -n 40` (iterate on the one failing test).
- `git diff` printed ~3.0k tokens per run (5x). Run it as `git diff --stat` first, then `git diff -- <path>` for the files you need.
- Large files: `src/data/catalog.ts` (~18.2k tokens, read 14x). `grep -n` them, then read only the lines you need.
```

Only real project commands (tests, builds, installs, linters, git, docker) and files that exist in the project make the list. The skill offers to add it for you, and asks first.

The full report also ranks your projects by leak score (`by project`).

### Live leak meter (Claude Code status line)

See the current session's leak score while you work. Add to `~/.claude/settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "python3 ~/.claude/plugins/marketplaces/tokenleak/skills/tokenleak/scripts/tokenleak.py statusline"
}
```

It prints `leak 3.1% A · ctx 84.2k · top big-read` (point the path at wherever `tokenleak.py` lives if you didn't install the plugin).

### What it finds

| leak | what happened | rule that fixes it |
|---|---|---|
| `big-read` | a file read far bigger than the part you needed | Locate, then read |
| `noisy-shell` | tests, builds, installs or logs dumped into context | Bound every command |
| `re-read` | a file read again, unchanged, while still in context | Never re-read |
| `wasted-call` | the same call, same answer, again (incl. Claude Code's "file unchanged" round-trips) | Never re-read |
| `serial-call` | two independent reads/searches done one turn after the other | Batch independent calls |
| `wide-search` | a search that returned pages of matches | Narrow searches |
| `big-fetch` | a web page or MCP/API payload dumped whole | Narrow fetches |
| `rewrite` | a whole file rewritten to change a few lines | Edit, don't rewrite |
| `big-result` | a subagent or another tool returned a huge result | Narrow searches and fetches |
| `verbose-reply` | long recap prose | Answer lean |

It also shows what's **always loaded**: your `CLAUDE.md` / `AGENTS.md` / memory files and the base context (system prompt, tools, MCP servers) re-sent on every call, with their share of your cost. Not counted as leaks, but often the cheapest win.

### How it's computed

For each tool result: **context tax = avoidable tokens × (cache write + every later call after that × cache read)**, using each provider's relative prices (Claude: cache read 0.1×, cache write 1.25–2×, output 5×; Codex/GPT-5: cached 0.1×, output 8×). *Avoidable* is an estimate: only the part above a sane budget counts (e.g. a 6k-token read counts as 4k avoidable), the full size only for exact repeats. The audit can't know whether a big read was truly needed, so treat each finding as a suspect, not a verdict, and judge the trend with `--compare`. The **leak score** is the share of your total token cost that this estimate calls avoidable. Dollar amounts come from Claude Code's own per-session cost (prorated when a session started before the `--since` window), never from a price table we maintain.

Everything stays on your machine: no network, no telemetry, ~1,700 lines of stdlib Python you can read in ten minutes.

## Benchmark

A/B tests in Claude Code (`claude -p`): same prompt, a fresh copy of the same small repo for every run, every run checked by a script (tests green, build passing, exact answer, feature working) and published with the exact rules and its token usage by type. Cost is the median API-equivalent cost per run, summed over tasks; intervals are 95% bootstrap intervals over runs (`bench/stats.py`), optimistic with 4 to 10 runs per arm.

| what | model | runs per arm | cost | 95% CI | passed |
|---|---|---|---|---|---|
| tokenleak rules | Sonnet 5 | 40 | **−32%** | −42% to −20% | 40/40 · 40/40 |
| same, without the task that gained most (add-feature) | Sonnet 5 | 30 | −19% | −36% to −14% | 30/30 · 30/30 |
| rules + read guard, against its own batch's baseline | Sonnet 5 | 20 | −23% | −41% to +10% | 20/20 · 20/20 |
| rules alone | Haiku 4.5 | 20 | −1% | −20% to +21% | 20/20 · 20/20 |
| rules + read guard (v1.4) | Haiku 4.5 | 20 | −20% | −31% to −4% | 20/20 · 20/20 |
| rules + read guard with outline (v1.5) | Haiku 4.5 | 20 | −28% | −35% to −13% | 20/20 · 20/20 |
| `autoCompactWindow` 300000 (a native Claude Code setting), 1M sessions | Sonnet 5 | 4 | −16% | −36% to −6% | 4/4 · 4/4 |

**Read it honestly.**
- Four small tasks on a synthetic repo the author wrote to contain what leaks in real ones; single runs swing up to 4x. The first Sonnet batch said −40%, the second −21%; the table pools both.
- Haiku 4.5 didn't follow the rules on its own; the read guard (code, not prompt) is what helped. On Sonnet the guard added nothing measurable over the rules.
- The `add-feature` task was written before the rules were tuned and never used to tune them. It also gains the most, which is why the table shows the total without it.
- Compaction pays only on long sessions: on short ones it cost +2% to +59% in the same harness ([BENCHMARK.md](https://github.com/Pazificateur69/tokenleak/blob/main/BENCHMARK.md#the-auto-compact-window)).

Everything, with per-task tables, the losing results and how each number is computed: [BENCHMARK.md](https://github.com/Pazificateur69/tokenleak/blob/main/BENCHMARK.md). To rerun it or measure your own sessions before and after: [REPRODUCE.md](https://github.com/Pazificateur69/tokenleak/blob/main/REPRODUCE.md).

## The rules

The full skill is [skills/tokenleak/SKILL.md](https://github.com/Pazificateur69/tokenleak/blob/main/skills/tokenleak/SKILL.md). In short:

1. **Locate, then read.** Check the size, `grep -n`, then read only that range.
2. **Compute, don't read.** Questions about data get a one-liner that prints the answer, not the data.
3. **Bound every command.** Quiet flags; long jobs go to a log file, read with `tail`, dig with `grep`. Never re-run just to see more.
4. **Never re-read** what is already in context.
5. **Batch independent calls** in one turn, and chain shell steps in one command.
6. **Diffs over files.** `git diff --stat` before `git diff`.
7. **Edit, don't rewrite.**
8. **Narrow searches and fetches.** Scope, cap, select fields.
9. **Delegate wide exploration** to a subagent; only its summary comes back.
10. **Answer lean.** Result first, no recap.

And never save tokens by truncating away the real error, guessing file contents, or skipping verification.

## FAQ

**Does it make the agent worse?** Not in the benchmark: every run is checked by a script, and the pass rate was the same in every arm (40/40 on Sonnet, 60/60 per batch on Haiku). The guardrails are explicit: a leak is cheaper than a wrong fix.

**My agent already does some of this.** Good agents do. Claude Code, for one, already blocks re-reading an unchanged file; the audit counts those blocked attempts as wasted round-trips. The audit tells you how much is left on your own sessions, not on a demo.

**ccusage or tokenleak?** Both read the same local transcripts. [ccusage](https://github.com/ryoppippi/ccusage) tells you how much you spent, by day, session or model. tokenleak tells you which tool results made it expensive and plugs them. They work well side by side.

**What about rtk, caveman and the rest?** Complementary. rtk compresses command output at the shell level; output-style skills shorten replies. tokenleak changes *what the agent asks for* and measures the result on your real transcripts. Run the audit before and after anything you install.

**What do the rules cost?** About 770 tokens, re-sent on every call from the cache: over a 60-call session, about as much as 6.1k tokens of fresh input (Claude Code writes its cache for an hour, at 2x). Keeping one 6k-token test log down to 800 tokens at call 5 of that session saves about six times that.

**Limitations.** Token sizes of individual results are estimated (~4 chars/token); session token totals come from the usage the transcripts record, and dollars only from the sessions that record a cost. "Avoidable" is an estimate, not a measurement. `serial-call` is a heuristic (it only flags a call whose target was already known and isn't mentioned in the previous result). Codex transcript formats change between versions; Claude Code is the best-tested path.

## Listed on

[Skills Directory](https://www.skillsdirectory.com/skills/pazificateur69-tokenleak) (security grade A). Find more tools like this on [Claude Market](https://www.claudemarket.ai/mcp).

## Contributing

Feature freeze until 2026-11-10: fixes, measurements and docs only. Reruns of the benchmark and before/after numbers from your own sessions are the most useful contributions right now: [REPRODUCE.md](https://github.com/Pazificateur69/tokenleak/blob/main/REPRODUCE.md), [CONTRIBUTING.md](https://github.com/Pazificateur69/tokenleak/blob/main/CONTRIBUTING.md). Tests: `python3 -m unittest discover -s tests`.
