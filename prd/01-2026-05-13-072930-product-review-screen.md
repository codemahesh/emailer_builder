# PRD: Product Review Screen (Pre-Emailer Gate)

**Document Status:** Draft — locked design from grilling session
**Author:** Product
**Created:** 2026-05-13
**Target Release:** TBD
**Related Files:**
- `frontend/src/pages/WorkspacePage.tsx`
- `frontend/src/components/layout/SyncPanel.tsx`, `LeftRail.tsx`
- `backend/app/models/product.py`, `models/campaign.py`, `models/manual_override.py`
- `backend/app/routers/products.py`
- `backend/app/modules/sheet_parser.py`, `product_scraper.py`

---

## 1. Executive Summary

Today, the moment a user finishes scraping products from Google Sheets or a file upload, the products flow directly into the emailer preview pane on `WorkspacePage`. There is no opportunity to review or correct scraped data before it shapes the email render. Scrape misses (missing images, wrong names, blank prices) propagate silently into the rendered emailer and are only caught much later — sometimes after a review link has already been shared.

This PRD introduces a **Product Review Screen**: a storefront-styled grid that opens after scraping and *gates* access to the emailer until the user has confirmed each product. Each card shows Photo, Description, Price, Discount, Pack of, and Quantity, with every field directly inline-editable. Edits are persisted as `ManualOverride` records so they survive future syncs. The screen reuses the existing scrape pipeline, image-replace endpoint, and sync gating model — no manual-add or remove flows are introduced in v1.

The outcome is a single, focused step where the user catches and corrects scrape errors before any rendering happens, reducing the volume of post-share corrections and increasing trust in the emailer output.

---

## 2. Problem Statement

**Today's flow:**
1. User connects Google Sheet or uploads file (`SyncPanel`)
2. Backend scrapes each product URL → populates `Product` rows
3. Products immediately render into the emailer preview (`PreviewPane`) on `WorkspacePage`
4. User notices errors *while looking at the rendered email* — a downstream view that mixes content (scrape result) with presentation (template, theme, layout)

**Pain points this causes:**
- Errors are caught in a context where the user is also evaluating *design*, so cognitive load is split.
- Some scrape misses (blank price, generic stock image) are easy to miss inside a styled card.
- Per-product edits today are scattered across `QualityWarningsPanel`, the image replace endpoint, and the sheet itself — there's no single screen for "go fix the data."
- Pack-of, quantity, and discount data are not currently part of the product model — they cannot be authored at all, only displayed if pre-baked into the description string.

**The opportunity:** Insert one focused review step between scrape and render, structured to look like the storefront the products will eventually appear in.

---

## 3. Goals & Objectives

### Primary Goals

1. **Catch scrape errors before rendering.** Surface every product as a card with all fields visible at a glance.
2. **Allow inline correction without leaving the screen.** Photo, Description, Price, Discount, Pack of, Quantity — all editable in place.
3. **Persist user edits across re-syncs.** Once a user corrects a field, future syncs must not overwrite their edit.
4. **Gate the emailer.** Block access to `WorkspacePage` until the user explicitly confirms review is complete.

### Non-Goals (v1)

- Manually adding products from the Review screen (deferred — users can edit sheet and re-sync).
- Removing scraped products from the Review screen (deferred — same reason).
- Scraping description, pack-of, quantity, or discount from product pages (unreliable across stores).
- Bulk-edit / multi-select operations.
- Search / filter / sort on the Review grid.

---

## 4. Target Users

**Primary persona: Campaign Operator**
- Manages 1–5 active campaigns at a time, each with 10–80 products.
- Owns a source Google Sheet of SKUs + product URLs; iterates on it.
- Has historically caught scrape errors inside the styled email preview; wants a faster, less ambiguous way.
- Cares about: image quality, accurate prices, correct pack info before the email goes out.

**Secondary persona: Reviewer/Approver**
- Out of scope for this PRD — Review screen is operator-only. Reviewers continue to use `/preview/:token` unchanged.

---

## 5. User Stories & Requirements

### Story 1 — Land on Review after first sync

> **As a** campaign operator,
> **I want** to be routed to the Review screen automatically after my first sync completes,
> **So that** I can confirm scraped data before any rendering happens.

**Acceptance Criteria:**
- After `SyncPanel` reports a successful first sync (`Campaign.reviewed_at IS NULL`), the app redirects to `/campaigns/:id/review`.
- `WorkspacePage` (`/campaigns/:id`) redirects to `/campaigns/:id/review` when `reviewed_at IS NULL`.
- Direct navigation to `/campaigns/:id` with an un-reviewed campaign is intercepted by the same redirect.

### Story 2 — View products as a storefront grid

> **As a** campaign operator,
> **I want** to see every scraped product laid out like an e-commerce listing,
> **So that** I can evaluate the catalog the way a shopper would.

**Acceptance Criteria:**
- Responsive grid: 4 cols on `xl`, 3 on `lg`, 2 on `md`, 1 on `sm`.
- Card order (top → bottom): **Photo · Description · Price + Discount · Pack of · Quantity**.
- Failed-scrape products render with the coming-soon placeholder and a gentle red border.
- Empty pack-of / quantity / discount fields show a muted placeholder (e.g., "—") that is clickable to begin editing.

### Story 3 — Inline-edit a text field

> **As a** campaign operator,
> **I want** to click any text field on a card and type a new value,
> **So that** I can correct scrape errors without opening a separate dialog.

**Acceptance Criteria:**
- Editable text fields: Description, Price, Discount, Pack of, Quantity.
- Field renders as static text by default; on click it becomes an `<input>` with the value pre-selected.
- On blur or `Enter`, value is committed via debounced (~400ms) `PATCH /campaigns/:id/products/:pid`.
- On `Esc`, edit reverts to last-committed value.
- Server-side, the PATCH updates the `Product` row **and** writes a `ManualOverride` row with `target_type` matching the field.

### Story 4 — Replace a product photo

> **As a** campaign operator,
> **I want** to click a product photo and upload a new image or paste an image URL,
> **So that** I can fix bad or missing scraped images.

**Acceptance Criteria:**
- Click on photo opens a small popover with two inputs: "Upload file" and "Paste image URL".
- Submission calls the existing `PATCH /campaigns/:id/products/:pid/replace-image` endpoint.
- Existing `ManualOverride` mechanism (target_type=`product_image`) is reused unchanged.
- On success, the card's photo updates immediately.
- Upload size limit (10MB) and image-MIME validation are enforced by the existing endpoint.

### Story 5 — Both price and discount visible when both present

> **As a** campaign operator,
> **I want** to see the price and the discount side-by-side when both are available,
> **So that** I can confirm both pieces will appear in the email.

**Acceptance Criteria:**
- If `formatted_price` is non-empty, render the price line.
- If `discount` is non-empty, render the discount as a small chip beside or below price.
- If only one is present, only that one renders.
- Both are independently click-to-edit.

### Story 6 — Proceed to the emailer

> **As a** campaign operator,
> **I want** a clear "Proceed to Emailer" button at the top/bottom of the grid,
> **So that** I can move forward once I'm satisfied with the catalog.

**Acceptance Criteria:**
- Button is always enabled (soft-block model).
- If any product has blank required fields (defined as: photo missing → using placeholder, or price+discount both blank), clicking opens a confirm dialog:
  > "3 products have missing prices and 1 is using a placeholder image. Continue anyway?"
- On confirm, calls `POST /campaigns/:id/review/complete`, which sets `Campaign.reviewed_at = now()`.
- On success, navigates to `/campaigns/:id` (Workspace).

### Story 7 — Edits survive a sync

> **As a** campaign operator,
> **I want** my Review edits to remain after I re-sync the sheet,
> **So that** I don't have to redo corrections every time the sheet updates.

**Acceptance Criteria:**
- Any text field I edited has a `ManualOverride` row with `target_type=product_<field>` and `override_url` holding the value.
- During sync, if a `ManualOverride` exists for a (product, target_type), the override value wins over the scraped/sheet value.
- This mirrors the existing image-override behavior in `routers/products.py`.

### Story 8 — Re-gate Review when new products appear

> **As a** campaign operator,
> **I want** to re-review only when *new* products are added via Update List,
> **So that** I don't get blocked every time I tweak a price in the sheet.

**Acceptance Criteria:**
- When `importSheetCommit` runs and the preflight diff reported `len(added) > 0`, set `Campaign.reviewed_at = NULL`.
- Removed-only or modified-only diffs do **not** clear the flag.
- Quick price update never clears the flag.
- Full Sync (manual re-scrape) **does** clear the flag (treated as a fresh review cycle).

### Story 9 — Re-open Review from the Workspace

> **As a** campaign operator,
> **I want** to revisit the Review screen after I've already proceeded,
> **So that** I can correct something I noticed in the rendered email.

**Acceptance Criteria:**
- A "Review products" button appears in `LeftRail` directly below `SyncPanel`.
- Clicking it navigates to `/campaigns/:id/review`.
- The Review screen on re-entry shows all current data; user can edit and click "Proceed" again (re-stamps `reviewed_at`).

### Story 10 — Pack-of / Quantity / Discount from the sheet

> **As a** campaign operator,
> **I want** to author pack-of, quantity, and discount in my sheet,
> **So that** the Review screen starts with those values pre-filled.

**Acceptance Criteria:**
- Sheet parser (`modules/sheet_parser.py`) reads optional columns `pack_of`, `quantity`, `discount` when present.
- Verify endpoint does **not** fail when these columns are missing.
- Values flow into `Product.pack_of`, `Product.quantity`, `Product.discount`.
- A `ManualOverride` for the field wins over the sheet value on each sync.

---

## 6. Success Metrics

**Adoption**
- % of new campaigns where the Review screen is reached and "Proceed" is clicked within the same session. **Target: ≥ 95%.**

**Engagement (signal of real value, not just clicks)**
- Average # of inline edits per Review session. **Healthy range: 2–10.** (Zero edits across most sessions = users are speed-clicking through the gate; the screen isn't doing its job.)
- % of Review sessions that include at least one photo replace. **Target: ≥ 15%** (matches observed scrape-failure rates).

**Quality outcomes**
- 30-day rate of post-share image-replace events. **Target: ↓ 40%** vs. baseline (catching errors earlier).
- Volume of `image_processed`/`fail` WebSocket events that lead to a Review-screen fix (vs. propagating to the rendered preview). **Target: ≥ 80% caught on Review.**

**Funnel**
- "Continue anyway" rate on the blank-fields confirm dialog. **Watch.** A high rate suggests we're over-warning; near-zero suggests the dialog is doing nothing.

---

## 7. Scope

### In Scope (v1)
- New route `/campaigns/:id/review`.
- New DB fields: `Product.pack_of`, `Product.quantity`, `Product.discount` (all `String(50)` nullable); `Campaign.reviewed_at` (DateTime nullable).
- New endpoint: `PATCH /campaigns/:id/products/:pid` for text fields.
- New endpoint: `POST /campaigns/:id/review/complete`.
- Sheet parser extension for optional columns `pack_of`, `quantity`, `discount`.
- `ManualOverride.target_type` extended with `product_price`, `product_description`, `product_pack_of`, `product_quantity`, `product_discount`. `override_url` column reused for text values.
- Sync flow: gate trigger on first sync, full sync, and Update List when added rows > 0.
- New frontend: `ProductReviewPage.tsx`, `ProductCard.tsx`, `ImageEditPopover.tsx`.
- `WorkspacePage.tsx` gating redirect.
- `LeftRail` "Review products" re-open button.

### Out of Scope (v1, may revisit)
- Manual product creation on the Review screen.
- Product removal/soft-delete on the Review screen.
- Scraping description / pack-of / quantity / discount from web pages.
- Bulk edit, multi-select, search, sort, filter on the grid.
- Review-screen-specific analytics dashboard beyond the metrics in §6.
- Mobile-native or PWA polish — desktop responsive is sufficient.
- Reviewer-facing variant (the unauthenticated `/preview/:token` flow is unchanged).
- Renaming `ManualOverride.override_url` → `override_value` (future cleanup migration).

---

## 8. Technical Considerations

### Data Model Changes

```sql
ALTER TABLE product
  ADD COLUMN pack_of VARCHAR(50),
  ADD COLUMN quantity VARCHAR(50),
  ADD COLUMN discount VARCHAR(50);

ALTER TABLE campaign
  ADD COLUMN reviewed_at TIMESTAMPTZ;
```

No changes to `manual_override` table structure. `target_type` is a free `String`; new values are added by usage only. The `override_url` column is reused to hold text values for non-image overrides (documented in model docstring).

### API Surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/campaigns/:id/products/:pid` | `PATCH` | Update one or more of: `formatted_price`, `scraped_name`, `pack_of`, `quantity`, `discount`. Writes Product + ManualOverride per touched field. |
| `/campaigns/:id/review/complete` | `POST` | Sets `Campaign.reviewed_at = now()`. Returns updated `Campaign`. |
| `/campaigns/:id/products/:pid/replace-image` | `PATCH` | **Existing** — reused unchanged. |

### Sync Flow Changes
- After `importSheetCommit` (and full sync, and Quick price update), apply `ManualOverride` rows when materializing the final Product row values (extends current image-only behavior).
- After full sync: `reviewed_at = NULL`.
- After Update List: if preflight had `added > 0`, `reviewed_at = NULL`.
- After Quick price update: no change to `reviewed_at`.

### Routing / Gating
- `App.tsx`: add `<Route path="/campaigns/:id/review" element={<ProductReviewPage />} />` (inside `ProtectedRoute`).
- `WorkspacePage.tsx`: after `loadCampaign`, if `campaign.reviewed_at == null`, `<Navigate to={`/campaigns/${id}/review`} replace />`.
- `ProductReviewPage`: on mount, if `reviewed_at != null`, allow continued use (re-entry case) without redirect.

### Persistence Pattern (matches existing code)
- Save-as-you-edit: each field PATCH is fire-and-forget with debounce (400ms). Optimistic local update; rollback on error with toast.
- No "Cancel all" semantics — edits commit individually.

### Image Edit Popover
- Reuses existing `replace-image` endpoint exactly.
- Two-tab popover: "Upload" (file input → multipart) and "URL" (text input → form field).
- Same 10MB limit, same MIME validation.

### Dependencies
- No new backend packages.
- No new frontend packages — Tailwind grid + existing `Button`, `Modal`, `Toast`, `Skeleton` primitives.

### Performance
- Initial Review grid loads via the existing `GET /campaigns/:id/products` endpoint. No new bulk endpoint needed.
- Inline edits are independent PATCHes; no batching required at v1 scale (≤100 products).
- Image uploads continue to flow through the existing `image_store` module.

### Security
- Both new endpoints require `current_active_user` and verify campaign ownership (same pattern as `routers/products.py:49`).
- No new auth surface.

---

## 9. Design & UX Requirements

### Visual Direction
- Storefront aesthetic — clean white cards, soft shadow, large square photo on top, type hierarchy: bold description, prominent price, muted secondary fields.
- Match existing design tokens (`text-heading-3`, `text-body`, `text-small`, `brand-primary`, `neutral-*`, `error-*`).

### Card Anatomy

```
┌────────────────────────────┐
│ ┌────────────────────────┐ │
│ │                        │ │  ← Photo (1:1 aspect, click → popover)
│ │      Product photo     │ │     red border if scrape_failed
│ │                        │ │
│ └────────────────────────┘ │
│                            │
│ Product description text…  │  ← click to edit (2-line truncate)
│                            │
│ ₹1299      [20% off]       │  ← price prominent, discount as chip
│                            │
│ Pack of 6 · Qty 12         │  ← both small/muted, click to edit
└────────────────────────────┘
```

### Inline Edit Affordances
- Hover on card → cursor changes to text-cursor over editable fields, subtle background tint on hover.
- Active editing state: input bordered with `brand-primary`, value pre-selected.
- Save state: brief checkmark flash (200ms) on commit.
- Error state: red ring + toast.

### Empty States
- Scraped name missing → placeholder text "Untitled product" in muted color.
- Price missing AND discount missing → muted "—" in the price slot.
- Pack-of / quantity missing → muted "—".
- Photo missing → `/static/coming-soon.svg` + gentle red border on the card.

### Layout
- Page header: campaign name (breadcrumb), "Review products before sending" subtitle, "Proceed to Emailer" primary button (right-aligned, sticky on scroll).
- Body: responsive grid with 16px gap.
- Footer (mobile only): sticky "Proceed" button.

### Accessibility
- Each editable field is a proper `<input>` with `aria-label` (e.g., "Edit price for SKU ABC-123").
- Keyboard support: Tab through cards in DOM order; Enter to commit; Esc to cancel.
- Confirm dialog uses the existing accessible `Modal` primitive.
- Color is never the sole indicator (red border is paired with the placeholder image as a state signal).

### Out of scope for design v1
- Drag-to-reorder.
- Image cropping / focal-point picker.
- Inline image AI-generation.

---

## 10. Timeline & Milestones

*(Estimates; firm dates will be set when engineering reviews.)*

| Phase | Scope | Est. Duration |
|---|---|---|
| **M1: Data model + migrations** | New columns, ManualOverride doc update, sheet parser extension | 2 days |
| **M2: Backend endpoints** | PATCH product, POST review/complete, sync flow gate triggers, override-survives-sync extension to non-image fields | 3 days |
| **M3: Frontend Review screen** | Page, card, popover, gating redirect, re-open button | 4 days |
| **M4: Polish & integration tests** | Confirm dialog, empty/error states, end-to-end test of sync→review→proceed→re-sync, metrics instrumentation | 2 days |
| **M5: Internal QA & launch** | Manual run-through with real sheets; ship behind no flag (small, gated change) | 1 day |

**Total: ~12 working days.**

---

## 11. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Users speed-click "Proceed" without actually reviewing | High | Medium | Track edit-count-per-session metric; if zero edits dominate, add a "Last reviewed N seconds ago" warning on `WorkspacePage`. |
| Reusing `ManualOverride.override_url` for text values is confusing for future devs | Medium | Low | Document explicitly in the model file. Plan a follow-up migration to rename → `override_value` once usage patterns stabilize. |
| Sheet authors add `pack_of`/`quantity`/`discount` columns with unexpected names ("Pack Size", "qty") | Medium | Low | Document expected column names in the template; consider a fuzzy header match in `sheet_parser` as a follow-up. |
| Edit-survives-sync introduces subtle bugs where users *want* the sheet to win | Low | Medium | The Update List preflight already shows the diff. Add a small "(your edit will be preserved)" hint in the diff for fields with overrides. |
| The gate frustrates power users on small price-only edits | Low (Quick price update doesn't gate) | Low | Re-gating policy is intentionally narrow: only added rows or full sync. Monitor "Continue anyway" rate and time-on-review. |
| Photo upload popover collides with existing image-quality flow in `QualityWarningsPanel` | Low | Low | Both use the same endpoint; behavior is consistent. Add an integration test. |

---

## 12. Dependencies & Assumptions

### Dependencies
- Existing scrape pipeline (`product_scraper.py`, sync flow) — no behavioral changes needed.
- Existing `image_store` + `replace-image` endpoint — reused as-is.
- Existing `ManualOverride` model — extended by usage, no schema change.
- Existing `Toast`, `Modal`, `Button`, `Skeleton` UI primitives.

### Assumptions
- Campaign sizes remain ≤ ~100 products in v1; no virtualization / pagination needed.
- Users have a stable internet connection during Review (PATCHes are not queued offline).
- The existing Google Sheet template doc/comm will be updated to mention the three new optional columns.
- Email template rendering can handle blank `pack_of`, `quantity`, `discount` gracefully (hide row / show "—"). **Verify with rendering team before launch.**

---

## 13. Open Questions

1. Should the rendered email template explicitly **hide** sections for products with missing pack-of / quantity, or always show "—"? *(Decision needed before M4 polish.)*
2. Do we want to surface a "your edit will be preserved" hint inside the Update List diff (`UpdateSummary.tsx`) for fields with existing `ManualOverride` rows? *(Nice-to-have; tracks Risk #4.)*
3. Long-term: should `ManualOverride.override_url` be renamed to `override_value` via migration? *(Defer to post-launch.)*
4. Metrics instrumentation — do we use existing preference-signal infra (`recordPreferenceSignal`) for "edit happened on Review", or add a dedicated event channel? *(Engineering call.)*

---

## Appendix A — Locked Decisions (from grilling session)

For traceability, the following decisions were resolved during design:

- **Architecture:** Gated page at `/campaigns/:id/review` (vs. inline panel or full pre-builder route).
- **Description field source:** Existing scraped product title (`scraped_name`), simply labeled "Description" in UI. Not scraped separately.
- **Pack-of, quantity, discount sources:** Sheet only (optional columns). Not scraped.
- **Discount display:** Both price and discount shown when both present. Discount styled as chip.
- **Sheet schema:** New columns optional; existing sheets unaffected. All three new fields `String(50)`.
- **Manual add:** Dropped from scope.
- **Manual remove:** Dropped from scope (option 13a).
- **Commit model:** Save-as-you-edit + Proceed flag (option 5c).
- **Conflict resolution on sync:** User edit wins, via extended `ManualOverride` (option 6a).
- **Re-gating policy:** First sync + Update List with added rows + full sync. Quick price update does not re-gate.
- **Navigation after gate passed:** Land on Workspace directly; re-open Review via `LeftRail` button.
- **Inline edit UX:** Click-to-edit (option 9b). Photo opens upload/URL popover.
- **Proceed button gating:** Soft block — confirm dialog when blank fields detected (option 10c).
