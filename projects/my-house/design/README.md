# Design outputs

Interview exports and the space program go here (`house-ai program build my-house
--actor <you> --out projects/my-house/design/program`), then the floor-plan concepts
(`house-ai plan generate my-house --actor <you>` writes `design/concepts/`, only after
the owner approved the site and program gates), later 3D output. Everything here is
derived from the project record and can be regenerated.

Exception: [OWNER_DESIGN_RULES.md](OWNER_DESIGN_RULES.md) is owner input, not a derived
export. It holds the owner's binding design rules; read it before any layout work.

## Design study folders

Each design study (one round of options by one agent, or the owner's own drawings) has
its own folder, named so that a plain name sort puts the **newest at the top**:

```
<rank>_<YYYY-MM-DD>_<author>-c<NN>
```

- `rank`: three digits counting **down** from `999`. A new folder takes the smallest
  rank in use minus one, so it sorts above every older folder.
- `YYYY-MM-DD`: the day the study was made.
- `author`: the agent that made it: `claude`, `codex` or `gemini`. Older folders keep
  the name they were made with (`argon` was Gemini). The owner's own drawings use
  `user-designed` in place of `<author>-c<NN>`.
- `c<NN>`: the design cycle, counting up across all agents (C05 was deleted; the next
  is C11). Option IDs inside keep the bare series name (`claude-c09`, `C09-1`); only
  the folder carries rank and date.

Never rename an existing study folder. Add a row to the top of this table with each
new one.

| Folder | Date | Made by | Contents |
|---|---|---|---|
| [990_2026-11-18_claude-c10](990_2026-11-18_claude-c10/) | 2026-11-18 | Claude Code | C10: one design fitted to both falls of the field, with a 3D model of field and house |
| [991_2026-10-27_claude-c09](991_2026-10-27_claude-c09/) | 2026-10-27 | Claude Code | C09-1, C09-2: compact versions of C08 |
| [992_2026-10-27_claude-c08](992_2026-10-27_claude-c08/) | 2026-10-27 | Claude Code | C08-1 to 3, reworked from the owner's 0109-r5 |
| [993_2026-10-26_argon-c07](993_2026-10-26_argon-c07/) | 2026-10-26 | Gemini (argon) | C07 A, B, C |
| [994_2026-10-26_argon-c06](994_2026-10-26_argon-c06/) | 2026-10-26 | Gemini (argon) | C06 A, B, C |
| [995_2026-10-22_claude-c04](995_2026-10-22_claude-c04/) | 2026-10-22 | Claude Code | C04-A and section study |
| [996_2026-10-22_codex-c03](996_2026-10-22_codex-c03/) | 2026-10-22 | Codex | C03 A, B and earthwork |
| [997_2026-10-21_codex-c02](997_2026-10-21_codex-c02/) | 2026-10-21 | Codex | C02 A, B |
| [998_2026-10-21_codex-c01](998_2026-10-21_codex-c01/) | 2026-10-21 | Codex | C01 massing study |
| [999_2026-10-17_user-designed](999_2026-10-17_user-designed/) | 2026-10-13 to 17 | Owner | Redesign 0109-r5 (A, B, C) and review 0110-r2 |
