# Changelog

All notable changes to tokenleak. Versions follow [semver](https://semver.org/).

## 1.4.0 (2026-10-12)
### New
- **Read guard** (Claude Code plugin): a whole-file `Read` of a text file over ~24 KB is stopped with its size and a hint to grep first; passing `limit` or `offset` always goes through. `TOKENLEAK_GUARD=0` turns it off, `TOKENLEAK_GUARD_BYTES` moves the threshold. Codex keeps its own hooks file without it.
- Instruction files are sized **as actually loaded** when the transcript records them (recent Claude Code), instead of their current size on disk; sessions that loaded none are no longer charged for them.
- The injected rules stop before the skill's Audit section (only useful with the script at hand): about 770 tokens instead of 950.
- `bench/run.py --variants baseline,tokenleak,guard`, and a Haiku 4.5 benchmark in `bench/results`.

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
