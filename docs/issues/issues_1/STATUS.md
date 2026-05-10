# Google Sheets Integration — Status Tracker

Source: `issues.md` in this folder. Update this file as issues are picked up, completed, or blocked. Designed for a Ralph loop to read at the start of each iteration and pick the next unblocked `todo` issue.

**Progress:** 3 / 10 done (30%)

```
[██████░░░░░░░░░░░░░░] 30%
```

---

## Status legend

- `todo` — not started, not yet picked up
- `in_progress` — currently being worked on (one at a time per loop)
- `blocked` — waiting on another issue or external input
- `review` — implementation done, awaiting human review / merge
- `done` — merged and verified

---

## Issue board

| #  | Title                                                          | Type | Status | Blocked by | Started     | Completed   | Notes |
|----|----------------------------------------------------------------|------|--------|------------|-------------|-------------|-------|
| 1  | Schema foundation + `sheet_parser` extraction                  | AFK  | done        | —          | 2026-05-10  | 2026-05-10  |       |
| 2  | Verify endpoint + Link-tab UI with all error banners           | AFK  | done        | 1       | 2026-05-10  | 2026-05-10  |       |
| 3  | Downloadable templates                                         | AFK  | done        | 2       | 2026-05-10  | 2026-05-10  |       |
| 4  | Versioned snapshots on Full Sync                               | AFK  | in_progress | 1       | 2026-05-10  |             |       |
| 5  | Preview endpoint + collapsible preview table                   | AFK  | todo   | 4          |             |             |       |
| 6  | File upload path (Upload tab end-to-end)                       | AFK  | todo   | 2, 4       |             |             |       |
| 7  | Update List + Update Summary + smart re-scrape worker          | AFK  | todo   | 4          |             |             |       |
| 8  | Action-button rationalization (three-button hierarchy)         | AFK  | todo   | 7          |             |             |       |
| 9  | Re-scrape progress card via WebSocket                          | AFK  | todo   | 7          |             |             |       |
| 10 | Preview refresh probe + "Updates available" banner             | AFK  | todo   | 5, 7       |             |             |       |

---

## Dependency graph

```
1 ── 2 ── 3
│    │
│    └──── 6
│         │
└── 4 ────┤
     │    │
     ├── 5 ──── 10
     │         │
     └── 7 ────┤
          ├── 8
          ├── 9
          └── 10
```

Unblocked at start: **Issue 1**.
After Issue 1 done: **2, 4** become unblocked.
After Issue 4 done: **5, 7** unblock (and **6** when 2 also done).

---

## Ralph loop guidance

1. Open this file. Find the lowest-numbered issue whose status is `todo` AND whose `Blocked by` issues are all `done`.
2. Mark it `in_progress`, fill the `Started` cell with today's date (YYYY-MM-DD).
3. Read the matching issue body in `issues.md` and implement it end-to-end (schema → API → worker → UI → tests as applicable).
4. Verify all acceptance criteria pass locally.
5. Mark it `done`, fill `Completed`, update the progress counter at the top, and re-render the progress bar.
6. Commit the changes and the updated `STATUS.md` together.
7. Loop.

If an issue cannot proceed (external blocker, ambiguous spec), set status to `blocked` with a one-line reason in `Notes` and move to the next unblocked issue.

---

## Progress log

Append a one-line entry below each time an issue's status changes. Newest at the top.

- 2026-05-10 — Issue 4: todo → in_progress
- 2026-05-10 — Issue 3: in_progress → done
- 2026-05-10 — Issue 3: todo → in_progress
- 2026-05-10 — Issue 2: in_progress → done
- 2026-05-10 — Issue 2: todo → in_progress
- 2026-05-10 — Issue 1: in_progress → done
- 2026-05-10 — Issue 1: todo → in_progress
