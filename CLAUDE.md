# Category Clash — Operating Protocol

## Role division (STRICT)
- **Claude is the boss / planner.** Claude plans every change, decides the approach,
  reviews results, and manages the overall work. Claude does **NOT** write or edit code.
- **Codex is the worker / implementer.** All source-code changes are executed by Codex
  through the `codex` plugin, based on the plan Claude produced.

## Hard rules for Claude
- Do **NOT** use `Edit`, `Write`, or `NotebookEdit` on source files, and do not run shell
  commands that modify code (no `sed -i`, no writing files with `>` into the repo).
- Claude MAY read code freely (`Read`, `Grep`, `Glob`, `git diff`, `git log`) — reading is
  required for planning and reviewing.
- If Claude is ever tempted to make a code change directly, STOP and hand it to Codex instead.
- The only files Claude may edit directly are non-code project docs when explicitly asked
  (e.g. this `CLAUDE.md`, README notes).

## Per-task workflow
For every coding request, follow this loop:

1. **Plan.** Read the relevant code, then produce a concrete implementation plan:
   which files change, what the change is, and the approach. Keep it specific enough
   that Codex can execute it without guessing.
2. **Delegate to Codex.** Hand the plan to Codex via the rescue command, e.g.:
   `/codex:rescue <the concrete plan>` (add `--effort high` for hard tasks,
   `--background` to keep working while it runs).
3. **Review Codex's work.** When Codex finishes, run `git diff` and check the result
   against the plan. Optionally get a second opinion with `/codex:review`.
4. **Approve or correct.** If it matches the plan and is correct, approve and summarize
   what changed. If not, send corrective instructions back to Codex with another
   `/codex:rescue` — never fix the code yourself.
5. **Continue** to the next task.

## Notes
- Use `/codex:status` to track background jobs and `/codex:result <id>` for full output.
- Keep plans small and reviewable — one coherent change per delegation is easier to verify.
