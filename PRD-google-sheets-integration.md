# PRD: Google Sheets Integration — Verification, Upload, Versioning & Smart Re-import

**Status:** Draft for review
**Owner:** Product (manoj)
**Author:** Generated from grilling session 2026-05-10
**Target release:** TBD
**Document type:** Standard PRD

---

## 1. Executive Summary

The current Google Sheets integration (`SyncPanel.tsx` + `sheet_reader.py`) lets users connect a Google Spreadsheet via URL, share access with a service account, and trigger Full Sync or Fast Sync. It works, but several user-facing problems remain:

1. There is no upfront verification that the link is accessible — failures only surface mid-sync.
2. Required columns (`SKU`, `Product Link`) are not validated before import — bad sheets cause silent or late failures.
3. Users cannot upload a file directly; they must own/host a Google Sheet.
4. There is no template to guide first-time users in formatting their data.
5. There is no preview of the parsed data before or after sync.
6. There is no lightweight "re-fetch the sheet without re-scraping" operation.
7. Sheet history is not preserved — once overwritten, the prior import is gone.

This PRD specifies a redesigned Sheets integration that adds **link verification, column validation, file upload, downloadable template, parsed-data preview, smart re-import (versioned), and a persistent versioned snapshot of every imported sheet**. The redesign rationalizes the current Full/Fast Sync buttons into three distinct operations with clear semantics.

The change touches one frontend panel (`SyncPanel.tsx`), the sheet-reading module, the sync workers, and adds two new database tables. No breaking changes to existing campaigns; existing manual image overrides are preserved.

---

## 2. Problem Statement

### 2.1 Current pain points

| # | Pain | Today | Cost to user |
|---|------|-------|--------------|
| 1 | No pre-flight check on the sheet URL | Errors surface only when Full Sync runs | Wastes a sync attempt; ambiguous failure messages |
| 2 | No column-level validation | Missing `sku` causes empty imports or partial failures | User cannot tell if their sheet is correctly formatted |
| 3 | No file upload | Forces every user into a Google Sheet | Excludes users with `.xlsx` / `.csv` workflows |
| 4 | No template | First-time users guess at header names and priority values | High failure rate on first attempt |
| 5 | No preview of parsed rows | User cannot verify what the system actually read | Trust gap; "did it import correctly?" |
| 6 | No "re-read without re-scrape" action | User must run Full Sync (slow, destructive) for any sheet edit | Discourages frequent small edits |
| 7 | No history of past imports | Each sync overwrites; no audit trail or diff | Cannot answer "what changed since last week?" |

### 2.2 Strategic context

The Sheets integration is the campaign onboarding step. Friction here gates everything downstream (visual brief, scrape, render). Reducing setup failure and increasing trust in imported data directly improves campaign-creation completion rate.

---

## 3. Goals & Objectives

### 3.1 Goals

1. **Pre-flight confidence.** A user knows within 3 seconds whether their sheet is connectable, accessible, and correctly formatted.
2. **Format flexibility.** Users can choose between linking a Google Sheet or uploading a file.
3. **Self-serve onboarding.** A downloadable template prevents 80% of "bad column" errors.
4. **Visible truth.** Users see exactly what the system parsed before relying on it.
5. **Fast iteration.** Editing a sheet and pulling the changes takes seconds, not minutes, and does not destroy scraped images.
6. **History.** Every import is preserved as a versioned snapshot for diffing, auditing, and (future) rollback.

### 3.2 Non-goals (v1)

- A version-browser UI for sheet history.
- Snapshot rollback / restore.
- Per-row re-scrape from the preview table.
- Multi-tab Google Sheets (continues to read first visible sheet).
- Live collaborative editing of the sheet within the app.
- Diff visualization between sheet versions in the UI.

---

## 4. Target Users & Personas

### Persona A — Campaign Manager (primary)
- Owns the product list for a campaign.
- Edits a Google Sheet repeatedly during a launch week.
- Frustrated when small edits force a slow re-scrape.
- Needs confidence the data the system has matches the sheet.

### Persona B — One-shot Importer (secondary)
- Has a static `.xlsx` or `.csv` exported from another system.
- Will not maintain a Google Sheet.
- Wants to upload, parse, and move on.

### Persona C — Internal Operator (tertiary)
- Debugs failed campaigns.
- Needs to answer: "what did the user import on date X, and did it parse correctly?"
- Reads versioned snapshots via API; no UI required in v1.

---

## 5. User Stories & Requirements

### 5.1 Functional requirements

#### FR-1 — Link verification
Verify the sheet URL is accessible and well-formed before connecting.

> **As** Persona A,
> **I want** the system to verify my Google Sheet link the moment I click Connect,
> **So that** I learn about access or format problems immediately, not after a 5-minute sync.

**Acceptance criteria:**
- A "Verify & Connect" button on the link tab triggers `POST /campaigns/{id}/sheet/verify`.
- Verification fires only on click (not on paste/blur) to avoid API spam.
- Five distinct error states are surfaced inline:
  - Invalid URL format (regex mismatch, no API call)
  - 404 sheet not found
  - 403 service account not shared (recovery CTA: copy service-account email)
  - Empty sheet (warning, does not block)
  - Missing required columns (recovery CTA: download template)
- On success: input shows "Connected to: *<sheet title>*" and the panel transitions to the connected state.
- Verification is read-only — no DB writes, no sync triggered.

#### FR-2 — Column validation
Validate that imported data contains the columns the rest of the system depends on.

> **As** Persona A,
> **I want** the system to refuse my sheet if `sku` or `product_link` is missing,
> **So that** I never create a campaign with broken data.

**Acceptance criteria:**
- Required columns: `sku`, `product_link`.
- Validation is case-insensitive and accepts the existing aliases in `sheet_reader.py:44` (e.g., `url`, `link`, `product link`).
- If either column is missing, verification returns `{ ok: false, error_code: "MISSING_COLUMNS", missing_columns: [...] }`.
- Optional columns (`section_title`, `priority`, `raw_price`, `utm_campaign`, `button_name`) remain optional with their existing defaults.
- The error block shows the missing column name(s) and a "Download Template" CTA.

#### FR-3 — Direct file upload
Allow users to upload `.xlsx` or `.csv` files as an alternative to a Sheets link.

> **As** Persona B,
> **I want** to upload an `.xlsx` or `.csv` file directly,
> **So that** I do not need to create or share a Google Sheet.

**Acceptance criteria:**
- The Sheets panel shows a segmented control: `[ Link ] [ Upload ]`.
- Upload tab accepts `.xlsx` and `.csv` only, max 5 MB, max 10,000 rows.
- File is validated server-side using the same column rules as FR-2.
- A successful upload writes a new `sheet_version` and updates the `products` table (same downstream behavior as a Sheets-link import).
- A campaign may switch sources between `link` and `upload`; the most recent import wins.
- "Refresh from sheet" controls are disabled when the latest version's source is `upload`.

#### FR-4 — Downloadable template
Provide a pre-formatted file users can fill in.

> **As** Persona A or B (first-time),
> **I want** a "Download Template" link,
> **So that** I get the column headers right on my first attempt.

**Acceptance criteria:**
- A static `.xlsx` template is served at `/static/sheet-template.xlsx`.
- A static `.csv` version is served at `/static/sheet-template.csv`.
- Template contains a header row with all supported columns and 1–2 example rows.
- A second worksheet ("Instructions") in the `.xlsx` documents required vs. optional columns and valid `priority` values.
- "Download Template" link appears: (a) below the upload input, (b) inside the "missing columns" verification error.

#### FR-5 — Fetched data preview
Show the parsed rows in the UI.

> **As** Persona A,
> **I want** to see the rows the system parsed from my sheet,
> **So that** I can verify the import is correct before relying on it.

**Acceptance criteria:**
- The connected state has a "Preview *N* products" toggle, collapsed by default.
- When expanded, a virtualized table renders the first 50 rows of the latest `sheet_version`.
- The table dynamically renders all columns present in the imported sheet (not a fixed schema).
- For >50 rows, paginate with `limit`/`offset`.
- A small refresh icon in the table header re-runs `/sheet/verify` against the live source. If data has changed, an inline "Updates available — Update List" prompt appears.
- The preview reads from `sheet_version_rows` (DB), not from a live Sheets API call. This is fast, reproducible, and matches "what was last imported."

#### FR-6 — Update List (smart re-import)
Re-fetch the sheet and apply changes without re-scraping unchanged products.

> **As** Persona A,
> **I want** an "Update List" button that pulls my sheet edits in seconds,
> **So that** I can iterate on prices and titles without losing my scraped images.

**Acceptance criteria:**
- "Update List" is the **primary** action button after first sync.
- It calls `POST /campaigns/{id}/sheet/import` which:
  1. Re-reads the source (link or last upload — uploads are one-shot, so Update List is hidden if last source is upload).
  2. Computes a checksum vs. the latest `sheet_version`.
  3. If unchanged: shows toast "No changes detected" and writes nothing.
  4. If changed: shows an inline summary `"Will add X, remove Y, update Z — [Cancel] [Apply]"`.
  5. On Apply: writes a new `sheet_version`, upserts the `products` table by SKU, soft-deletes (`deleted_at`) products whose SKU disappeared, and re-scrapes only products whose `product_link` is new or changed.
- Manual image overrides (`ManualOverride` records, `products.py:222`) are always preserved.
- A WebSocket progress channel reports re-scrape progress for affected products.

#### FR-7 — Versioned snapshots
Every import is preserved as an immutable version.

> **As** Persona C,
> **I want** every import preserved with metadata,
> **So that** I can answer "what did the user import on date X" without asking them.

**Acceptance criteria:**
- A new `sheet_versions` row is written on Full Sync, Update List, and Upload.
- A new `sheet_version_rows` row is written per imported data row, preserving original `row_index`.
- Unknown/extra columns are stored in `extra` (JSONB) so future schema additions don't lose historical data.
- Checksum dedupe: if the new import has the same checksum as the latest version, no new version is written.
- Retention: last 10 versions per campaign; older versions auto-pruned.
- `GET /campaigns/{id}/sheet/versions` returns metadata only (id, version, source, imported_at, row_count, checksum) — no UI in v1.

#### FR-8 — Rationalized sync buttons
Replace today's Full/Fast Sync pair with three operations of distinct cost and effect.

| Button | Operation | Cost | Effect |
|---|---|---|---|
| **Update List** (primary) | Re-import + smart re-scrape on link change | Seconds | New version, products upserted, only changed-link products re-scraped |
| **Full Sync** (secondary) | Re-import + re-scrape everything | Minutes | New version, all products re-scraped, manual overrides preserved |
| **Quick price update** (overflow menu) | Re-import price + UTM only, existing SKUs only | Seconds | Reuses existing `fast_sync_worker`; never touches images |

**Acceptance criteria:**
- The first sync of a campaign hides "Update List" and "Quick price update" until at least one Full Sync has succeeded.
- Full Sync retains the existing confirm modal ("This re-scrapes everything…").
- Quick price update is hidden in a "More actions" overflow menu (kebab) — most users never need it.

### 5.2 Non-functional requirements

- **Latency:** `/verify` returns within 3 seconds on a 1,000-row sheet over a typical Google API connection.
- **Latency:** `/preview?limit=50` returns within 500 ms (it reads from Postgres, not Google).
- **Limits:** Upload max 5 MB, max 10,000 rows. Reject larger inputs with a clear error.
- **Backwards compatibility:** Existing campaigns with a `sheet_url` continue to work without migration. Their first post-deploy sync writes the first `sheet_version` row.
- **Observability:** Every verify and import call emits a structured log line with `campaign_id`, `source`, `error_code` (if any), `row_count`, and `duration_ms`.

---

## 6. Success Metrics

Framework: **HEART** + a single North Star.

### 6.1 North Star
**Sheet-to-first-successful-sync rate** — the percentage of users who, having opened the Sheets panel, complete their first successful import within the same session. Target: **+15 percentage points** over the current baseline.

### 6.2 HEART metrics

| Dimension | Metric | Target |
|---|---|---|
| Happiness | Post-import survey: "Did the import behave as you expected?" (yes/no) | ≥85% yes |
| Engagement | Update List clicks / campaign / week (after first sync) | ≥3 |
| Adoption | % of new campaigns using Upload tab vs. Link tab | Track only (no target — measures persona B share) |
| Retention | % of campaigns that re-import (Update List or Full Sync) within 7 days of creation | ≥60% |
| Task success | % of `/verify` calls that succeed on first attempt | ≥75% (vs. estimated ~40% today on first connect) |

### 6.3 Operational metrics

- Median `/verify` latency < 3 s.
- Median `/preview` latency < 500 ms.
- 0 data-loss incidents from version pruning (i.e., versions newer than the 10-cap retention are never pruned).

---

## 7. Scope

### 7.1 In scope

- New `SyncPanel` UI with segmented Link/Upload control.
- `POST /campaigns/{id}/sheet/verify` endpoint (read-only).
- `POST /campaigns/{id}/sheet/import` endpoint (Update List).
- `GET /campaigns/{id}/sheet/preview` endpoint.
- `GET /campaigns/{id}/sheet/versions` endpoint.
- File upload endpoint accepting `.xlsx` and `.csv`.
- Static template files (`.xlsx`, `.csv`).
- New tables: `sheet_versions`, `sheet_version_rows`.
- Soft-delete column on `products` (`deleted_at`).
- Smart re-scrape logic in the Update List worker (re-scrape only changed-link products).
- Renaming `Fast Sync` → `Quick price update` in UI (worker code reused as-is).

### 7.2 Out of scope (v1)

- Version-history browser UI.
- Diff visualization between versions.
- Snapshot rollback / restore.
- Per-row re-scrape from preview.
- Multi-tab Sheets (still reads first visible sheet, per `sheet_reader.py:160`).
- Real-time Sheets-change detection (webhooks / push).
- CSV import variants beyond UTF-8 (no auto-detection of encodings).

---

## 8. Technical Considerations

### 8.1 Architecture

**Frontend** — `frontend/src/components/layout/SyncPanel.tsx`
- Refactor into `SyncPanel/` folder with subcomponents: `SourcePicker`, `LinkTab`, `UploadTab`, `PreviewTable`, `ActionButtons`, `UpdateSummary`.
- Add new API client methods in `frontend/src/lib/api.ts`: `verifySheet`, `importSheet`, `previewSheet`, `uploadSheet`.

**Backend** — modules
- New `backend/app/modules/sheet_parser.py` — extracts header normalization (currently in `sheet_reader.py:77`) so it is shared between Sheets and uploaded `.xlsx`/`.csv` paths. Existing `read_sheet` is refactored to use it.
- New `backend/app/modules/sheet_version_store.py` — write/read `sheet_versions` and `sheet_version_rows`, compute checksum, prune old versions.
- New `backend/app/workers/import_worker.py` — Update List logic: diff vs. latest version, upsert products, soft-delete missing SKUs, enqueue scrape only for changed-link products.

**Backend** — endpoints
- New `backend/app/routers/sheet.py` (or extend `sync.py`) for `/verify`, `/import`, `/preview`, `/versions`, `/upload`.
- Static template files served from `backend/app/static/`.

**Database** — new schema, new migration

```sql
CREATE TABLE sheet_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    version INT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('link', 'upload')),
    source_ref TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    imported_by UUID NOT NULL REFERENCES users(id),
    row_count INT NOT NULL,
    checksum TEXT NOT NULL,
    UNIQUE (campaign_id, version)
);
CREATE INDEX ix_sheet_versions_campaign_imported
    ON sheet_versions (campaign_id, imported_at DESC);

CREATE TABLE sheet_version_rows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID NOT NULL REFERENCES sheet_versions(id) ON DELETE CASCADE,
    row_index INT NOT NULL,
    sku TEXT,
    product_link TEXT,
    extra JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX ix_sheet_version_rows_version
    ON sheet_version_rows (version_id, row_index);

ALTER TABLE products
    ADD COLUMN deleted_at TIMESTAMPTZ NULL;
```

### 8.2 API contracts

```
POST   /campaigns/{id}/sheet/verify
  body (link):   { source: "link", sheet_url: string }
  body (upload): multipart file
  response:
    { ok: bool,
      error_code: "INVALID_URL" | "NOT_FOUND" | "NOT_SHARED"
                | "EMPTY_SHEET" | "MISSING_COLUMNS" | null,
      headers_found: string[],
      missing_columns: string[],
      row_count: int,
      sheet_title: string | null }

POST   /campaigns/{id}/sheet/import
  body: { source: "link" | "upload", sheet_url?: string }
        (or multipart for upload)
  response: 202 { sync_job_id: UUID, summary: { added: int, removed: int, updated: int, unchanged: int } }

POST   /campaigns/{id}/sheet/full-sync       (existing)
POST   /campaigns/{id}/sheet/quick-price     (existing fast-sync, renamed in API)

GET    /campaigns/{id}/sheet/preview?version=latest&limit=50&offset=0
  response: { headers: string[], rows: object[], version: int, fetched_at: timestamp, row_count: int }

GET    /campaigns/{id}/sheet/versions
  response: [{ id, version, source, source_ref, imported_at, imported_by, row_count, checksum }]

GET    /static/sheet-template.xlsx
GET    /static/sheet-template.csv
```

### 8.3 Dependencies

- `openpyxl` (already present in backend `.venv`) for `.xlsx` parsing.
- Stdlib `csv` for `.csv` parsing.
- Existing `google-api-python-client` for Sheets access.
- No new frontend dependencies.

### 8.4 Security

- Upload endpoint: enforce 5 MB cap *before* reading into memory; reject MIME types other than `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and `text/csv`.
- All endpoints require `current_active_user` and verify campaign ownership (same pattern as `products.py:49`).
- `sheet_version_rows.extra` JSONB never executes; treat as opaque user data.
- Service-account credentials remain server-only; never returned to client.

### 8.5 Performance

- `/preview` reads from `sheet_version_rows` indexed by `(version_id, row_index)` — O(limit) regardless of total rows.
- Update List re-scrape enqueues only changed products → median Update List completes in <10 s for typical sheets.
- Checksum dedupe avoids writing redundant version rows on repeat clicks.

---

## 9. Design & UX Requirements

### 9.1 Panel layout (connected state)

```
┌─────────────────────────────────────────┐
│ Google Sheets               ● Connected │
│                                         │
│ [ Link ]  [ Upload ]    ← segmented     │
│                                         │
│ Connected to: "Q4 Catalog"              │
│ docs.google.com/spreadsheets/d/...      │
│                                         │
│ Service account email      [Copy]       │
│                                         │
│ ▸ Preview 47 products                   │
│                                         │
│ [ Update List ]            ← primary    │
│ [ Full Sync ]              ← secondary  │
│   ⋯ More actions                        │
│      └ Quick price update               │
│                                         │
│ Change sheet URL                        │
└─────────────────────────────────────────┘
```

### 9.2 Empty (link) state
- URL input + "Verify & Connect" button.
- Service account chip (existing).
- "Need a starting point? Download template" link below.

### 9.3 Upload state
- Drop zone: "Drop .xlsx or .csv here, or browse".
- "Download template" link prominent.
- After upload: shows row count and detected columns; same connected layout.

### 9.4 Error states (verify failures)
- Inline red banner above the action button.
- Title + recovery CTA per error type:
  - `INVALID_URL`: "URL doesn't look like a Google Sheets link."
  - `NOT_FOUND`: "Sheet not found. Check the URL."
  - `NOT_SHARED`: "Service account doesn't have access. [Copy email]"
  - `EMPTY_SHEET`: warning chip "Sheet is empty — connect anyway?"
  - `MISSING_COLUMNS`: "Missing column: `product_link`. [Download template]"

### 9.5 Update summary inline panel

```
Update will:
  + Add 3 products
  − Remove 1 product
  ≠ Update 5 products
[ Cancel ] [ Apply ]
```

### 9.6 Accessibility
- All buttons have aria-labels.
- Preview table is keyboard-navigable (arrow keys cycle rows).
- Error banners are `role="alert"`.
- WCAG AA contrast on all text/background pairs.

---

## 10. Timeline & Milestones

| Phase | Scope | Estimated effort |
|---|---|---|
| **M1 — Schema & APIs** | Migration for `sheet_versions`, `sheet_version_rows`, `products.deleted_at`. `/verify`, `/preview`, `/versions` endpoints. `sheet_parser.py` refactor. Static templates. | 1.5 weeks |
| **M2 — Upload + Update List worker** | Upload endpoint and parser. `import_worker.py` with smart re-scrape. New `/import` endpoint. Backwards-compatible bridge for existing campaigns. | 1.5 weeks |
| **M3 — Frontend redesign** | New `SyncPanel` with Link/Upload tabs, preview table, three-button hierarchy, update summary inline panel, error states. | 2 weeks |
| **M4 — QA, telemetry, polish** | End-to-end tests, metric instrumentation, copy review, accessibility audit. | 1 week |

**Total:** ~6 weeks. Specific dates TBD with engineering.

---

## 11. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `.xlsx` parsing edge cases (merged cells, formulas, hidden rows) | Medium | Medium | Use `openpyxl` `data_only=True`; document edge cases in instructions sheet; reject merged-cell headers with a clear error. |
| Existing campaigns missing `sheet_version` history pre-migration | High | Low | First post-deploy sync writes version 1; no backfill needed. Version-history endpoint returns empty for un-synced campaigns. |
| Soft-delete on `products` introduces NULL handling everywhere | Medium | High | Add a single `Product.active` query helper used by all readers; run one-time audit of all `select(Product)` call sites. |
| Smart re-scrape mis-detects "changed link" (e.g., trailing slash) | Medium | Medium | Normalize URLs (strip trailing slash, lowercase host) before comparison. |
| Users uploading huge sheets (>10k rows) | Low | Medium | Hard cap at 10k rows; reject server-side with a clear error mentioning the limit. |
| Sheet checksum collision → false negative on changes | Negligible | Medium | Use SHA-256 over canonical-sorted JSON of normalized rows. |
| Removing Fast Sync surprises power users who relied on it | Low | Low | Keep functionality under "Quick price update" in overflow menu; release notes explain the rename. |
| Version pruning races with read | Low | Low | Use `DELETE WHERE imported_at < (SELECT MIN(...) FROM (latest 10))` in a single transaction. |

---

## 12. Dependencies & Assumptions

### 12.1 Dependencies
- Service-account credentials remain configured (`settings.google_sheets_credentials_json`).
- Postgres ≥12 for JSONB indexing (already in use).
- ARQ Redis worker queue (already in use).
- Existing `gateway.send_progress` WebSocket channel for sync progress.

### 12.2 Assumptions
- Most users will use Link tab; Upload is a secondary path (we do not need to optimize Upload for high volume).
- Soft-delete is acceptable; no current product flow assumes deletion is hard.
- Manual image overrides in `ManualOverride` are the single source of truth for "do not overwrite this product's image."
- Sheets API quota limits (60 req/min/user) are sufficient at expected verify+import frequency.

---

## 13. Open Questions

1. **Update summary confirmation** — should pure-edit updates (no add/remove) skip the inline summary and apply silently? Current spec: skip confirmation only when the diff is empty (no-op). Confirm this is the desired behavior or whether even pure-edit updates should require confirmation.
2. **Version retention cap** — 10 is a guess. Should this be configurable per campaign, or globally tunable?
3. **Upload + verify** — current spec requires uploading the file twice (once for verify, once for import). Acceptable, or should we cache uploads server-side for 5 min keyed by an opaque token?
4. **Soft-deleted products** — should they appear in the preview table, in the products list (greyed out), or be filtered out entirely? Current spec: filtered out everywhere except via an internal `?include_deleted=true` flag.
5. **Telemetry consent** — the post-import survey ("Did the import behave as you expected?") needs UX review and a privacy check before shipping.
6. **Plural sheet tabs** — Sheets with multiple tabs are read first-tab-only today. Some users may expect tab selection; out of scope here, but should we surface a warning when the user's sheet has >1 tab?

---

## 14. Appendix

### 14.1 Reference: existing files touched
- `frontend/src/components/layout/SyncPanel.tsx` — full rewrite
- `frontend/src/lib/api.ts` — add 4 new client methods
- `backend/app/modules/sheet_reader.py` — refactor header-norm logic into `sheet_parser.py`
- `backend/app/workers/fast_sync_worker.py` — unchanged behavior, surfaced under "Quick price update"
- `backend/app/workers/sync_worker.py` — emit `sheet_versions` write on Full Sync
- `backend/app/routers/sync.py` — extend or split into `sheet.py`
- `backend/app/models/product.py` — add `deleted_at`
- New: `backend/app/models/sheet_version.py`, `backend/app/migrations/versions/<new>_sheet_versions.py`

### 14.2 Glossary
- **Source** — origin of the imported data: Google Sheets URL (`link`) or uploaded file (`upload`).
- **Version** — an immutable snapshot of one import. Identified by `(campaign_id, version)`.
- **Smart re-scrape** — scraping only those products whose `product_link` is new or changed since the previous version.
- **Checksum** — SHA-256 of the normalized rows JSON; used to skip writing duplicate versions.
- **Soft-delete** — marking a product as `deleted_at = now()` instead of removing the row, preserving foreign-key references and the option to restore.
