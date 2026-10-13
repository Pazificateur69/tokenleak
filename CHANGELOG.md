# Changelog

All notable changes to tokenleak. Versions follow [semver](https://semver.org/).

## 1.6.0 (2026-10-13)
### New: the biggest lever for long sessions
- **Context window replay.** On a 1M-token window Claude Code compacts only near the limit, so everything, the model's own output included, is re-sent on every call. The audit now replays your main Claude Code sessions with an earlier auto-compact (`autoCompactWindow` at 200k, 300k, 400k, 500k), charges every extra compaction on the harsh side, and recommends a value when it saves 5% or more (in the terminal report, `--html` and `--json` under `totals.context_window`). On the author's last 30 days: 66% of calls over 200k tokens, `300000` → −22% on the whole bill.
- The skill's audit section explains the trade-off and offers to set it, only with the user's go-ahead. The rules injected in every session are unchanged (not one token more).

### Measured
- Real sessions (30 days, 23k calls): after a call that writes a lot, the next call's context grows by 1.04x that output, so the model's thinking, replies and tool calls stay in context; they were 42% of everything re-sent, tool results 20%.
- Quality under compaction (Haiku 4.5, the four tasks chained in one session): `autoCompactWindow` 100k, the lowest Claude Code accepts, 2 to 3 compactions mid-task: 5/5 passed, as did 5/5 without. On those short sessions compacting cost +59% and doubled wall time, which is why the audit only recommends it when your own sessions show a gain. The replay model predicted +91% there: it overstates the cost of compacting.
- `bench/run.py`: `chain` task (all four in one session) and `compact` variant; results in `bench/results/2026-10-13-haiku-4.5-compaction`.

### Faster
- Shell commands are split with `shlex` only when they contain quotes or escapes: a 30-day audit of 3.3 GB of transcripts went from 17 s to 14 s.

## 1.5.1 (2026-10-12)
From an outside review (OpenAI Codex, read-only), each point checked against the code before changing it.

### Fixed
- `tokenleak suggest` advice no longer pipes tests and builds into `tail`, which hid their exit status: it writes the log, prints `exit=`, then shows the tail. Each tool gets its own quiet flag (`jest --silent`, `vitest --reporter=dot`, `pip -q`; npm keeps `--silent`).
- `--since`: a session that started before the window kept its whole recorded cost; it now keeps the window's share. The spend line says how many sessions record a cost.
- Read guard: an `offset` without `limit` no longer bypasses it (the Read tool still returns up to 2,000 lines); only a positive `limit` does. Files over 64 MB get an estimated line count instead of a full scan inside the hook.
- Codex: later output chunks of the same call were dropped; they now add up. Claude Code: a tool call logged twice counts once.
- A folder plus a file inside it no longer counts that transcript twice; `--agent` now filters explicit paths too.
- A report with no leaks still shows what is always loaded (often the cheapest win).
- `--json --redact` drops session ids.

### Benchmark and docs
- Every published run now carries its token usage by type; summaries show median wall time and the output share of cost, so the "output is 7% (Sonnet) to 10-11% (Haiku) of the bill" figure can be rebuilt from the repo.
- The `add-feature` checker is stricter (a second category, and the default report unchanged). All 55 published `add-feature` runs were re-checked: all pass.
- Harness: a checker that crashes or times out records a failed run instead of stopping the benchmark; a run without a cost is reported as missing, never as $0; exports keep the exact rules file.
- README, site and privacy page: the headline says the −32% is with the rules; findings are called estimates, not costs; the rules' own cost is computed instead of claimed; wall time is published (mixed: the guard was slower in one Haiku batch, faster in the other); "Try it first" one-liner at the top.

## 1.5.0 (2026-10-12)
### New
- **The read guard hands back an outline.** When it stops a whole read of a big code or Markdown file, the agent gets the file's definitions or headings with line numbers (outermost first, at most 60 rows; a long top level is sampled across the file), so it can `Read` just that range. CSV files get their header; logs and data files get none. Tested end to end with the real plugin: denied, then one `Read` at the right offset.
- **Cost split** at the top of the report (and in `--html` / `--json`): context (cache reads, cache writes and uncached input) versus output. In the benchmark runs without tokenleak, output was 7% of the cost on Sonnet and 10% on Haiku.
- MCP tools show as `server:tool` (a server id that is only a UUID is dropped), and long paths in the top-leaks list keep their file name.

### Benchmark
- Haiku 4.5, second batch (60 runs, 60/60 passed): read guard with outline −28%, the v1.4 guard without it −25% in the same batch (within the noise of 5 runs per task; the outline saved most on the data question, 9 API calls instead of 12).
- Harness: Apple's `python3` writes bytecode under `~/Library/Caches`, which the run sandbox denies; `fix-build` failed in every arm alike until the cache was pointed inside the run's folder (`PYTHONPYCACHEPREFIX`). Those 15 runs were redone for all three arms.

### Fixed (from an independent review)
- Outline: a top level longer than 60 entries no longer stops halfway through the file; Markdown headings nest by `#` level and `#` comments inside code blocks are skipped; prose such as "class that ..." and value assignments such as `const p = (x).y` are no longer taken for definitions; a UTF-8 BOM no longer hides line 1; files over 4 MB say the outline covers only their start.
- The guard ignores a hook event that is not a JSON object instead of printing a traceback.
- Top-leaks labels never overflow their column, even with long MCP tool names.

## 1.4.0 (2026-10-12)
### New
- **Read guard** (Claude Code plugin): a whole-file `Read` of a text file over ~24 KB is stopped with its size and a hint to grep first; passing `limit` or `offset` always goes through. `TOKENLEAK_GUARD=0` turns it off, `TOKENLEAK_GUARD_BYTES` moves the threshold. Codex keeps its own hooks file without it.
- Instruction files are sized **as actually loaded** when the transcript records them (recent Claude Code), instead of their current size on disk; sessions that loaded none are no longer charged for them.
- The injected rules stop before the skill's Audit section (only useful with the script at hand): about 770 tokens instead of 950.
- `bench/run.py --variants baseline,tokenleak,guard`, and a Haiku 4.5 benchmark in `bench/results`.

### Benchmark, corrected
- A second Sonnet 5 batch (same day, same tasks) gave −21% where the first gave −40%. The README and the site now show both batches pooled: **−32%** over 80 runs, 40/40 passed in both arms, −51% on the held-out task.
- Haiku 4.5: the rules alone changed nothing (−1%); with the read guard, −20% (60 runs).

### Fixed (from an independent review, each with a reproduction)
- One malformed tool input (e.g. a `Read` whose `offset` is a list) crashed the whole audit; inputs are now type-checked and a bad transcript is skipped with a note.
- Windows: the report and `--share` crashed when piped (cp1252); output is now UTF-8.
- Codex subagent rollouts (guardian, spawned threads) were counted as separate sessions; they now join their parent.
- `--compare --json --redact` leaked paths; `--compare` now rejects `--html`/`--share` instead of ignoring them.
- Context tax was off by one call: the first later call writes the cache and the next ones read it; a result never re-sent costs nothing.
- `--since` counted every call of a file touched in the window; it now counts only the calls inside it (and keeps the true session-start context).
- Per-project avoidable spend could count a session twice when a subagent ran in a subfolder.
- `--compare` crashed on timestamps it couldn't parse; ISO dates with `Z` or nanoseconds now work on Python 3.8+.
- Bad `--since` values print a clear error instead of a traceback.
- Different screenshots returned by the same call were flagged as wasted calls.
- "by project" only lists folders with at least 2 sessions, skips temp folders, and aligns in color.

## 1.3.0 (2026-10-12)
- `--html FILE`: self-contained, shareable HTML report (leak score, avoidable spend, leak kinds with their fix, top leaks, by project). Combine with `--redact` before sharing.
- Install the CLI straight from GitHub: `uvx --from git+https://github.com/Pazificateur69/tokenleak tokenleak` or `pipx install git+https://github.com/Pazificateur69/tokenleak`.
- README: animated context-stack illustration (pure CSS SVG, complete even where animations don't run).

## 1.2.1 (2026-10-12)
- `suggest` recognizes project files on Windows (separator- and drive-aware path check).

## 1.2.0 (2026-10-12)
- `tokenleak suggest`: turns a project's own recurring leaks (noisy test/build/install/lint/git commands, large files read whole) into rules for its `CLAUDE.md` / `AGENTS.md`.
- Report: "by project" section.
- Codex "code mode" (`exec` running JavaScript, e.g. web search) is classified as fetches or tool results instead of shell output.

## 1.1.1 (2026-10-12)
- Claude Code manifest no longer lists `hooks/hooks.json` twice (loader warning; rules were still injected once).
- Plugin metadata: documentation, support, privacy and terms links.

## 1.1.0 (2026-10-12)
- `--compare DATE`: leak score and cost per call before vs after a date.
- `tokenleak statusline`: live leak score in the Claude Code status line.
- Codex plugin (`codex plugin marketplace add Pazificateur69/tokenleak`).
- Rules v1.1: "check the size before reading" and "compute, don't read" (see the benchmark notes on how this was kept honest).

## 1.0.0 (2026-10-12)
- First release: lean-context rules (Agent Skill + Claude Code plugin with SessionStart/SubagentStart hooks) and a local, read-only audit of Claude Code and Codex transcripts.
