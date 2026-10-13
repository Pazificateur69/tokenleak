# caveman (competitor arm)

`SKILL.md` is an unmodified copy of `skills/caveman/SKILL.md` from
[JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) at commit
[`2e08b9177c07bb7249a8a2d1a6758e5db281d002`](https://github.com/JuliusBrussee/caveman/blob/2e08b9177c07bb7249a8a2d1a6758e5db281d002/skills/caveman/SKILL.md)
(2026-10-08, plugin v3.2.0; git blob `9a94044529e5ee1576361c891b4a271504518e6f`).
It is byte-identical to the plugin copy, `plugins/caveman/skills/caveman/SKILL.md`.

License: Apache-2.0, Copyright 2026 Julius Brussee. `LICENSE`, `NOTICE` and `LICENSE-MIT` are unmodified copies of
the files at the same commit (`LICENSE-MIT` covers the parts contributed under MIT before caveman 3.0.0, as its
`NOTICE` says). "Caveman" is a trademark of Julius Brussee; this benchmark is not affiliated with or endorsed by it.

## What the `caveman` arms append

`bench/run.py` rebuilds what the plugin's SessionStart hook (`src/hooks/caveman-activate.js`, default mode
`caveman`) injects: the banner `CAVEMAN MODE ACTIVE — mode: caveman`, this file's body without its YAML
frontmatter, and the hook's one-line `Switch: ...` footer. Text only: no CLI, engine, proxy or MCP server.

Not reproduced: the UserPromptSubmit hook (`caveman-mode-tracker.js`) also adds a one-line reminder on each user
prompt, i.e. once per `claude -p` run.

To refresh: copy the file at a new commit, update the SHA here and in `COMPETITORS` in `bench/run.py`.
