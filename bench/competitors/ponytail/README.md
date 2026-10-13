# ponytail (competitor arm)

`SKILL.md` is an unmodified copy of `skills/ponytail/SKILL.md` from
[DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) at commit
[`2961b52fc1fe6a5a87c7a959a79512e5c2f3ffe5`](https://github.com/DietrichGebert/ponytail/blob/2961b52fc1fe6a5a87c7a959a79512e5c2f3ffe5/skills/ponytail/SKILL.md)
(2026-10-13; git blob `b76922f76ec6f4db532203c55d710b749fa1f6af`).

License: MIT, Copyright (c) 2026 DietrichGebert. `LICENSE` is an unmodified copy of the file at the same commit.

## What the `ponytail` arms append

`bench/run.py` rebuilds what the plugin's SessionStart hook (`hooks/ponytail-activate.js` via
`hooks/ponytail-instructions.js`, default level `full`) injects: the banner `PONYTAIL MODE ACTIVE — level: full`,
then this file's body without its YAML frontmatter and without the `lite` / `ultra` rows of the levels table.
Its UserPromptSubmit hook only speaks on `/ponytail` level commands, so nothing is missing from that hook; the SessionStart codebase map is (see below).

To refresh: copy the file at a new commit, update the SHA here and in `COMPETITORS` in `bench/run.py`.

**Not reproduced: the codebase map.** At the pinned commit, ponytail's SessionStart hook (`hooks/ponytail-activate.js`) also appends a short "Codebase map" of the working folder, built by `hooks/ponytail-map.js` (on by default; off with `PONYTAIL_MAP=0`). The harness does not run ponytail's code, so the `ponytail` arms get the rules without the map. That map exists to save search calls, so these arms may understate ponytail by that much.
