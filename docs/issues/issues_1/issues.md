# Google Sheets Integration — Issues

Tracer-bullet slices derived from `PRD-google-sheets-integration.md` and `docs/UX-google-sheets-integration.md`.

Each slice cuts through schema → API → worker → UI → tests where applicable. Issues are listed in dependency order. Status is tracked in `STATUS.md` next to this file.

---

## Issue 1: Schema foundation + `sheet_parser` extraction

**Type:** AFK

### What to build

Lay the data-layer and parsing foundation that all later slices depend on. No user-visible behavior changes.

- Add migration creating `sheet_versions` and `sheet_version_rows` tables and a `deleted_at TIMESTAMPTZ NULL` column on `products`. Schema per PRD §8.1.
- Extract header normalization (currently in `sheet_reader.py`) into a new `backend/app/modules/sheet_parser.py`. Refactor `read_sheet` to use it. Behavior is unchanged for existing call sites.
- Add a `Product.active` query helper (filters `deleted_at IS NULL`) and audit existing `select(Product)` call sites — switch readers that should never see soft-deleted rows.
- Add a `sheet_version_store.py` module skeleton with `write_version(...)`, `latest_version(campaign_id)`, `compute_checksum(rows)`, `prune_old_versions(campaign_id, keep=10)`. Unit-tested but not yet wired into any worker.

### Acceptance criteria

- [x] Alembic (or project's migration tool) migration applies cleanly forward and reverses cleanly.
- [x] `sheet_parser.normalize_headers(raw_headers) -> dict` accepts every alias in the existing `sheet_reader.py` aliases table; round-trip unit tests cover all aliases.
- [x] Existing Full Sync still works end-to-end against a real Google Sheet (no regression).
- [x] `Product.active` helper used by every reader that displayed products to end-users; tests confirm soft-deleted rows are hidden.
- [x] `sheet_version_store.compute_checksum` is deterministic and order-independent over rows; covered by unit tests.
- [x] `prune_old_versions` keeps the newest 10 by `imported_at`, deletes the rest in a single transaction; covered by an integration test.

### Blocked by

None — can start immediately.

---

## Issue 2: Verify endpoint + Link-tab UI with all error banners

**Type:** AFK

### What to build

End-to-end verification path on the Link tab. User pastes URL, clicks **Verify & Connect**, sees either a connection chip or one of five inline error banners. No DB writes — verification is read-only (PRD FR-1, UX C1).

- `POST /campaigns/{id}/sheet/verify` returning `{ ok, error_code, headers_found, missing_columns, row_count, sheet_title, tab_count }`. The five `error_code` values are `INVALID_URL` (regex pre-check, no API call), `NOT_FOUND`, `NOT_SHARED`, `EMPTY_SHEET` (warning), `MISSING_COLUMNS`. Required columns: `sku`, `product_link` (case-insensitive, alias-aware via `sheet_parser`).
- New `SyncPanel` skeleton with: source segmented control (Link selected, Upload disabled placeholder for now), URL input, Verify & Connect button, connection chip, service-account row with copy affordance, error banner system per UX §B-2.9. Banners have no dismiss control; clear on successful re-verify.
- Verify success copy: "Verified — nothing imported yet. Click Full Sync to begin." (UX §B-3).
- Multi-tab info banner when `tab_count > 1` (UX §B-7 13.6).

### Acceptance criteria

- [x] Verify fires only on click — pasting/blurring the input does not call the API.
- [x] Each of the five error codes renders the exact banner copy from UX §B-3.
- [x] `NOT_SHARED` banner shows the service-account email with a working copy button (icon → checkmark for 2 s).
- [x] `EMPTY_SHEET` banner is yellow/warning and offers "Connect anyway"; the other four are red/danger and have no dismiss.
- [x] Successful verify replaces the URL input with a connection chip showing sheet title + truncated URL + row count + detected-columns chips.
- [x] p95 latency < 3 s for a 1,000-row sheet (PRD §5.2). Loading spinner appears within 100 ms.
- [x] Switching to the Upload tab and back preserves the typed URL but clears verification status (UX I2).
- [x] Backend e2e test covers all five error codes against fixtures.

### Blocked by

Issue 1.

---

## Issue 3: Downloadable templates

**Type:** AFK

### What to build

Static `.xlsx` and `.csv` templates served by the backend, linked from the empty state and from the `MISSING_COLUMNS` error banner (PRD FR-4).

- `.xlsx` template with a primary "Products" sheet (header row + 1–2 example rows covering required + all optional columns) and a second "Instructions" worksheet documenting required vs. optional columns and valid `priority` values.
- `.csv` template mirroring the Products sheet header row + example rows.
- Files served at `/static/sheet-template.xlsx` and `/static/sheet-template.csv`.
- Frontend "⤓ Download template" link in the Link-tab empty state (below the Verify button) and inside the `MISSING_COLUMNS` banner CTA.
- Clicking initiates a static download; no spinner, no dialog.

### Acceptance criteria

- [x] Both files download with correct MIME types and open without warnings in Excel/Google Sheets/Numbers.
- [x] Filling the template and uploading/connecting it results in a clean verify success (no `MISSING_COLUMNS`).
- [x] Instructions worksheet lists every column from `sheet_parser` aliases and all valid `priority` values.
- [x] Both download links work from the locations specified in UX §B-1.1 and §B-3 microcopy table.

### Blocked by

Issue 2.

---

## Issue 4: Versioned snapshots on Full Sync

**Type:** AFK

### What to build

Every successful Full Sync writes an immutable `sheet_versions` row + per-row `sheet_version_rows`. Checksum dedupe avoids duplicate versions. 10-version retention. API-only; no UI surface yet (PRD FR-7).

- Wire `sheet_version_store.write_version` into the existing Full Sync worker (`sync_worker.py`).
- Compute SHA-256 checksum over canonical-sorted JSON of normalized rows; if it matches the latest version, skip the write and emit a structured log line.
- After each successful write, call `prune_old_versions` keeping the newest 10.
- New endpoint `GET /campaigns/{id}/sheet/versions` returning metadata only.
- Backwards compatibility: existing campaigns without history get version 1 written on their next Full Sync; no migration backfill.

### Acceptance criteria

- [ ] Running Full Sync on a campaign with no prior versions creates `version=1`.
- [ ] Re-running Full Sync with no upstream changes does NOT write a new version (checksum match).
- [ ] Editing one row and re-running Full Sync writes `version=N+1`.
- [ ] After 11 syncs with distinct checksums, only the 10 newest versions remain.
- [ ] Soft-deleted rows excluded from canonical-row JSON (deletion affects diff but not historical row preservation).
- [ ] `GET /sheet/versions` returns `[{id, version, source, source_ref, imported_at, imported_by, row_count, checksum}]` ordered newest-first.
- [ ] Manual image overrides survive every Full Sync (no regression of existing behavior).

### Blocked by

Issue 1.

---

## Issue 5: Preview endpoint + collapsible preview table

**Type:** AFK

### What to build

Read-only preview of the latest imported version, served from `sheet_version_rows` (not a live Sheets call). Collapsed by default behind a disclosure caret (PRD FR-5; UX §B-2.6). Refresh probe is deferred to Issue 10.

- `GET /campaigns/{id}/sheet/preview?version=latest&limit=50&offset=0` returning `{ headers, rows, version, fetched_at, row_count }`.
- Frontend `<PreviewTable>` component: disclosure caret with `▸ Preview {N} products`, virtualized table, sticky header, dynamic columns (no hard-coded schema), pagination controls.
- Snapshot caption beneath header: `Snapshot from v{version} — refresh to check live.` (refresh icon present but disabled/no-op until Issue 10).
- Soft-deleted rows are excluded from the preview by default (UX §B-7 13.4).
- Keyboard navigation: arrow keys cycle rows; Home/End jump first/last.

### Acceptance criteria

- [ ] `/preview` p95 < 500 ms (PRD §5.2 / §8.5).
- [ ] Columns rendered come from the `headers` field in the response — adding a new column to a future import surfaces without code changes.
- [ ] First 50 rows render; pagination works and updates `offset`.
- [ ] Disclosure is collapsed by default (UX D2).
- [ ] Soft-deleted rows do not appear.
- [ ] Preview reflects the snapshot, not live data — editing the source sheet does not mutate the preview without an Update List or Full Sync.
- [ ] Keyboard navigation and `<table>`/`<thead>`/`<tbody>` semantics meet UX §B-6 a11y.

### Blocked by

Issue 4.

---

## Issue 6: File upload path (Upload tab end-to-end)

**Type:** AFK

### What to build

Persona B's primary path: drop an `.xlsx` or `.csv`, parse it server-side using `sheet_parser`, run the same column validation as Link, write a `sheet_versions` row of source `upload`, and proceed (PRD FR-3).

- Enable the Upload tab in the segmented control. Dropzone per UX §B-2.5: idle / drag-over / uploading / error / success states.
- Upload endpoint accepting multipart `.xlsx` / `.csv`; enforce 5 MB cap **before** reading into memory; reject other MIME types; max 10,000 rows.
- Reuse `sheet_parser` so column validation matches Link verification exactly.
- On success: write `sheet_versions` (source = `upload`, source_ref = original filename), upsert `products`, transition the panel to the connected state.
- One-shot semantics: when latest version source is `upload`, hide Update List and replace with "Replace file" affordance; connection chip shows `[Upload (one-shot)]` tag (UX P6-R2, C4).
- Switching from Link → Upload (or vice versa) preserves the prior connection chip with a "Pending source change" tag until the new source verifies (UX I11).

### Acceptance criteria

- [ ] Both `.xlsx` and `.csv` parse correctly through the same `sheet_parser` path.
- [ ] Files >5 MB or with >10,000 rows are rejected with the documented error before parsing.
- [ ] Wrong MIME types rejected server-side regardless of extension.
- [ ] All five error codes (where applicable: `MISSING_COLUMNS`, `EMPTY_SHEET`) surface in the dropzone error state with the same banner copy as Link.
- [ ] After upload success, the connection chip shows `[Upload (one-shot)]` and Update List is not visible.
- [ ] Re-uploading replaces the prior file (treated as a new version).
- [ ] Cancel during upload aborts the XHR.

### Blocked by

Issues 2, 4.

---

## Issue 7: Update List + Update Summary + smart re-scrape worker

**Type:** AFK

### What to build

The day-to-day operation for Persona A. Pull sheet edits in seconds, show a diff, apply only on confirmation, re-scrape only changed-link products, preserve manual overrides (PRD FR-6; UX §B-1.4, §B-2.8).

- `POST /campaigns/{id}/sheet/import` with two phases:
  1. **Preflight** (synchronous): re-read the source, compute diff vs. latest version, return `{ added, removed, updated, unchanged, rescrape_count }`. No DB writes.
  2. **Commit** (async, on Apply): write new `sheet_versions`, upsert `products` by SKU, soft-delete missing SKUs (`deleted_at = now()`), enqueue scrape only for products whose `product_link` changed (URL-normalized: strip trailing slash, lowercase host). Returns `202 { sync_job_id }`.
- New `import_worker.py` performing the smart re-scrape; reuses existing scrape pipeline.
- Manual image overrides (`ManualOverride` records) always preserved (PRD §11 risk, UX C7).
- Frontend `<UpdateSummary>` panel renders inline when preflight returns a non-empty diff:
  - `+ Add N products` · `− Remove N (kept in history)` · `≠ Update N products` · sub-bullet `↳ M will be re-scraped (link changed)` when applicable.
  - `Cancel` (outlined) and `Apply` (filled primary) right-aligned.
- Empty diff: skip the summary entirely; show toast "No changes detected." (UX D5).
- Soft-deleted SKU returning in a future import is restored: shown as `+ Add 1 product (restored from history)` (UX I12).

### Acceptance criteria

- [ ] Editing a non-link field (e.g., price) for one row → preflight reports `updated=1, rescrape_count=0`; Apply writes a new version and does NOT enqueue any scrape.
- [ ] Changing a `product_link` → `rescrape_count=1`; Apply enqueues exactly that product for scrape.
- [ ] Removing a row from the sheet → preflight reports `removed=1`; Apply soft-deletes the matching `products` row (`deleted_at` set).
- [ ] Empty diff renders no summary; toast appears instead.
- [ ] URL normalization treats `https://example.com/p/1` and `https://example.com/p/1/` as the same link.
- [ ] Cancel discards the diff; no version row is written.
- [ ] Manual image overrides survive every Update List apply.
- [ ] Concurrent Update List click while a sync job is in flight is blocked; existing job continues (UX I10).

### Blocked by

Issue 4.

---

## Issue 8: Action-button rationalization (three-button hierarchy)

**Type:** AFK

### What to build

Replace today's Full/Fast Sync pair with the three-operation hierarchy from PRD FR-8 and UX §B-2.7.

- Rename Fast Sync surface (worker code unchanged) to "Quick price update". Move it into a kebab (⋯) overflow menu. New endpoint alias `POST /campaigns/{id}/sheet/quick-price` (or rename existing endpoint with a deprecation shim only if explicitly required — otherwise rename outright per the project's no-back-compat policy).
- Action zone visibility rules:
  - Pre-first-Full-Sync: only Full Sync visible (filled primary). Update List and kebab hidden (UX D3, P4-F2).
  - Post-first-Full-Sync: Update List filled primary, Full Sync outlined secondary, kebab visible.
- Subtitles on each button per UX §B-3 microcopy table.
- Full Sync retains its existing confirm modal with copy from UX §B-3 ("Re-scrape everything?").
- Quick price update fires immediately on click (no confirm); success/partial/failure toasts per UX §B-3.

### Acceptance criteria

- [ ] First-time campaign shows only Full Sync; Update List and kebab appear after the first successful Full Sync.
- [ ] Exactly one filled primary button visible in the action zone at any moment (UX C2).
- [ ] Quick price update item appears under the kebab and is hidden until at least one Full Sync has succeeded (UX D6).
- [ ] Full Sync confirm modal copy matches UX §B-3 verbatim.
- [ ] Quick price update success toast: `Prices updated for {n} SKUs. Images untouched.`
- [ ] Quick price update never touches images (regression test against `ManualOverride` and product image URLs).

### Blocked by

Issue 7.

---

## Issue 9: Re-scrape progress card via WebSocket

**Type:** AFK

### What to build

While a sync job is in flight, the action zone collapses into a progress card driven by the existing `gateway.send_progress` WebSocket (UX §B-1.6, P4-F6).

- Subscribe to progress events keyed by `sync_job_id` returned by `/sheet/import` and Full Sync.
- Progress card shows: header `Re-scraping {done} of {total} changed products…`, progress bar, last-completed SKU with check, and the leave-anytime hint.
- Navigating away and returning resumes the live progress view (state is server-driven, not client-cached).
- All sync buttons disabled while a job is in flight for the campaign (UX I10).
- On completion: action zone restored; toast fires per UX §B-3 with manual-override preserved count (UX C7) — e.g., `Synced {n} products. {k} images preserved (manual overrides).` and `Updated {n} products. {m} images re-scraped, {k} preserved (manual overrides).`

### Acceptance criteria

- [ ] Starting a Full Sync immediately replaces the action zone with the progress card.
- [ ] Refreshing the page mid-sync re-renders the progress card with current state.
- [ ] All sync buttons return to enabled only when no job is in flight for the campaign.
- [ ] Post-Update List toast lists `m re-scraped` and `k preserved (manual overrides)`.
- [ ] Post-Full-Sync toast lists `k preserved (manual overrides)`.
- [ ] WebSocket disconnect during sync does not lose the job; reconnecting picks up the live state.

### Blocked by

Issue 7.

---

## Issue 10: Preview refresh probe + "Updates available" banner

**Type:** AFK

### What to build

The cheap probe that lets users check whether the live source has diverged from the snapshot, without committing anything (UX §B-2.6, P3-A7).

- Refresh icon in the preview table header calls `/sheet/verify` against the live source (read-only).
- Result rendered inside the preview header:
  - No diff → caption updates to `No changes since last import.`
  - Diff → inline banner inside the preview body: `Updates available — [Update List]`. Clicking the CTA jumps focus to the Update List button.
- Disabled when source = upload (no live source to refresh).
- Tooltip / aria-label: `Check the source for updates`.

### Acceptance criteria

- [ ] Clicking refresh with no upstream changes flips the caption to `No changes since last import.` and never triggers Update List.
- [ ] Clicking refresh after an upstream edit shows the inline `Updates available` banner with a working CTA that focuses Update List.
- [ ] The probe never writes to the DB.
- [ ] Refresh icon is disabled (or hidden) when source = upload.
- [ ] Banner persists in the preview header until the next interaction (refresh, expand/collapse, or Update List click).

### Blocked by

Issues 5, 7.
