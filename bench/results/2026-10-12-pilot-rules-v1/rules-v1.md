# tokenleak

Every tool result you pull into context is re-sent on **every later call** until compaction. A 6k-token log read at call 5 of a 60-call session is paid ~55 more times. Every extra round-trip re-sends the whole context. Output costs ~5x input and joins the context too. So let in only what the next decision needs. Correctness first: a leak is cheaper than a wrong fix.

## Rules

1. **Locate, then read.** Search first (`grep -n`, `rg -n`, Grep), then read only the region you need (offset/limit, `sed -n 'A,Bp'`). Read a whole file only if it is short (under ~300 lines) or you truly need all of it.
2. **Bound every command.** Never let tests, builds, installs or logs stream into context unbounded.
   - Quiet or failures-only modes: `pytest -q -x`, `vitest run --reporter=dot`, `go test ./... 2>&1 | grep -v '^ok'`, `cargo test -q`, `npm ci --silent`, `make -s`.
   - Long jobs: `L="${TMPDIR:-/tmp}/out.log"; cmd > "$L" 2>&1; echo "exit=$?"; tail -n 40 "$L"`. Need more? `grep -n -m 20 -E 'error|FAIL|panic' "$L"` on the saved log. Never re-run a job just to see more of its output.
   - Iterate on the one failing test, not the whole suite. Run the full suite once at the end, quietly.
3. **Never re-read what you have.** A file you read or wrote is still in context. Re-read only after compaction or after something else changed it.
4. **Batch independent calls.** Reads and searches that don't depend on each other go in one turn (parallel tool calls). Each extra round-trip re-sends everything.
5. **Diffs over files.** `git status -s`, `git diff --stat` then `git diff -- <path>`, `git log --oneline -n 15`, `git show --stat <sha>`.
6. **Edit, don't rewrite.** Targeted edits only. Never rewrite a whole file to change a few lines, and never paste back into chat code that is already on disk.
7. **Narrow searches and fetches.** Scope by path and file type, cap results (`-m`, `head_limit`, `| head -n 30`, `-l` for names only). Pick fields from APIs and JSON (`--json a,b`, `jq '.items[] | {id,name}'`, `per_page`). Ask a web fetch a precise question instead of dumping the page.
8. **Delegate wide exploration.** If an answer means opening 10+ files and you only need the conclusion, hand it to a subagent if your agent has them. Only its summary enters your context.
9. **Answer lean.** Lead with the result. No step-by-step recap, no restating the diff, no closing summary of what the user can already see, no filler.

## Never save tokens by

- truncating so hard you miss the real error (widen with `grep`/`sed -n` on the saved log instead);
- skipping a read you need to edit correctly, or guessing file contents;
- skipping verification. Run the tests, quietly.

## Audit

When asked to audit tokens or find leaks, run `python3 scripts/tokenleak.py` from this skill's directory (Python 3.8+, no dependencies, local and read-only). Use `--current` for the session you are in, `--here` for the current project, and `--since 30d` for a wider window. Report the leak score, the top 3 leak kinds, and the matching rule above.
