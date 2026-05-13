# Issues — Product Review Screen (Pre-Emailer Gate)

**Source PRD:** `prd/01-2026-05-13-072930-product-review-screen.md`
**Created:** 2026-05-13
**Intended for:** Ralph autonomous loop. One issue at a time, top-down.

---

## How to use this document (for Ralph)

1. **Pick the lowest-numbered issue that is not yet `[x] Complete`.**
2. **Before starting**, verify every "Blocked by" issue is `[x] Complete`. If not, skip and pick the next one.
3. **Read the full "What to build" + "Acceptance criteria" + "Validation" sections.**
4. **Mark `[~] In Progress`** at the top of the issue before writing code.
5. **Tick each acceptance-criteria checkbox** as you finish it.
6. **Run the validation commands** in the "Validation" block. All must pass.
7. **Mark `[x] Complete`** at the top of the issue.
8. **Commit** with message `feat(review): issue N — <title>`.
9. **Pick the next issue.**

Top-of-issue status legend: `[ ]` Not started · `[~]` In progress · `[x]` Complete · `[!]` Blocked / needs human.

---

## Dependency flow

```
                     ┌─────────────────────┐
                     │ #1 Schema + sheet   │   (foundation — must land first)
                     │    ingestion        │
                     └──────────┬──────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
   ┌─────────────────────────┐     ┌─────────────────────────┐
   │ #2 PATCH endpoint       │     │ #4 Read-only Review     │
   │    + ManualOverride     │     │    page + gating        │
   └────────────┬────────────┘     └────────────┬────────────┘
                │                               │
                ▼                               │
   ┌─────────────────────────┐                  │
   │ #3 Override wins on sync│                  │
   └────────────┬────────────┘                  │
                │                               │
                └───────────────┬───────────────┘
                                ▼
   ┌──────────────────────────────────────────────────────────┐
   │ #5 Inline text editing     #6 Photo edit popover         │
   │ (depends on #2, #4)        (depends on #4)               │
   └────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────┐
   │ #7 Soft-block confirm dialog        │
   │ #8 Re-gating triggers               │
   │ #9 LeftRail re-open button          │
   │ (all depend on #4; can run parallel)│
   └────────────────────┬────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────┐
   │ #11 Metrics (depends on #5/#6/#7)   │
   └─────────────────────────────────────┘

   #10 Email rendering for blanks  — HITL, depends on #1, parallel to all UI work
```

**Strict order Ralph should follow when in doubt:**
`#1 → #2 → #3 → #4 → #5 → #6 → #7 → #8 → #9 → #11 → #10 (HITL)`

---

## Repo cheat-sheet

| Area | Path |
|---|---|
| Models | `backend/app/models/` |
| Migrations | `backend/app/migrations/` (alembic, see `backend/alembic.ini`) |
| Routers | `backend/app/routers/` |
| Sync / scrape modules | `backend/app/modules/` |
| Backend schemas | `backend/app/schemas/` |
| Frontend pages | `frontend/src/pages/` |
| Frontend components | `frontend/src/components/` |
| Frontend API client | `frontend/src/lib/api.ts` |
| Routing | `frontend/src/App.tsx` |
| Backend tests | `backend/tests/` (pytest) |
| Run backend tests | `cd backend && pytest` |
| Run frontend type-check | `cd frontend && npm run typecheck` (or `tsc --noEmit`) |
| Run frontend build | `cd frontend && npm run build` |

---

---

## Issue 1: Schema + sheet ingestion for new fields

**Status:** `[x]` Complete
**Type:** AFK
**Blocked by:** None — can start immediately
**Blocks:** #2, #3, #4, #10
**PRD stories covered:** Story 10

### What to build

Add three optional string columns to `Product` (`pack_of`, `quantity`, `discount`, all `String(50)` nullable) and one nullable `DateTime` column to `Campaign` (`reviewed_at`). Extend the sheet parser so that if the sheet contains any of the optional columns `pack_of`, `quantity`, `discount`, the values are read into the corresponding `Product` fields. If the columns are absent, parsing must succeed without error and the verify endpoint must not flag them as missing.

The product read schema must expose the new fields so any client fetching products sees them.

This is a foundation slice. No UI, no behavior change beyond data plumbing.

### Acceptance criteria

- [x] `Product` model has new columns: `pack_of: String(50) nullable`, `quantity: String(50) nullable`, `discount: String(50) nullable`.
- [x] `Campaign` model has new column: `reviewed_at: DateTime(timezone=True) nullable`.
- [x] Alembic migration generated and applies cleanly (forward and reverse).
- [x] `schemas/sync.py` (`ProductRead`) and any other product-exposing schemas expose `pack_of`, `quantity`, `discount`.
- [x] Campaign read schema exposes `reviewed_at`.
- [x] `modules/sheet_parser.py` reads optional columns `pack_of`, `quantity`, `discount` when present.
- [x] Missing optional columns DO NOT cause verify failures (`MISSING_COLUMNS` only fires for `sku`/`product_link`).
- [x] Existing tests in `backend/tests/` still pass.
- [x] Unit test: parsing a sheet with the three new columns populates the fields.
- [x] Unit test: parsing a sheet WITHOUT the new columns leaves them `None` and does not error.

### Validation

```bash
cd backend && pytest -x
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd frontend && npm run build
```

All three must succeed.

### Notes for Ralph

- Look at existing `Product` model (`backend/app/models/product.py`) for column style.
- Look at existing migrations under `backend/app/migrations/versions/` to copy alembic style.
- `sheet_parser.py` lives at `backend/app/modules/sheet_parser.py` — find header-matching logic and extend.

---

## Issue 2: PATCH product text-fields endpoint + ManualOverride extension

**Status:** `[x]` Complete
**Type:** AFK
**Blocked by:** #1
**Blocks:** #3, #5, #11
**PRD stories covered:** Story 3 (server side)

### What to build

Add a `PATCH /campaigns/{campaign_id}/products/{product_id}` endpoint to `backend/app/routers/products.py`. Accept a JSON body with any subset of: `formatted_price`, `scraped_name`, `pack_of`, `quantity`, `discount`. For each provided field:

1. Update the field on the `Product` row.
2. Upsert a `ManualOverride` row with `target_type = product_<field>` and `override_url` storing the literal text value. Use `target_type` strings exactly: `product_price` (for `formatted_price`), `product_description` (for `scraped_name`), `product_pack_of`, `product_quantity`, `product_discount`.
3. Use the same campaign-ownership check pattern from the existing image endpoints.

Document in the `ManualOverride` model file (`backend/app/models/manual_override.py`) that `override_url` is reused for text values on non-image target types.

### Acceptance criteria

- [x] `PATCH /campaigns/{campaign_id}/products/{product_id}` route exists.
- [x] Requires `current_active_user` and verifies campaign ownership (404 otherwise).
- [x] 404 when product not found / belongs to other campaign.
- [x] Accepts partial body (any subset of the five fields).
- [x] 422 when body has no recognized fields.
- [x] Returns updated `ProductRead`.
- [x] Each touched field results in exactly one `ManualOverride` row (existing row of same target_type replaced).
- [x] `ManualOverride.override_url` stores the text value verbatim.
- [x] `ManualOverride` model file has docstring note about reuse for text values.
- [x] Test: PATCH one field → product updated + override row exists.
- [x] Test: PATCH multiple fields → multiple overrides.
- [x] Test: PATCH same field twice → exactly one override row remains.
- [x] Test: ownership check rejects other-user campaign.

### Validation

```bash
cd backend && pytest -x backend/tests
cd backend && pytest -x backend/tests/test_routers_products.py
```

### Notes for Ralph

- Existing image-replace endpoint in `backend/app/routers/products.py:115` is the reference pattern (delete-then-insert for the override).
- Add a Pydantic request schema (e.g., `ProductPatchRequest`) in `backend/app/schemas/sync.py` or a new file — match codebase convention.
- The mapping from request field → `target_type` is intentionally explicit; do not infer dynamically.

---

## Issue 3: ManualOverride wins for text fields during sync

**Status:** `[x]` Complete
**Type:** AFK
**Blocked by:** #2
**Blocks:** (nothing structurally, but PRD Story 7 won't be true until this lands)
**PRD stories covered:** Story 7

### What to build

The image-override survival mechanism (`ManualOverride` with `target_type=product_image`) already exists in the sync flow. Extend it so that for every product the sync touches, after materializing the new value from sheet/scrape, the code looks up any `ManualOverride` for that product whose `target_type` matches one of `product_price`, `product_description`, `product_pack_of`, `product_quantity`, `product_discount`, and applies the override value to the corresponding `Product` field, winning over the new sheet/scrape value.

This must apply to: Full Sync, Update List apply (`importSheetCommit`), and Quick Price Update.

### Acceptance criteria

- [x] Sync materialization code applies non-image `ManualOverride` rows.
- [x] Mapping (target_type → Product attribute) is the inverse of the mapping in #2.
- [x] Test: edit a price via the PATCH endpoint → run a Full Sync → price remains the user's value (sheet's price is discarded).
- [x] Test: edit description → Update List apply → description preserved.
- [x] Test: edit pack_of → Quick Price Update → pack_of preserved.
- [x] Test: no override for a field → sheet value wins (regression safety).
- [x] Existing image-override test still passes.

### Validation

```bash
cd backend && pytest -x backend/tests
```

### Notes for Ralph

- Find the sync orchestration code under `backend/app/modules/` and `backend/app/routers/sync.py`. Search for `ManualOverride` references; that's where image overrides apply today.
- Resist the temptation to "generalize" beyond the five target_types defined in #2 — being explicit is desired.

---

## Issue 4: Read-only Review page + gating redirect + complete endpoint

**Status:** `[ ]` Not started
**Type:** AFK
**Blocked by:** #1
**Blocks:** #5, #6, #7, #8, #9
**PRD stories covered:** Story 1, Story 2, Story 6 (skeleton)

### What to build

End-to-end gate the emailer.

**Backend:**
- Add `POST /campaigns/{campaign_id}/review/complete` that sets `Campaign.reviewed_at = now()` and returns the updated campaign. Ownership-checked.

**Frontend:**
- Create `frontend/src/pages/ProductReviewPage.tsx`. Route: `/campaigns/:id/review`. Fetch products via the existing `getProducts` API.
- Create `frontend/src/components/review/ProductCard.tsx`. Render fields in this top→bottom order: Photo · Description · Price + Discount · Pack of · Quantity. **Display only, no editing yet.** Failed-scrape products: coming-soon placeholder + gentle red border. Empty pack/quantity/discount/price: muted "—".
- Grid: 4 cols xl / 3 lg / 2 md / 1 sm, 16px gap.
- Page header: breadcrumb + "Review products before sending" subtitle + "Proceed to Emailer" primary button (right-aligned, sticky on scroll). Button always enabled; on click → POST review/complete → navigate to `/campaigns/:id`.
- Modify `frontend/src/pages/WorkspacePage.tsx`: after `loadCampaign`, if `campaign.reviewed_at == null`, render `<Navigate to={`/campaigns/${id}/review`} replace />`.
- Modify `frontend/src/App.tsx` to register the new route (inside `<ProtectedRoute>`).
- Modify `frontend/src/components/layout/SyncPanel.tsx` `onSyncComplete` flow so the first successful sync triggers navigation to the Review page (the gate redirect in `WorkspacePage` will also catch it, but the explicit nav is friendlier).
- Add API client functions in `frontend/src/lib/api.ts`: `completeReview(campaignId)`.

No inline editing, no photo popover, no soft-block — those are later issues.

### Acceptance criteria

- [ ] `POST /campaigns/:id/review/complete` exists, ownership-checked, sets `reviewed_at`, returns campaign.
- [ ] Backend test: endpoint flips `reviewed_at` from null to a timestamp.
- [ ] Backend test: ownership rejected.
- [ ] `/campaigns/:id/review` route registered, protected.
- [ ] Direct navigation to `/campaigns/:id` with `reviewed_at == null` redirects to `/campaigns/:id/review`.
- [ ] Direct navigation to `/campaigns/:id` with `reviewed_at != null` stays on Workspace.
- [ ] Grid renders all products fetched from `getProducts`.
- [ ] Card shows: Photo (square), Description (`scraped_name`, 2-line truncate), Price (`formatted_price`), Discount (chip when present), Pack of, Quantity.
- [ ] Failed-scrape card has placeholder photo + red border.
- [ ] Empty text fields render muted "—".
- [ ] Both price and discount visible when both present.
- [ ] "Proceed to Emailer" button calls complete endpoint, then navigates to Workspace.
- [ ] After Proceed, user lands on Workspace (not redirected back to Review).
- [ ] `npm run build` and `tsc --noEmit` succeed.

### Validation

```bash
cd backend && pytest -x
cd frontend && npm run typecheck && npm run build
```

Manual smoke (record as comments in commit message):
1. Create a new campaign, sync — should land on Review page.
2. Click Proceed — should land on Workspace.
3. Navigate back to `/campaigns/:id` directly — should stay on Workspace.

### Notes for Ralph

- Look at `frontend/src/pages/WorkspacePage.tsx` for the load pattern (`loadCampaign`, `useEffect`).
- Look at `frontend/src/components/layout/TopBar.tsx` for breadcrumb usage.
- Reuse design tokens: `text-heading-3`, `text-body`, `text-small`, `bg-neutral-50`, `border-neutral-200`, `text-error-600`, `brand-primary`.
- Components go under `frontend/src/components/review/` (new dir).

---

## Issue 5: Inline text editing on Review cards

**Status:** `[ ]` Not started
**Type:** AFK
**Blocked by:** #2, #4
**Blocks:** #11
**PRD stories covered:** Story 3 (UI), Story 5

### What to build

Turn the static text fields on each `ProductCard` (Description, Price, Discount, Pack of, Quantity) into click-to-edit fields wired to the PATCH endpoint from #2.

**UX:**
- Default: field renders as static text.
- Click: swap to `<input>` with current value pre-selected.
- Enter or blur: commit. Esc: revert to last-committed value.
- Debounce PATCH by 400ms to coalesce keystrokes.
- Optimistic local update; on error, revert to previous value and show toast.
- Brief checkmark flash (200ms) on successful commit. Red ring on error.
- Each input has `aria-label` like `Edit price for SKU ABC-123`.

**API client:** Add `patchProduct(campaignId, productId, body)` in `frontend/src/lib/api.ts`.

### Acceptance criteria

- [ ] All five text fields are click-to-edit.
- [ ] Pre-selection of input value on edit-mode entry.
- [ ] Enter commits; blur commits; Esc reverts.
- [ ] PATCH is debounced 400ms.
- [ ] Optimistic UI: card displays new value before PATCH resolves.
- [ ] On PATCH error: value reverts, toast shows.
- [ ] Successful commit triggers brief checkmark visual.
- [ ] `aria-label` present on each input with SKU and field name.
- [ ] Keyboard: Tab moves focus through cards in DOM order.
- [ ] `npm run typecheck && npm run build` succeed.
- [ ] Manual smoke: edit price → reload page → new value persists.
- [ ] Manual smoke: edit field → check `ManualOverride` row exists in DB.

### Validation

```bash
cd frontend && npm run typecheck && npm run build
cd backend && pytest -x  # ensure nothing regressed
```

### Notes for Ralph

- Consider extracting an `<InlineTextField>` component in `frontend/src/components/review/InlineTextField.tsx` to share between the five fields.
- Use existing `showToast` from `frontend/src/components/ui/Toast.tsx` for error messaging.
- Existing debounce pattern: search for "debounce" in `frontend/src/hooks/` — there may be a hook already.

---

## Issue 6: Photo edit popover

**Status:** `[ ]` Not started
**Type:** AFK
**Blocked by:** #4
**Blocks:** #11
**PRD stories covered:** Story 4

### What to build

When the user clicks a product photo on the Review card, open a small popover/modal with two tabs: **Upload file** and **Paste image URL**. Submission calls the existing `PATCH /campaigns/:id/products/:pid/replace-image` endpoint (no backend changes). On success, the card photo updates immediately (use the response `processed_image_url`).

Create `frontend/src/components/review/ImageEditPopover.tsx`.

### Acceptance criteria

- [ ] Click on card photo opens popover.
- [ ] Popover has two tabs: Upload / URL.
- [ ] Upload tab: file input (accept `image/*`).
- [ ] URL tab: text input with placeholder "https://…".
- [ ] Submit calls existing `replace-image` endpoint via `lib/api.ts`.
- [ ] 10MB / non-image errors surface as toast and keep popover open.
- [ ] On success, popover closes and card photo updates.
- [ ] Esc closes popover without saving.
- [ ] `npm run typecheck && npm run build` succeed.
- [ ] Manual smoke: replace a photo via URL → card updates → reload preserves it.
- [ ] Manual smoke: replace via file upload → same.

### Validation

```bash
cd frontend && npm run typecheck && npm run build
```

### Notes for Ralph

- Look at `frontend/src/lib/api.ts` for any existing `replaceProductImage` function; if absent, add it (multipart form upload).
- For the modal/popover primitive, reuse `frontend/src/components/ui/Modal.tsx`.

---

## Issue 7: Soft-block confirm dialog on Proceed

**Status:** `[ ]` Not started
**Type:** AFK
**Blocked by:** #4
**Blocks:** #11
**PRD stories covered:** Story 6 (refinement of behavior already shipped in skeleton form)

### What to build

Refine the "Proceed to Emailer" flow so that when the user clicks Proceed, before calling complete:

1. Scan products for "blank required fields":
   - photo is the coming-soon placeholder (`scrape_failed == true` OR `processed_image_url` equals `/static/coming-soon.svg`)
   - both `formatted_price` and `discount` are blank
2. If any product has at least one blank, open a confirm modal with summary:
   > "3 products have missing prices and 1 is using a placeholder image. Continue anyway?"
3. Two buttons: Cancel (close modal) and "Continue anyway" (proceed to complete + navigate).
4. If no blanks, skip dialog and proceed.

### Acceptance criteria

- [ ] Blank-detection logic correctly identifies placeholder photos and price+discount-blank products.
- [ ] Confirm dialog only opens when blanks exist.
- [ ] Dialog message includes correct counts.
- [ ] Cancel closes dialog without side-effect.
- [ ] Continue calls complete endpoint and navigates.
- [ ] When no blanks: clicking Proceed proceeds directly (no dialog).
- [ ] Manual smoke with a campaign that has 1 placeholder photo and 1 blank-price product: dialog shows correct counts.

### Validation

```bash
cd frontend && npm run typecheck && npm run build
```

### Notes for Ralph

- Use `frontend/src/components/ui/Modal.tsx`.
- Place blank-detection as a pure function in the page or in a small helper file so it's testable.

---

## Issue 8: Re-gating triggers after Full Sync / Update List with adds

**Status:** `[ ]` Not started
**Type:** AFK
**Blocked by:** #4
**Blocks:** #11
**PRD stories covered:** Story 8

### What to build

Wire `Campaign.reviewed_at` to be cleared (set to `NULL`) in the appropriate moments inside the sync flow:

- **Full Sync:** clear `reviewed_at` when Full Sync starts (or when it completes — pick "completes" for cleaner semantics).
- **Update List apply:** in `importSheetCommit`, if the preflight diff had `len(added) > 0`, clear `reviewed_at` after apply.
- **Quick Price Update:** do NOT touch `reviewed_at`.

After clear: the next time the user lands on `/campaigns/:id`, the redirect from #4 will kick them to Review.

### Acceptance criteria

- [ ] Full Sync completion clears `reviewed_at`.
- [ ] Update List apply with `added > 0` clears `reviewed_at`.
- [ ] Update List apply with only `modified`/`removed` does NOT clear `reviewed_at`.
- [ ] Quick Price Update never clears `reviewed_at`.
- [ ] Backend test for each of the four cases above.
- [ ] Manual smoke: complete Review → run Quick Price Update → navigate to Workspace, NOT Review.
- [ ] Manual smoke: complete Review → Update List with a new SKU → navigate, lands on Review.

### Validation

```bash
cd backend && pytest -x
```

### Notes for Ralph

- The preflight result already exists; find it in `routers/sync.py` or wherever `importSheetCommit` lives — the `added`/`modified`/`removed` arrays are computed there.
- Use a single DB UPDATE inside the existing transaction; no separate endpoint.

---

## Issue 9: Re-open Review button in LeftRail

**Status:** `[ ]` Not started
**Type:** AFK
**Blocked by:** #4
**Blocks:** #11
**PRD stories covered:** Story 9

### What to build

Add a "Review products" button in `frontend/src/components/layout/LeftRail.tsx` directly below the `<SyncPanel />` (and above `<VisualBriefPanel />`). Clicking it navigates to `/campaigns/:id/review`. Visible only when products exist (`products.length > 0`).

### Acceptance criteria

- [ ] Button visible in LeftRail directly under SyncPanel when products exist.
- [ ] Hidden when there are no products.
- [ ] Click navigates to `/campaigns/:id/review` using `react-router-dom` `useNavigate`.
- [ ] Visual matches existing LeftRail panel buttons (look at `VisualBriefPanel`/`SectionsPanel` for style).
- [ ] `npm run typecheck && npm run build` succeed.

### Validation

```bash
cd frontend && npm run typecheck && npm run build
```

### Notes for Ralph

- `LeftRail.tsx` is short — straightforward insertion.
- `useNavigate` is already imported elsewhere in the codebase.

---

## Issue 10: Email rendering for blank pack/quantity/discount

**Status:** `[ ]` Not started
**Type:** **HITL** (open question — needs decision from render team / product)
**Blocked by:** #1
**Blocks:** Nothing structurally; pure render-quality polish.
**PRD stories covered:** PRD §13 open question #1

### What to build

Decide and implement: when a product has a blank `pack_of`, `quantity`, or `discount`, should the email template:

- (a) **hide** the corresponding line/row entirely, OR
- (b) always render the line with a "—" / fallback placeholder?

**Decision must be captured in a comment in the PRD or this file before implementation.** Then update the MJML renderer (`backend/app/modules/mjml_renderer.py`) to match.

This is HITL because Ralph must NOT pick (a) or (b) on its own. The render team's preference shapes the email visually.

### Acceptance criteria

- [ ] Decision recorded (here or in PRD).
- [ ] MJML renderer handles blank pack_of correctly per decision.
- [ ] MJML renderer handles blank quantity correctly per decision.
- [ ] MJML renderer handles blank discount correctly per decision (also: when only discount is present and price is blank, render discount only).
- [ ] Existing rendering tests still pass.
- [ ] At least one new test per field covering the blank case.

### Validation

```bash
cd backend && pytest -x
```

### Notes for Ralph

- **STOP and ask a human** for the (a) vs (b) decision before writing code. Update this issue's "Status" to `[!]` and surface the question in your loop output.

---

## Issue 11: Review-screen metrics instrumentation

**Status:** `[ ]` Not started
**Type:** AFK
**Blocked by:** #5, #6, #7
**Blocks:** Nothing.
**PRD stories covered:** PRD §6

### What to build

Instrument the Review screen to emit signals for the metrics defined in PRD §6:

1. **Edit count per session.** Fire a signal each time an inline edit commits successfully (#5) or a photo replace succeeds (#6).
2. **Proceed click + blanks-confirmed.** Fire one signal on Proceed; include a flag `had_blanks: bool` and (if true) whether the user clicked "Continue anyway" or "Cancel" (#7).
3. **Photo replace count per session.**

Reuse the existing preference-signal channel (`recordPreferenceSignal` in `frontend/src/lib/api.ts`) unless the team prefers a dedicated event channel — if so, leave a note in this issue and stop for human input (HITL fallback).

### Acceptance criteria

- [ ] Inline edit success → 1 signal emitted with field name.
- [ ] Photo replace success → 1 signal emitted.
- [ ] Proceed click → 1 signal with `had_blanks` flag.
- [ ] "Continue anyway" → 1 signal with outcome=`continued`.
- [ ] Cancel from soft-block → 1 signal with outcome=`cancelled`.
- [ ] No metric calls in render path (avoid duplicate emissions).
- [ ] `npm run typecheck && npm run build` succeed.

### Validation

```bash
cd frontend && npm run typecheck && npm run build
```

### Notes for Ralph

- If unclear which signal channel to use, mark this issue `[!]` and ask before implementing.
- Existing call: `recordPreferenceSignal({ signal_type, asset_type, signal_value, campaign_id })` — see `frontend/src/pages/WorkspacePage.tsx:222`.

---

## Done definition (apply to every issue before marking `[x]`)

- [ ] All acceptance criteria ticked.
- [ ] All commands in "Validation" succeed locally.
- [ ] No new TypeScript errors (`npm run typecheck`).
- [ ] No new Python test failures (`pytest`).
- [ ] If a UI change: at least one manual smoke noted in commit message.
- [ ] Commit message format: `feat(review): issue N — <short title>`.
- [ ] No unrelated refactors or formatting churn in the diff.

---

## Out-of-scope reminders (do not implement)

- Manual product add.
- Product remove / soft-delete on Review.
- Scraping description / pack-of / quantity / discount from web pages.
- Bulk edit / multi-select / search / filter / sort on the grid.
- Rename `ManualOverride.override_url` → `override_value` (future cleanup).
- Drag-to-reorder cards.
- Image cropping / focal-point picker.

If a task seems to require any of the above, STOP, mark `[!]`, and ask a human.
