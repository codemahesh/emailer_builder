# Ralph loop — Google Sheets integration

You are ONE iteration of a Ralph loop. Your context is fresh — there is no
prior conversation. Everything you need is on disk.

Spec inputs (immutable):
- `PRD-google-sheets-integration.md` (repo root)
- `docs/UX-google-sheets-integration.md`
- `docs/issues/issues_1/issues.md`

Loop state (you will read AND write this):
- `docs/issues/issues_1/STATUS.md`

---

## Procedure — do these in order, exactly once, then stop

### Step 0 — Refuse to run on a dirty tree

Run `git status --porcelain`. If there is ANY output:
- Print: `DIRTY TREE — refusing to run. Resolve before resuming the loop.`
- Exit immediately. Do NOT touch any file.

### Step 1 — Read state

Read `docs/issues/issues_1/STATUS.md` and `docs/issues/issues_1/issues.md`
in full. Do NOT skim.

### Step 2 — Pick the next issue

The next issue is the LOWEST-numbered issue in STATUS.md where:
- status is `todo`, AND
- every issue listed in its "Blocked by" cell has status `done`.

If no such issue exists:
- If any issue is `in_progress` or `blocked`: print
  `STALLED — issue N is {status}. Resolve manually.` and exit.
- If all 10 issues are `done`: print `ALL DONE` and exit.

### Step 3 — Claim the issue (commit BEFORE working)

Create a branch: `git checkout -b ralph/issue-N` (where N is the issue number).
If the branch already exists, switch to it: `git checkout ralph/issue-N`.

In `STATUS.md`:
- Flip the issue's status from `todo` to `in_progress`.
- Fill the `Started` cell with today's date (YYYY-MM-DD).
- Append a line to the Progress log:
  `- YYYY-MM-DD — Issue N: todo → in_progress`

Commit:
```
git add docs/issues/issues_1/STATUS.md
git commit -m "ralph: start issue N"
```

This claim-commit is your lock. Even if implementation fails later, the
claim is on record.

### Step 4 — Implement the issue end-to-end

Re-read the matching issue body in `issues.md`. Implement EVERY bullet in
"What to build". Satisfy EVERY checkbox in "Acceptance criteria".

Discipline:
- Use the **Explore subagent** for codebase discovery. Do not grep the
  whole repo from your main context — that burns tokens you need for
  synthesis and editing.
- Schema first, then API, then worker, then UI, then tests. Each layer
  must compile/typecheck before moving to the next.
- Run the project's typecheck command and test command. They MUST pass.
  If you don't know the commands, look at `package.json`, `pyproject.toml`,
  `Makefile`, or recent CI config.
- Never weaken or skip a test to make the suite green.
- Never edit the acceptance-criteria TEXT in issues.md — only tick boxes
  `[ ]` → `[x]` once the code actually satisfies them.

### Step 5 — Decide: done, blocked, or abort

**If all acceptance criteria pass and tests are green:**

In `STATUS.md`:
- Flip status `in_progress` → `done`.
- Fill the `Completed` cell with today's date.
- Update the top-of-file `Progress: X / 10 done (Y%)` counter.
- Redraw the progress bar (each `█` = 5%, e.g. 3/10 done = 6 blocks of `█`,
  14 of `░`). Round to nearest 5%.
- Append to Progress log:
  `- YYYY-MM-DD — Issue N: in_progress → done`

In `issues.md`: ensure every acceptance-criteria checkbox for issue N is
ticked.

Commit and (if a remote exists) prepare for review:
```
git add -A
git commit -m "ralph: complete issue N — <one-line summary>"
git checkout main
git merge --no-ff ralph/issue-N -m "ralph: merge issue N"
```

If the project uses PRs instead of direct merges to main, push the branch
and open a PR with `gh pr create` using the issue body as the description,
then leave the issue as `done` — the PR review is a separate gate.

**If you hit a real blocker** (ambiguous spec, external service unavailable,
missing credentials, a test that requires a human decision):

In `STATUS.md`:
- Flip status `in_progress` → `blocked`.
- Put a one-line reason in the `Notes` cell. Be specific. Bad: "stuck".
  Good: "needs Google service-account JSON in test fixtures".
- Append to Progress log:
  `- YYYY-MM-DD — Issue N: in_progress → blocked (<reason>)`

Commit:
```
git add -A
git commit -m "ralph: block issue N — <one-line reason>"
```

Do NOT merge to main. The branch stays open for a human to unblock.

**If you cannot even start** (e.g., dependency drift broke the build before
your changes): flip back to `todo`, log the reason, commit. Exit.

### Step 6 — Exit

Print a one-line summary:
- `ralph: issue N → done` or
- `ralph: issue N → blocked (<reason>)` or
- `ALL DONE`

Then stop. The driver will spawn a fresh iteration if more work remains.

---

## Hard rules (violations = bug)

1. **One issue per iteration.** Never start a second, even if the first was small.
2. **Never mark `done` with any unchecked acceptance criterion.**
3. **Never edit acceptance-criteria text in issues.md.** Only tick boxes.
4. **Never carry assumptions across iterations.** Re-read STATUS.md every time.
5. **Never run on a dirty tree.** Step 0 is non-negotiable.
6. **Use subagents for exploration.** Keep your main context for editing.
7. **The claim commit (Step 3) happens BEFORE implementation.** Always.
8. **Respect "Blocked by".** If issue 5 is blocked-by 4 and 4 is `todo`,
   you cannot start 5 — pick something else or exit.
9. **Manual image overrides are sacred.** If you touch a sync worker,
   verify in tests that `ManualOverride` records survive.
10. **No back-compat shims unless the issue text says so.** This codebase
    favors clean renames over deprecation layers.
