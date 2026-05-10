# UI/UX Spec — Google Sheets Integration

**Source PRD:** `PRD-google-sheets-integration.md`
**Target surface:** `frontend/src/components/layout/SyncPanel.tsx` (full rewrite)
**Status:** Draft for design / engineering handoff
**Author:** Generated 2026-05-10

---

## How to read this spec

Part A establishes the UX foundations (mental models, IA, affordances, cognitive load, states, flow integrity). Part B derives concrete visual specs from those foundations. **Do not implement Part B without first reading Part A** — the visual decisions reference foundation-pass IDs (e.g., "P3-A4") and lose meaning otherwise.

The PRD covers FR-1…FR-8. A coverage matrix at the end of Part A confirms every FR appears in at least one foundation pass.

---

# PART A — UX FOUNDATIONS

---

## Pass 1 — Mental Model & User Intent

### Primary user intent (one sentence per persona)

| Persona | Intent |
|---|---|
| **A — Campaign Manager** | "Get my product list into the system, see that it landed correctly, and pull in my edits later without losing the images that were already scraped." |
| **B — One-shot Importer** | "Drop my file in, confirm it parsed, and never touch this panel again." |
| **C — Internal Operator** | "Look up what was imported, when, and from where, to debug a campaign." (No UI in v1 — API only. Mentioned for completeness.) |

### Likely misconceptions

| # | Misconception | Why it forms | Where to correct |
|---|---|---|---|
| M1 | "Update List re-scrapes everything (so it's slow / risky)." | Today's "Full Sync" is the only refresh users know. | Microcopy on the button (`Update List` subtitle: "Pull sheet edits — only re-scrapes new/changed links"); Update Summary panel itemizes what will change. |
| M2 | "If I upload a file, I can edit it later via Update List." | Upload feels like a "live" connection. | Hide Update List when latest source is `upload`; replace with "Upload new file" affordance. |
| M3 | "Quick price update will refresh everything I changed." | The word "update" overlaps Update List. | Bury Quick price update in overflow menu; subtitle: "Prices & UTM only. Existing SKUs only. Skips images." |
| M4 | "Verify saves my sheet / starts a sync." | The button sits where Connect used to. | Button label is "Verify & Connect"; copy under success state explicitly says "Nothing imported yet — click Full Sync to begin." |
| M5 | "The preview is live data from Google." | Preview looks like a spreadsheet. | Caption beneath preview: "Snapshot from version N — imported [time ago]"; refresh icon explicitly fetches the live sheet for comparison. |
| M6 | "If a row disappears from my sheet, the product is gone forever." | Soft-delete is invisible. | Update Summary lines say "Remove 1 product (kept in history)"; Open Question 4 below. |

### UX principles to reinforce

- **Verify is read-only.** Connecting and importing are separate steps.
- **Versions are immutable.** A new import never destroys a previous one.
- **Smart re-scrape preserves manual work.** Manual image overrides survive every operation.
- **Cost matches button prominence.** The cheapest, safest action is the most prominent.

---

## Pass 2 — Information Architecture

### All user-visible concepts

Source mode (Link/Upload) · Sheet URL · Uploaded filename · Service-account email · Connection state · Sheet title · Detected columns · Required-column status · Row count · Preview rows · Version number · Last imported timestamp · Source of last import · Update List action · Full Sync action · Quick price update action · Update summary (added / removed / updated counts) · Cancel/Apply on summary · Re-scrape progress · Template downloads (.xlsx / .csv) · Error banners (5 codes) · Change-source affordance.

### Grouped structure

#### Group 1 — Source & Connection
| Concept | Tier | Rationale |
|---|---|---|
| Source mode segmented control (Link / Upload) | **Primary** | Decision gate before anything else can happen. |
| Sheet URL input *(Link mode)* | Primary | The single input that unblocks the panel. |
| File dropzone *(Upload mode)* | Primary | Same role as URL input on the other tab. |
| Verify & Connect button | Primary | The action that resolves the empty state. |
| Connection chip (sheet title + source link) | Primary (post-connect) | Confirms which sheet is bound to this campaign. |
| Service-account email + Copy | **Secondary** | Only needed when resolving `NOT_SHARED`. Rendered inline at all times for discoverability, but visually quiet. |
| "Change source" affordance | **Hidden** | Disclosed in an overflow / link beneath the chip; rare action. |

#### Group 2 — Data Visibility
| Concept | Tier | Rationale |
|---|---|---|
| Row count + version number | Primary | Single line of truth: "47 products · v3 · imported 12 min ago". |
| Detected columns chip list | Secondary | Shown in the verify result and beneath the preview header; reassures users that aliases were recognized. |
| Preview table | **Hidden by default** | Disclosed via "▸ Preview 47 products" toggle. Rationale: most returning users do not need to re-verify. |
| Preview refresh icon | Secondary | Inside preview header; only relevant once preview is open. |
| "Updates available" inline prompt | Primary (when present) | Surfaces only when refresh detects a delta. |
| Version history (full list) | Hidden / API-only in v1 | Per PRD §3.2 non-goal. |

#### Group 3 — Actions
| Concept | Tier | Rationale |
|---|---|---|
| Update List | **Primary post-first-sync** | The expected day-to-day operation. |
| Full Sync | **Secondary** (or Primary pre-first-sync) | First-time mandatory; afterward rare. |
| Quick price update | **Hidden** (overflow menu) | Power-user shortcut, easy to misuse. |
| Update Summary inline panel | Primary (transient) | Appears only between Update List click and Apply. |
| Cancel / Apply | Primary (within summary) | The decision the summary exists to support. |

#### Group 4 — Feedback & History
| Concept | Tier | Rationale |
|---|---|---|
| Error banners (5 codes) | Primary (transient) | Block progress until resolved or dismissed. |
| Re-scrape progress | Primary (transient) | Replaces the action group while running. |
| Toasts (no-change, success, failure) | Secondary | Non-blocking confirmations. |
| Template download links | Secondary | Two locations: empty state and `MISSING_COLUMNS` error. |
| Last-imported timestamp | Secondary | Part of the row-count line. |

### IA principle

The panel is a single column with three vertical zones:
**Source → Data → Actions**, with **Feedback** overlaying whichever zone it relates to. The user's eye travels top-to-bottom and rarely needs to backtrack.

---

## Pass 3 — Affordances & Action Clarity

### Affordance map

| ID | Action | Visual / interaction signal |
|---|---|---|
| P3-A1 | Switch source mode | Segmented control; single click; selected pill is filled, the other is outlined. Switching does **not** clear the URL field (preserves user input) but resets verification status. |
| P3-A2 | Type / paste sheet URL | Standard text input with monospace font and `placeholder="https://docs.google.com/spreadsheets/d/…"`. |
| P3-A3 | Verify & connect | Filled primary button labeled "Verify & Connect". Shows spinner + text "Verifying…" while loading. Disabled when input is empty or when source is `upload` and no file is selected. |
| P3-A4 | Drop / browse file | Dashed-border dropzone with a centered "Drop .xlsx or .csv here, or browse" label. Hover/drag-over: border becomes solid + tinted background. Click anywhere on zone opens native file picker. |
| P3-A5 | Copy service-account email | Inline pill with copy-icon affordance; on click the icon swaps to a checkmark for 2 s and the row tooltip says "Copied". |
| P3-A6 | Expand preview | Caret + label ("▸ Preview 47 products"). Click toggles. The caret rotates to ▾. Keyboard: Enter/Space. |
| P3-A7 | Refresh preview | Small circular-arrow icon inside the preview table header. Tooltip: "Check the source for updates". On click: spinner replaces icon; result is a banner inside the preview, not a destructive write. |
| P3-A8 | Update List | Filled **primary** button. Subtitle line beneath label (small, muted): "Pull sheet edits". |
| P3-A9 | Full Sync | Outlined **secondary** button. Subtitle: "Re-scrape everything". Triggers confirm modal. |
| P3-A10 | Open more actions | Kebab (⋯) icon button right-aligned beneath Full Sync. Click opens a small menu with one item: "Quick price update". |
| P3-A11 | Quick price update | Menu item; on click goes straight to action (no confirm) — it is the safest of the three. Toast on completion. |
| P3-A12 | Apply update | Filled primary button inside the Update Summary panel. |
| P3-A13 | Cancel update | Outlined button beside Apply. Discards the diff; no version is written. |
| P3-A14 | Download template | Plain text link with download icon. Clicking initiates a static file download — no spinner, no dialog. |
| P3-A15 | Change source | Plain text link beneath the connection chip ("Change sheet URL"). Opens an inline edit of the URL field; user must Verify again. |

### Affordance rules

- **R1 — Filled = commits state. Outlined = navigational or reversible.** Verify, Update List, Full Sync (after confirm), Apply Update, and Quick price update are all state-committing — Verify is the only filled button that does *not* write to the DB, and its subtitle clarifies that.
- **R2 — Destructive or expensive actions require confirm.** Full Sync gets a confirm modal. Quick price update does not (cheap, scoped). Update List shows the diff summary, which functions as the confirm surface.
- **R3 — Read-only data is visually flat.** Preview table cells, version line, detected columns chips: no shadow, no border, no hover state.
- **R4 — Tab/source switches are local.** No network call; no destructive write; no spinner.
- **R5 — One primary per zone.** At any moment there is exactly one filled primary button visible in the action zone. (Verify before connect; Update List after first sync; Apply during summary.)

---

## Pass 4 — Cognitive Load & Decision Minimization

### Friction points

| ID | Moment | Type | Simplification |
|---|---|---|---|
| P4-F1 | "Should I use Link or Upload?" | Choice | Default to Link tab. Upload tab carries a subtle subtitle: "For one-shot imports — no live updates." Decision is reversible (P3-A1). |
| P4-F2 | "Which sync button do I press first?" | Choice | Pre-first-sync: only Full Sync is visible. Update List and the kebab menu render only after the first successful Full Sync (PRD FR-8 acceptance). |
| P4-F3 | "What does Update List actually do?" | Uncertainty | (a) Subtitle on the button. (b) The Update Summary panel never auto-applies — user always sees the diff before commit. |
| P4-F4 | "Is my sheet edit picked up yet?" | Uncertainty | Preview's refresh icon (P3-A7) is the cheap probe; result is "Updates available — Update List" inline, not a separate dashboard. |
| P4-F5 | Waiting on `/verify` | Waiting | Button shows "Verifying…" within 100 ms; PRD §5.2 caps p95 at 3 s. No optimistic UI — verify is short enough to wait through. |
| P4-F6 | Waiting on Update List re-scrape | Waiting | Action zone collapses into a progress card driven by the existing `gateway.send_progress` WebSocket. User can navigate away; on return, the panel resumes the live state. |
| P4-F7 | "Did I overwrite my manual image?" | Uncertainty | Toast after every Update List/Full Sync: "N images preserved (manual overrides)." |
| P4-F8 | "Where do I get the right column names?" | Uncertainty | Template links appear in two locations: empty state and inside the `MISSING_COLUMNS` error. |

### Defaults introduced

- **D1** — Source = Link.
- **D2** — Preview = collapsed.
- **D3** — Post-first-sync action group = `[Update List]` filled, `[Full Sync]` outlined, kebab.
- **D4** — Verify fires only on click (PRD FR-1 explicit).
- **D5** — Update Summary appears only when the diff is non-empty; no-op imports show a single toast and skip the summary entirely (recommendation against PRD Open Question 1).
- **D6** — Quick price update menu item is hidden until at least one Full Sync has succeeded.

### Progressive disclosure rules

| Surface | Visible when |
|---|---|
| Connection chip | Sheet/file is verified successfully. |
| Preview table contents | User clicks the disclosure caret. |
| Update List + kebab | At least one Full Sync has succeeded for this campaign. |
| Update Summary panel | Update List click produced a non-empty diff. |
| Re-scrape progress card | A sync job is in flight for this campaign. |
| Service-account email "Copy" tooltip | Hover or focus. |

---

## Pass 5 — State Design & Feedback

State matrix per element. Columns: **User sees / understands / can do**.
States: **Empty · Loading · Success · Partial · Error**.

### Source picker (segmented control)

| State | User sees | User understands | User can do |
|---|---|---|---|
| Empty (initial) | "[Link] [Upload]" with Link selected | This is the source choice | Click either tab |
| Loading | n/a | — | — |
| Success | Selected pill highlighted | Their choice is registered | Switch back |
| Partial | n/a | — | — |
| Error | n/a | — | — |

### Sheet URL input *(Link tab)*

| State | User sees | User understands | User can do |
|---|---|---|---|
| Empty | Placeholder URL, button disabled | Needs a URL | Paste / type |
| Loading | Input read-only, button shows "Verifying…" with spinner | Verification in flight | Wait |
| Success | Input collapses; connection chip replaces it | Connected to a specific sheet | Change sheet, proceed to actions |
| Partial | Connected chip + warning chip "Sheet is empty" | Connected but no rows | Connect anyway / cancel |
| Error | Input retained; red banner above button per error code (see below) | Why it failed + how to fix | Apply suggested CTA |

### Upload dropzone *(Upload tab)*

| State | User sees | User understands | User can do |
|---|---|---|---|
| Empty | Dashed dropzone, "Drop .xlsx or .csv here, or browse", template link below | Where to put the file | Drop or browse |
| Loading | Filename + spinner + "Uploading…" | Upload in progress | Wait, Cancel |
| Success | Filename, row count, detected columns; transitions to connection chip | File parsed | Proceed to Full Sync |
| Partial | Filename + warning "Sheet is empty" | File ok but no rows | Upload another / continue |
| Error | Red banner with code-specific message; dropzone reset | Why it failed | Re-upload / download template |

### Connection chip

| State | User sees | User understands | User can do |
|---|---|---|---|
| Empty | Hidden until verified | — | — |
| Loading | n/a | — | — |
| Success | "Connected to: *Q4 Catalog*" + truncated source URL + "Change" link | Which sheet/file is bound | Click "Change" |
| Partial | Same + small "Last source: Upload" tag | Connected via upload (Update List unavailable) | Replace via "Change" |
| Error | Stale chip + warning "Last refresh failed" | Connection lost since last verify | Re-verify |

### Preview table (within disclosure)

| State | User sees | User understands | User can do |
|---|---|---|---|
| Empty (collapsed) | "▸ Preview 47 products" | Data is available, hidden | Expand |
| Loading | "Loading preview…" skeleton rows | Fetching from DB | Wait |
| Success | Header row + first 50 data rows + pagination | What was last imported | Scroll, paginate, refresh |
| Partial | Banner inside table: "Updates available — [Update List]" | Live sheet differs from snapshot | Click Update List |
| Error | "Preview unavailable" placeholder + retry | Read failed | Retry, collapse |

### Update List button

| State | User sees | User understands | User can do |
|---|---|---|---|
| Empty (pre-first-sync) | Hidden | — | — |
| Loading | "Checking for updates…" with spinner | Diff in progress | Wait |
| Success — no changes | Toast "No changes detected" | Nothing to do | Continue |
| Success — changes | Update Summary panel renders | Review pending diff | Apply or Cancel |
| Error | Red toast "Update failed: <reason>" | Action did not run | Retry |

### Update Summary panel

| State | User sees | User understands | User can do |
|---|---|---|---|
| Empty | Hidden | — | — |
| Loading | n/a (rendered after diff completes) | — | — |
| Success | "+ Add 3 · − Remove 1 (kept in history) · ≠ Update 5" + Cancel/Apply | What will happen on Apply | Apply / Cancel |
| Partial | Same + "Will re-scrape 2 products with new links" | Some products will be re-scraped | Apply / Cancel |
| Error | n/a | — | — |

### Full Sync button

| State | User sees | User understands | User can do |
|---|---|---|---|
| Empty (pre-first-sync) | Filled primary | The first thing to click | Click → confirm modal |
| Empty (post-first-sync) | Outlined secondary | Heavier alternative to Update List | Click → confirm modal |
| Loading | Progress card replaces the action zone | Sync in flight | Navigate away (job continues) |
| Success | Action zone restored; toast "Synced N products"  | Done | Inspect preview |
| Partial | Toast "Synced N of M products — see logs" | Some failures | Open logs (future), retry |
| Error | Red toast "Full Sync failed: <reason>" | Action did not run | Retry |

### Quick price update *(overflow menu item)*

| State | User sees | User understands | User can do |
|---|---|---|---|
| Empty (pre-first-sync) | Item not in menu | — | — |
| Loading | Menu closes; small inline spinner near kebab | Quick action running | Wait |
| Success | Toast "Prices updated for N SKUs" | Prices refreshed; images untouched | Continue |
| Partial | Toast "Prices updated for N of M SKUs" | Some skipped (missing SKU) | Open log |
| Error | Red toast "Quick price update failed: <reason>" | Did not run | Retry |

### Error banners (Verify failures, FR-1)

| Error code | Banner title | Body | Recovery CTA |
|---|---|---|---|
| `INVALID_URL` | "URL doesn't look like a Google Sheets link." | "Make sure the link starts with `https://docs.google.com/spreadsheets/`." | (none — fix and re-Verify) |
| `NOT_FOUND` | "Sheet not found." | "Double-check the URL — the sheet may have been moved or deleted." | (none) |
| `NOT_SHARED` | "Service account doesn't have access." | "Share the sheet with the service-account email below as Viewer or Editor." | **[Copy email]** |
| `EMPTY_SHEET` | "Sheet is empty." (warning, yellow) | "We connected, but found no rows. You can connect anyway." | **[Connect anyway]** |
| `MISSING_COLUMNS` | "Missing column: `product_link`." (or list) | "Your sheet must include `sku` and `product_link`. Use the template to get the headers right." | **[Download template]** |

Banners use `role="alert"`, are dismissable only by re-verify (not by an X — an X would let users continue with a broken state).

---

## Pass 6 — Flow Integrity Check

### First-time user path

```
empty panel
  → (optional) Download template
  → fill template OR paste URL
  → Verify & Connect
    ├─ error → fix per banner CTA → re-verify
    └─ success → connection chip + (only) [Full Sync]
  → Full Sync → confirm → progress → toast "Synced N products"
  → action zone reveals Update List + kebab
```

### Returning user path

```
connected panel
  → edit sheet outside the app
  → Update List
    ├─ no changes → toast "No changes detected" (D5)
    └─ changes → Update Summary
        → Cancel (no version written)
        OR
        → Apply → progress (re-scrape only changed-link rows) → toast
```

### Risk table

| ID | Risk | Where | Mitigation |
|---|---|---|---|
| P6-R1 | User clicks Full Sync when only a price changed (wastes minutes). | Post-first-sync action zone. | Visual hierarchy: Update List filled primary, Full Sync outlined; subtitles clarify cost. |
| P6-R2 | User uploads a file then expects Update List to pull future edits. | Connection chip after Upload. | When source = upload, Update List is hidden, replaced by "Upload new file" affordance; chip shows "Source: Upload (one-shot)". |
| P6-R3 | User dismisses `NOT_SHARED` banner without copying SA email. | Verify error state. | Banner has no dismiss; the only way past is to re-verify, and the [Copy email] CTA is the most prominent element in the banner. |
| P6-R4 | User assumes preview is live and acts on stale prices. | Connected steady state. | Caption beneath preview header: "Snapshot from version N — [refresh icon] check live". On refresh: explicit "Updates available" or "No changes". |
| P6-R5 | User deletes a row from the sheet, panics that history is lost. | Update Summary "Remove 1 product". | Summary line reads "Remove 1 product (kept in history)"; tooltip explains soft-delete. |
| P6-R6 | User runs Quick price update expecting full refresh. | Overflow menu. | Menu item subtitle: "Prices & UTM only. Existing SKUs only. Skips images." |
| P6-R7 | User edits a SKU's link, doesn't realize re-scrape ran. | Post-Update List toast. | Toast lists "N images re-scraped, M preserved (manual overrides)." |
| P6-R8 | First-time user mistakes Verify for Sync. | Empty state. | After Verify success, helper text: "Verified — nothing imported yet. Click Full Sync to begin." |

### Visibility decisions

**Must be visible at all times (post-connect):**
- Connection chip (which sheet)
- Row count + version + last-imported (one line)
- Action zone (current primary action)

**Visible on demand:**
- Preview table (P3-A6 toggle)
- Service-account email (always rendered, but quiet)
- Quick price update (kebab menu)

**Implied / never shown in v1:**
- Version history list (API only per PRD §3.2)
- Per-row scrape status
- Diff visualization between versions

### Hard UX constraints carried into Part B

- **C1** — Verify is read-only. The button label and successful-state copy must say so.
- **C2** — Exactly one filled primary button is visible in the action zone at any moment.
- **C3** — Update List never auto-applies. The summary is the confirm.
- **C4** — Update List is invisible when the latest source is Upload.
- **C5** — Quick price update never appears in the main action group.
- **C6** — Error banners do not have a dismiss control. They clear only on successful re-verify.
- **C7** — Manual image override preservation must be confirmed in every post-sync toast.
- **C8** — Soft-deletes must be labeled "(kept in history)" in user-facing copy.

### FR coverage matrix (sanity check)

| FR | Pass 2 (IA) | Pass 3 (affordance) | Pass 5 (state) | Part B reference |
|---|---|---|---|---|
| FR-1 Verify | Group 1 | P3-A3 | URL input + Error banners | §B-Empty layouts, §B-Banner component |
| FR-2 Column validation | Group 1 ("Detected columns") | (Verify chain) | `MISSING_COLUMNS` row | §B-Banner component |
| FR-3 Upload | Group 1 | P3-A4 | Upload dropzone | §B-Empty (Upload variant), §B-Dropzone component |
| FR-4 Template | Group 4 | P3-A14 | (link in two locations) | §B-Empty layouts, §B-Banner (`MISSING_COLUMNS`) |
| FR-5 Preview | Group 2 | P3-A6, P3-A7 | Preview table | §B-Connected layout, §B-Preview component |
| FR-6 Update List | Group 3 | P3-A8, P3-A12, P3-A13 | Update List + Update Summary | §B-Connected layout, §B-Update Summary component |
| FR-7 Versions | Group 4 (history line) | (none — passive) | Version line in row count | §B-Connected layout (row-count line) |
| FR-8 Three-button hierarchy | Group 3 | P3-A8 / P3-A9 / P3-A11 | Update List / Full Sync / Quick price update tables | §B-Action group component |

---

# PART B — VISUAL SPECIFICATIONS

> Every spec below references a foundation-pass ID. If a future request contradicts a Part-A constraint (C1–C8), revise Part A first.

---

## §B-1 Screen layouts

### B-1.1 Empty state — Link tab (first-time user)

```
┌─────────────────────────────────────────────────┐
│ Google Sheets                       ○ Not connected │
│                                                 │
│ ┌──────────┬──────────┐                         │
│ │  Link    │  Upload  │   ← segmented (P3-A1)   │
│ └──────────┴──────────┘                         │
│                                                 │
│ Sheet URL                                       │
│ ┌─────────────────────────────────────────────┐ │
│ │ https://docs.google.com/spreadsheets/d/…    │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ Service account: svc@…iam.gserviceaccount.com   │
│   Share the sheet with this email as Editor.    │
│   [📋 Copy email]                                │
│                                                 │
│ [ Verify & Connect ]    ← filled primary (P3-A3)│
│                                                 │
│ Need a starting point? ⤓ Download template      │
└─────────────────────────────────────────────────┘
```

Annotations: button is disabled until input has at least one character. Placeholder text is muted. Service account block is always visible (D2 rationale: low-frequency but high-stakes when needed; users do not know to look in settings for it).

### B-1.2 Empty state — Upload tab

```
┌─────────────────────────────────────────────────┐
│ Google Sheets                       ○ Not connected │
│                                                 │
│ ┌──────────┬──────────┐                         │
│ │  Link    │  Upload  │                         │
│ └──────────┴──────────┘                         │
│                                                 │
│ ┌╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶┐ │
│ ╷                                              ╷│
│ ╷       ⤴  Drop .xlsx or .csv here             ╷│
│ ╷             or  [browse]                     ╷│
│ ╷                                              ╷│
│ ╷       Max 5 MB · Max 10,000 rows             ╷│
│ └╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶┘ │
│                                                 │
│ ⤓ Download template (.xlsx · .csv)              │
│                                                 │
│ Note: uploads are one-shot. To pull future      │
│ edits automatically, use a Google Sheet link.   │
└─────────────────────────────────────────────────┘
```

Drag-over: dashed border becomes solid + tinted background (P3-A4).

### B-1.3 Connected steady state (post-first-sync)

```
┌─────────────────────────────────────────────────┐
│ Google Sheets                          ● Connected │
│                                                 │
│ ┌──────────┬──────────┐                         │
│ │  Link    │  Upload  │  ← reflects current src │
│ └──────────┴──────────┘                         │
│                                                 │
│ Connected to: "Q4 Catalog"                      │
│ docs.google.com/spreadsheets/d/abc…             │
│ 47 products · v3 · imported 12 min ago          │
│ Detected columns: sku · product_link · price …  │
│                                                 │
│ Service account svc@…  [📋 Copy]                 │
│                                                 │
│ ▸ Preview 47 products                           │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ [ Update List ]    ← filled primary (P3-A8) │ │
│ │ [  Full Sync   ]   ← outlined  (P3-A9)      │ │
│ │                              ⋯ More actions │ │
│ │                                  ↳ Quick price update │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ Change sheet URL                                │
└─────────────────────────────────────────────────┘
```

Constraint check: C2 satisfied (Update List is the sole primary). C5 satisfied (Quick price update is in the kebab). C7 will be satisfied in the post-sync toast copy (see §B-3).

### B-1.4 Update Summary inline panel

Replaces the action group inline (does not push the panel taller than the viewport — if needed the action group scrolls into the summary).

```
┌─────────────────────────────────────────────────┐
│ Update will:                                    │
│   + Add      3 products                         │
│   − Remove   1 product   (kept in history)      │
│   ≠ Update   5 products                         │
│       ↳ 2 will be re-scraped (link changed)     │
│                                                 │
│   [ Cancel ]            [ Apply ] ← primary     │
└─────────────────────────────────────────────────┘
```

If diff is empty: panel never renders; toast "No changes detected" appears instead (D5).

### B-1.5 Error banner variants (above Verify button)

```
┌─────────────────────────────────────────────────┐
│ ⚠  Service account doesn't have access.         │
│    Share "Q4 Catalog" with the email below as   │
│    Viewer or Editor, then verify again.         │
│    [📋 Copy svc@…iam.gserviceaccount.com]        │
└─────────────────────────────────────────────────┘
```

Variants for each of the 5 error codes follow the same shape. Color: yellow/warning for `EMPTY_SHEET`; red/danger for the other four.

### B-1.6 Re-scrape progress (replaces action zone)

```
┌─────────────────────────────────────────────────┐
│ Re-scraping 2 of 5 changed products…            │
│ ████████████░░░░░░░░░░  40%                     │
│ Last: SKU-1029  ✓                                │
│                                                 │
│ You can leave this panel — sync will continue.  │
└─────────────────────────────────────────────────┘
```

Progress is driven by the existing `gateway.send_progress` WebSocket. On completion the action zone is restored and a toast fires (see §B-3).

---

## §B-2 Component specifications

### B-2.1 Segmented control `<SourcePicker>`

- Two pills, equal width, full panel width.
- Selected pill: filled background, text in inverse color.
- Unselected pill: text-only, muted.
- Click switches mode instantly; **does not** clear input fields (preserves typed URL or just-uploaded filename) but **does** reset verification status (banner clears, connection chip hides until re-verify).

### B-2.2 Verify button `<VerifyButton>`

| Sub-state | Label | Spinner | Disabled |
|---|---|---|---|
| Idle, input empty | "Verify & Connect" | — | yes |
| Idle, input filled | "Verify & Connect" | — | no |
| Loading | "Verifying…" | yes | yes |
| Connected | (hidden — chip replaces) | — | — |

Latency budget: 100 ms to enter Loading; 3 s p95 total per PRD §5.2.

### B-2.3 Connection chip `<ConnectionChip>`

- Single line: `Connected to: "<title>"` with title in semibold.
- Subline: source URL in monospace, truncated mid-string with ellipsis, full URL in tooltip.
- Subline 2: `47 products · v3 · imported 12 min ago` (relative time updates each minute the panel is mounted).
- Subline 3: `Detected columns:` followed by chips for each column normalised by `sheet_parser.py`.
- Right-aligned: `Change` link.
- When source = upload, append a small tag `[Upload (one-shot)]` after the title (P6-R2).

### B-2.4 Service-account row `<ServiceAccountRow>`

- Always rendered when not yet connected and after any verification error of code `NOT_SHARED`.
- After successful connect, shown in a quieter, smaller form beneath the chip.
- Copy interaction (P3-A5): icon→checkmark for 2 s, tooltip "Copied".
- Email displayed in monospace; selectable text.

### B-2.5 Dropzone `<UploadDropzone>`

| Sub-state | Visuals | Interaction |
|---|---|---|
| Idle | Dashed border, centered prompt, limits subtext | Click anywhere opens file picker |
| Drag-over | Solid border, tinted background | Drop accepted |
| Uploading | Filename + progress bar + Cancel link | Cancel aborts xhr |
| Error | Red border + inline message + Retry | Click resets to Idle |
| Success | Filename + ✓ + row count → transitions to ConnectionChip | — |

Client-side guards before upload: extension check (`.xlsx`/`.csv`); size check ≤ 5 MB. Server still re-validates per PRD §8.4.

### B-2.6 Preview table `<PreviewTable>`

- Default state: collapsed, disclosure label `▸ Preview <rowCount> products`.
- Expanded: virtualized table; header row sticky; first 50 rows; pagination controls at bottom (`< 1 / 4 >`).
- Columns rendered dynamically from `headers` field in `/preview` response — do not hard-code.
- Header bar of the table contains: title "Preview", small refresh icon (P3-A7) right-aligned, caption "Snapshot from v3 — [refresh] check live".
- On refresh result:
  - No diff → caption updates to "No changes since last import."
  - Diff present → inline banner inside table body: "Updates available — [Update List]" (clicking jumps focus to Update List button).
- Soft-deleted rows are excluded from the preview by default (Open Question 4 recommendation below).

### B-2.7 Action group `<ActionButtons>`

| Surface | Pre-first-sync | Post-first-sync |
|---|---|---|
| Update List (filled primary) | hidden | shown |
| Full Sync (filled primary) | shown | (becomes outlined secondary) |
| Kebab menu | hidden | shown, contains "Quick price update" |
| Subtitles under each button | n/a | "Pull sheet edits" / "Re-scrape everything" / "Prices & UTM only…" |

Full Sync triggers the existing confirm modal. Update List triggers the diff endpoint, then renders `<UpdateSummary>` inline. Quick price update fires immediately (no confirm).

### B-2.8 Update Summary `<UpdateSummary>`

- Renders only when the diff returned by `/sheet/import` (preflight phase) is non-empty.
- Lines: Add count (green +), Remove count (red −, with parenthetical "kept in history"), Update count (neutral ≠).
- Sub-bullet under Update count when re-scrape is required: "↳ N will be re-scraped (link changed)".
- Buttons: `[Cancel]` outlined, `[Apply]` filled primary, right-aligned.
- Cancel discards diff (no version written, no API call beyond the preflight).

### B-2.9 Error banner system `<ErrorBanner>`

- Driven by `error_code` from `/verify` response.
- Mapping table (also see §B-3 microcopy):
  - `INVALID_URL`, `NOT_FOUND`, `NOT_SHARED`, `MISSING_COLUMNS` → `severity=danger` (red)
  - `EMPTY_SHEET` → `severity=warning` (yellow), unique CTA "Connect anyway"
- Always renders the icon + title + body + recovery CTA layout.
- `role="alert"`; not dismissable (P6-R3, C6).

---

## §B-3 Microcopy library

| Surface | Copy |
|---|---|
| Verify button (idle) | `Verify & Connect` |
| Verify button (loading) | `Verifying…` |
| Verify success helper | `Verified — nothing imported yet. Click Full Sync to begin.` |
| Connection chip title | `Connected to: "{sheet_title}"` |
| Connection chip row-count line | `{row_count} products · v{version} · imported {relative_time}` |
| Detected columns label | `Detected columns:` |
| Upload limits subtitle | `Max 5 MB · Max 10,000 rows` |
| Upload one-shot note | `Note: uploads are one-shot. To pull future edits automatically, use a Google Sheet link.` |
| Template link | `⤓ Download template` |
| Template link (xlsx + csv) | `⤓ Download template (.xlsx · .csv)` |
| Preview disclosure | `▸ Preview {row_count} products` |
| Preview snapshot caption | `Snapshot from v{version} — refresh to check live.` |
| Preview no-change result | `No changes since last import.` |
| Preview updates-available banner | `Updates available — [Update List]` |
| Update List button | `Update List` (subtitle: `Pull sheet edits`) |
| Full Sync button | `Full Sync` (subtitle: `Re-scrape everything`) |
| Quick price update item | `Quick price update` (subtitle: `Prices & UTM only. Existing SKUs only. Skips images.`) |
| Update Summary header | `Update will:` |
| Update Summary lines | `+ Add {n} products`  ·  `− Remove {n} product(s) (kept in history)`  ·  `≠ Update {n} products` |
| Update Summary re-scrape sub-line | `↳ {n} will be re-scraped (link changed)` |
| Update Summary buttons | `Cancel` · `Apply` |
| No-change toast | `No changes detected.` |
| Update success toast | `Updated {n} products. {m} images re-scraped, {k} preserved (manual overrides).` |
| Full Sync confirm title | `Re-scrape everything?` |
| Full Sync confirm body | `This will re-fetch the sheet and re-scrape every product. Manual image overrides are preserved. This can take several minutes.` |
| Full Sync confirm buttons | `Cancel` · `Re-scrape all` |
| Full Sync success toast | `Synced {n} products. {k} images preserved (manual overrides).` |
| Quick price update success toast | `Prices updated for {n} SKUs. Images untouched.` |
| Quick price update partial toast | `Prices updated for {n} of {m} SKUs. {k} skipped — see logs.` |
| Generic failure toast | `{Action} failed: {error}. [Retry]` |
| Copy-confirmation tooltip | `Copied` |
| Service-account help | `Share the sheet with this email as Editor.` |
| Error: INVALID_URL | Title `URL doesn't look like a Google Sheets link.` · Body `Make sure the link starts with "https://docs.google.com/spreadsheets/".` |
| Error: NOT_FOUND | Title `Sheet not found.` · Body `Double-check the URL — the sheet may have been moved or deleted.` |
| Error: NOT_SHARED | Title `Service account doesn't have access.` · Body `Share the sheet with the email below as Viewer or Editor, then verify again.` · CTA `📋 Copy {email}` |
| Error: EMPTY_SHEET | Title `Sheet is empty.` · Body `We connected, but found no rows.` · CTA `Connect anyway` |
| Error: MISSING_COLUMNS | Title `Missing column: {col}` (or `Missing columns: {col1}, {col2}`) · Body `Your sheet must include "sku" and "product_link". Use the template to get the headers right.` · CTA `⤓ Download template` |
| Re-scrape progress header | `Re-scraping {done} of {total} changed products…` |
| Re-scrape leave-anytime hint | `You can leave this panel — sync will continue.` |
| Aria-label: tab control | `Choose a source: Google Sheets link or file upload` |
| Aria-label: copy email | `Copy service account email` |
| Aria-label: refresh preview | `Check the source for updates` |
| Aria-label: kebab | `More sync actions` |

---

## §B-4 Interaction details

| ID | Interaction | Detail |
|---|---|---|
| I1 | Verify firing | `POST /campaigns/{id}/sheet/verify` fires only on click (P3-A3, FR-1 acceptance). Pasting or blurring the input does NOT fire. Debounce N/A. |
| I2 | Tab switch | Local only. URL field value preserved; verification status reset (banner clears, chip hides). |
| I3 | Preview refresh | Calls `/verify` (read-only). Banner result stays in the preview header until next interaction. Does NOT auto-trigger Update List. |
| I4 | Update List click | Calls `/sheet/import` preflight; renders `<UpdateSummary>`. Apply confirms; the same endpoint commits and returns 202 with `sync_job_id`. |
| I5 | Apply click | UI immediately enters re-scrape progress state via WebSocket subscription on `sync_job_id`. |
| I6 | Full Sync click | Confirm modal → on confirm, transitions action zone to progress card. Progress identical to I5. |
| I7 | Quick price update click | No confirm. Spinner near kebab. On completion: toast. |
| I8 | Upload re-upload | Per FR-3 + Open Question 3: file must be re-uploaded for both verify and import (no server-side caching in v1). UX surfaces this honestly: after a successful upload, the dropzone is replaced by the connection chip and a "Replace file" link. |
| I9 | Network failure on Verify | Toast `Verification failed: {network error}. [Retry]`. No banner mutation (banners are reserved for `error_code` results). |
| I10 | Concurrent sync attempt | If a sync job is already in flight for this campaign, all sync buttons are disabled and the progress card is shown. |
| I11 | Source switch with prior connection | Switching from Link → Upload (or vice versa) does NOT immediately disconnect. Connection chip remains until a new verify/upload completes successfully. The chip shows a small "Pending source change" tag while in this transient state. |
| I12 | Soft-deleted product reappears | If a previously-removed SKU returns in a new sheet version, the import worker un-soft-deletes it. UX surfaces this in the Update Summary as `+ Add 1 product (restored from history)`. |

---

## §B-5 Design system tokens (roles only)

The repo's existing design system supplies actual values. This spec specifies *roles*.

### Color roles

| Role | Used for |
|---|---|
| `surface.panel` | Panel background |
| `surface.flat` | Read-only data rows (preview cells, version line) |
| `text.primary` / `text.muted` | Body / subtitles |
| `text.mono` | URLs, SKUs, service-account email |
| `action.primary` | Filled primary buttons (Verify, Update List, Full Sync pre-first-sync, Apply) |
| `action.secondary` | Outlined secondary buttons (Full Sync post-first-sync, Cancel) |
| `status.success` | Connection chip dot, success toasts |
| `status.warning` | EMPTY_SHEET banner |
| `status.danger` | INVALID_URL / NOT_FOUND / NOT_SHARED / MISSING_COLUMNS banners, failure toasts |
| `status.info` | Re-scrape progress card |

### Typography hierarchy

| Token | Used for |
|---|---|
| `title.panel` | "Google Sheets" header |
| `title.section` | "Update will:", error banner titles |
| `body.default` | Most copy |
| `body.mono` | URLs, SKUs, service-account email |
| `caption` | Subtitles under buttons, snapshot caption, dropzone limits |

### Spacing rhythm

- `panel.padding`: applied uniformly inside the panel.
- `group.gap`: vertical gap between IA groups (Source / Data / Actions).
- `button.gap`: vertical gap inside the action group.
- Preview table uses dense row spacing distinct from the rest of the panel.

No hex codes, no font names. Defer to the existing tokens in the frontend repo.

---

## §B-6 Responsive & accessibility

### Responsive

- Panel min width: 320 px (still legible on mobile sidebar).
- At < 480 px: segmented control becomes full-width pills stacked horizontally; preview table scrolls horizontally with sticky first column (SKU).
- At ≥ 480 px: layout matches §B-1 wireframes.
- The panel itself is part of the campaign workspace; absolute width is owned by the workspace layout, not this spec.

### Accessibility (per PRD §9.6)

- All interactive elements have aria-labels (see §B-3 microcopy).
- Error banners use `role="alert"`; screen readers announce them on appearance.
- Preview table:
  - `<table>` with `<thead>`/`<tbody>`.
  - Arrow keys cycle rows; Home/End jump to first/last.
  - Refresh icon button has `aria-label` and a visible focus ring.
- Focus order through the panel: source picker → input/dropzone → Verify button → service-account copy → preview disclosure → action group (Update List → Full Sync → kebab) → change-source link.
- WCAG AA contrast on all text/background pairs (verify against existing tokens).
- Confirm modals trap focus; Esc cancels.

---

## §B-7 Open UX questions (recommendations)

These map to PRD §13 items where the UX answer is not obvious.

| PRD § | Question | Recommendation in this spec | Reasoning |
|---|---|---|---|
| 13.1 | Should pure-edit no-op imports skip the summary? | **Skip only when diff is empty** (D5). Pure edits (≠ only) still show the summary so the user knows what will change. | Empty diff = nothing to confirm; pure edits = the user benefits from seeing scope before apply. |
| 13.2 | Version retention cap | UX-neutral; out of scope. | UX does not depend on the cap; expose nothing in v1. |
| 13.3 | Cache uploads for verify→import | **Re-upload required** (I8). UX surfaces this honestly. | Avoids a server-side cache; honest UX is acceptable for the upload persona who is one-shot anyway. |
| 13.4 | Soft-deleted products in preview | **Filtered out of preview by default**; Update Summary uses "(kept in history)" copy to make soft-delete legible. | Preview's job is "what is currently active"; history surface (out of scope v1) is where deleted rows would appear. |
| 13.5 | Post-import survey | **Defer.** Telemetry consent is out of scope for this spec. | Added complexity that does not block the redesign. |
| 13.6 | Multi-tab sheet warning | **Add a Verify-time info banner** when `sheet_title` is from a workbook with more than one tab: "This workbook has multiple tabs. We import the first one. Other tabs are ignored." | Cheap and prevents a surprising silent behavior. Add `tab_count` to the `/verify` response if not already present. |

---

## Implementer checklist

- [ ] Read Part A end-to-end before touching layout.
- [ ] Confirm constraints C1–C8 are satisfied at every state transition.
- [ ] Wire the existing `gateway.send_progress` WebSocket into the re-scrape progress card.
- [ ] Map every `error_code` from `/verify` to its banner per §B-3.
- [ ] Hide Update List + kebab when no Full Sync has succeeded; hide Update List when source = upload.
- [ ] Manual override count must appear in every post-sync toast (C7).
- [ ] Soft-deleted products are excluded from preview; Update Summary uses "(kept in history)" copy (C8).
- [ ] All copy in §B-3 lifted verbatim into the i18n bundle.
- [ ] Accessibility checks per §B-6 pass.
