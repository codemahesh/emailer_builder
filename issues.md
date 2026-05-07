# Dynamic Email Builder — Issues

24 vertical slices derived from `PRD.md`, `TECHNICAL_PRD.md`, and `UX_SPECS.md`. Each issue cuts end-to-end through schema → API → UI → tests and is independently demoable. HITL = requires human interaction (credentials, design input, security review). AFK = can be implemented and merged without human interaction.

---

## Issue 1: Walking skeleton — repo, auth, dashboard, empty campaign

**Type:** HITL

### What to build

The first end-to-end thread through every layer of the stack. A user signs in, lands on the campaign dashboard, creates a new campaign by entering a name and Google Sheet URL, and sees that empty campaign persisted. No sync, no rendering, no AI — only the spine.

The slice provisions Railway services (React static site, FastAPI app server, PostgreSQL, Redis), wires FastAPI-Users JWT auth with bcrypt and two roles (editor, reviewer — gating deferred to Issue 24), and scaffolds the global UI frame: top bar, breadcrumbs, status pill placeholder, avatar menu. The campaign workspace shell renders an empty left rail and a preview pane reading "Sync a Google Sheet to see your preview" — the rest of the workspace is empty containers waiting for later slices to fill in.

This is HITL because it requires cloud account creation, secret provisioning (OpenAI key, Sheets service account JSON, JWT secret), and database/Redis instance configuration. Subsequent slices can run AFK.

### Acceptance criteria

- [ ] Frontend (React + Vite), backend (FastAPI), Postgres, and Redis all deployed on Railway with environment variables wired
- [ ] `POST /auth/login` issues a JWT; `GET /auth/me` returns the current user
- [ ] Login screen renders per UX_SPECS §3.1 (single-column, 400px card, error states)
- [ ] Logged-in user sees campaign dashboard at `/campaigns` with "Start your first campaign" empty state per UX_SPECS §3.2
- [ ] "+ New Campaign" opens the modal per UX_SPECS §3.3; submitting persists `Campaign(name, sheet_url, owner_id, status='draft')` and redirects to `/campaigns/:id`
- [ ] Campaign workspace renders the global frame (top bar, breadcrumb `Campaigns / [name]`, status pill, avatar menu) and split-screen shell (380px left rail + preview pane placeholder)
- [ ] Dashboard lists the user's campaigns with name, status pill, last-modified timestamp, and overflow menu (Duplicate / Archive stubs are present but the actions can be no-ops in this slice)
- [ ] Logout invalidates the session and returns to login
- [ ] Database migrations checked in (Alembic) covering `User` and `Campaign`
- [ ] CI runs lint + type-check + a smoke test that registers a user, creates a campaign, and lists it

### Blocked by

None — this is the foundational slice.

---

## Issue 2: Google Sheets Full Sync

**Type:** AFK

### What to build

The first time the editor pastes a Sheet URL and clicks "Full Sync", the system reads the standard columns (`Section_Title`, `SKU`, `Product_Link`, `Priority`, `Price`, `UTM_Campaign`, `Button_Name`), runs `PriceFormatter` regex normalisation, runs `UTMBuilder` to stitch the global UTM prefix, and persists structured product records. The Sync panel in the left rail shows live progress ("Reading sheet… 12/40") and a final summary ("40 of 40 imported · 0 failures · 2 minutes ago") per UX_SPECS §3.5.1.

This slice does not yet scrape product pages or process images — products are stored with their Sheet-provided fields only. The Fast Sync button is hidden (UX_SPECS Pass 4 default: first sync is always Full).

### Acceptance criteria

- [ ] `SheetReader` module reads a Sheet via the configured service account, returns a typed list of product records, and isolates Sheets API logic from HTTP/DB layers
- [ ] `PriceFormatter` normalises a range of raw price strings (with/without symbol, decimal variations, negative prices) and is unit tested
- [ ] `UTMBuilder` concatenates global prefix + sheet UTM correctly with empty/null edge cases and is unit tested
- [ ] `POST /campaigns/:id/sync/full` enqueues sync, returns a job id, emits progress over WebSocket, and persists `Section` + `Product` rows linked to the campaign
- [ ] Sync panel UI shows: status dot (success/warn/danger), progress bar while running, summary counts when done, failure-row drawer when partial per UX_SPECS §3.5.1
- [ ] Sync confirmation dialog appears for Full Sync and warns it will discard non-overridden assets (manual overrides not yet implemented — copy still present for future-proofing)
- [ ] Auth-protected error states named: "Could not access sheet — share with `<service_account_email>`" with copyable email per UX_SPECS Pass 6 risk #1
- [ ] Unit tests: `SheetReader` parsing with mocked API responses, `PriceFormatter` edge cases, `UTMBuilder` concatenation
- [ ] Integration test: end-to-end sync against a fixture Sheet returns expected product count

### Blocked by

Issue 1.

---

## Issue 3: Product scraping + Coming-Soon placeholder + manual replacement

**Type:** AFK

### What to build

After Sheet sync persists raw product rows, a per-product `ProductScraper` job fetches the product page (httpx + BeautifulSoup), extracts product name and image URL, and stores them. When scraping fails or yields no usable image, a "Coming Soon" placeholder image is injected and the product card renders a yellow "Scrape failed — replace?" badge per UX_SPECS Pass 3 affordance row 5. The editor can click that badge to upload a replacement image (file upload or paste URL); the replacement bypasses the scraper entirely.

### Acceptance criteria

- [ ] `ProductScraper` module accepts a product URL, returns a typed `ScrapeResult` (success | failed-with-reason), and is isolated from queue/DB/image pipeline
- [ ] Scraping runs as part of the sync pipeline behind `JobQueue` (ARQ) so the UI is not blocked
- [ ] Failed scrapes inject a configurable `coming-soon.png` and persist a `scrape_failed=true` flag on the product
- [ ] Quality warning card UI (UX_SPECS §3.7.4) opens when the user clicks the "Scrape failed" badge: tabs for Upload / URL, drop-zone, validates that the input is a valid image
- [ ] Replacement upload writes through `ImageStore` (local filesystem adapter) and updates the product image URL; "Manual" provenance pill appears on the product card per UX_SPECS §3.6.2
- [ ] Per-product progress is reflected in the Quality Warnings panel count per UX_SPECS §3.5.3
- [ ] Unit test: `ProductScraper` returns failed result when page lacks expected structure
- [ ] Integration test: a campaign sync where one URL 404s ends with one Coming-Soon product and a working manual upload flow

### Blocked by

Issue 2.

---

## Issue 4: Image quality gate + processing pipeline + WebSocket progress + SKU cache

**Type:** AFK

### What to build

Every scraped image runs through `ImageQualityGate` (Laplacian-variance blur check + dimension check) producing PASS / WARN / FAIL. PASS and WARN images enter `ImageProcessor` (REMBG background removal, optional Real-ESRGAN upscale on WARN, centred 10% padding crop, composited onto a placeholder neutral background — the orchestrator-supplied colour comes in Issue 6). FAIL images skip processing and emit a quality warning to the UI. Processed images are stored via `ImageStore` and cached by SKU in Redis. Progress is streamed to the client over WebSocket.

### Acceptance criteria

- [ ] `ImageQualityGate` is a pure function returning `{verdict, reason}`; tested with a synthetic sharp image (PASS), a blurred image (FAIL), and a small image (WARN) generated programmatically
- [ ] `ImageProcessor` is a pure function (input: bytes + config; output: bytes) with no DB/queue/HTTP knowledge
- [ ] `ImageStore` interface (`write(bytes) → url`, `read(url) → bytes`) with a local filesystem adapter and a stable URL served via FastAPI static route
- [ ] `SKUCache` (Redis) skips reprocessing on cache hit; manual overrides write directly into the cache
- [ ] `JobQueue` (ARQ + Redis) runs image processing per product; `WebSocketGateway` routes per-job progress events to the connected React client
- [ ] Live preview tile state per UX_SPECS §3.5.3 / §3.6.2: shimmer skeleton during processing, processed image on success, red-bordered tile + "Processing failed — upload a replacement" on error
- [ ] Quality Warnings panel (UX_SPECS §3.5.3) lists all FAIL and WARN items with Replace / Keep affordances; FAIL items cannot be dismissed without replacement; replacements re-run through `ImageQualityGate` (Pass 6 risk #8)
- [ ] Integration tests: a real low-resolution image triggers upscaling, a high-resolution image skips it; SKU cache hit returns the cached URL on second sync

### Blocked by

Issue 3.

---

## Issue 5: MJML renderer + default template + priority columns + ToC + viewport toggle

**Type:** AFK

### What to build

After sync produces products, the campaign workspace renders a live email preview by compiling an MJML document on the FastAPI server and serving the HTML into a sandboxed iframe in the React preview pane. Layout uses one default template: priority-driven columns (High = full-width hero, Medium = 2-column, Low = 3-column), products grouped into `<mj-section>` per `Section_Title`, and an icon-based Table of Contents row at the top driven by `IconToCMapper` against a stub keyword table. The viewport toggle (Desktop 600px / Mobile 375px) animates the iframe width per UX_SPECS §3.4.

### Acceptance criteria

- [ ] `MJMLRenderer` is a pure function: identical inputs produce identical HTML; owns priority-to-column mapping; substitutes manual overrides at this layer (interface ready for Issue 11)
- [ ] `IconToCMapper` is a pure function returning ordered icon assignments; unmatched titles get a default icon; unit tested
- [ ] `POST /campaigns/:id/render` returns compiled HTML; React renders it into an iframe sandboxed with `sandbox="allow-same-origin"`
- [ ] Live preview refreshes within 1–2s of any layout-affecting change (debounced)
- [ ] Viewport segmented control (UX_SPECS §3.4) toggles iframe width 600px ↔ 375px with `motion-default` 240ms transition
- [ ] Bottom status strip in preview pane shows live KB readout, section count, product count per UX_SPECS §3.4
- [ ] Empty / loading / success / error preview states match UX_SPECS §3.6 Live Preview Canvas table
- [ ] Unit tests: priority assignments produce correct column counts; ToC rows generated for each section title; locked sections (when present in input) are preserved verbatim

### Blocked by

Issue 2.

---

## Issue 6: VisualOrchestrator + visual brief panel + first-render-before-banners

**Type:** HITL

### What to build

After sync completes, `VisualOrchestrator` makes a single GPT-4o call (server-side key) returning a structured JSON visual brief: campaign theme, selected layout template id, colour palette (background, section, accent, button), product background colour, font hierarchy (h1/h2/body sizes), and a DALL-E 3 prompt. The brief is persisted, applied to MJML rendering immediately, and surfaced in the Visual Brief panel (UX_SPECS §3.5.2) showing theme name, palette swatches, template name, font preview, and "Influenced by your preferences" line (preference injection ships in Issue 17 — line is rendered with a stub state for now).

The initial preview renders with the brief's tokens before banner generation begins — banners are async (Issue 7). Pass 6 constraint 5: first preview within 4s of sync completion.

This is HITL because the system prompt must be hand-reviewed for prompt injection (product names and section titles arrive from a Google Sheet and could attempt to override instructions; per Tech PRD Further Notes the prompt is a "critical security boundary"). The reviewed system prompt is committed alongside the code.

### Acceptance criteria

- [ ] `VisualOrchestrator` module accepts (section_titles, product_names, brand_tokens, preference_context_stub) and returns a typed `VisualBrief`
- [ ] System prompt enforces JSON-only output; product/section text is injected as user-role data, never instruction; refusal patterns documented; reviewed against prompt-injection cases (e.g. a product name like `"Ignore previous instructions and..."`)
- [ ] `VisualBrief` is persisted in Postgres and linked to the campaign
- [ ] `MJMLRenderer` consumes brief tokens (palette, fonts, product background colour) on every render
- [ ] Visual Brief panel UI matches UX_SPECS §3.5.2: AI sparkle pill, theme name, 5 palette swatches (clickable to inspect), template name (link to picker — picker ships in #8), font preview, "Influenced by your preferences" line, [Vibe Shift] [Override theme] buttons (handlers stubbed)
- [ ] First preview renders with brief tokens within 4s of sync completion (measured); banner slot shows palette-driven gradient placeholder per UX_SPECS Pass 4 / §3.6.3
- [ ] Visual Brief states (empty / loading / success / partial / error) per UX_SPECS §3.5 Visual Brief table
- [ ] Test: orchestrator output schema validation rejects malformed responses; prompt-injection fixture ("ignore instructions") yields a refusal or sanitised brief, not raw HTML
- [ ] Test: token cap on preference injection (10 strongest signals max) — assertable when Issue 17 lands; for now the cap is enforced on a stub context

### Blocked by

Issues 4 and 5.

---

## Issue 7: ArtistAgent — async banner + offer-strip generation + variant switcher

**Type:** AFK

### What to build

After the visual brief is ready, `ArtistAgent` is enqueued to call DALL-E 3 with the brief's prompt and produce 3 hero banner variants and a matching set of offer strips. Generation runs in the background; the editor keeps working in the meantime. Generated assets stream in via WebSocket, fading the placeholder out and the real banner in (UX_SPECS §5.3 banner swap-in). The banner variant switcher (UX_SPECS §3.6.3) shows variant 1 active by default with thumbnails for variants 2 and 3; clicking a thumb swaps the active banner, and each thumb has hover thumbs-up/down for preference capture (signals consumed in Issue 17).

### Acceptance criteria

- [ ] `ArtistAgent` accepts a DALL-E prompt, returns 3 banner URLs + N offer strip URLs (N = number of major sections, capped)
- [ ] Generation runs as an ARQ job; `WebSocketGateway` emits `banner_ready` events with campaign id and variant index
- [ ] Generation status pill in preview toolbar: "✦ Generating 2 banners…" while running, dismisses on complete (UX_SPECS §5.5)
- [ ] Banner swap-in animation: placeholder fades out 160ms, real banner fades in 240ms, 80ms overlap; "✦ generated" toast bottom-right of preview for 3s
- [ ] Variant switcher renders 3 thumbs (80×40); active has `brand-primary` border; click swaps; thumbs have hover thumbs-up/down (records preference signals — Issue 17 consumes them; storage layer in this slice writes signal rows)
- [ ] Failed generation state per UX_SPECS §3.5 Visual Brief table partial row: grey block + "Banner generation failed — retry or upload your own"; retry and upload affordances present (upload uses Issue 11's manual override flow)
- [ ] Test: WebSocket event delivery for a banner-ready job updates the correct campaign in the React store
- [ ] Test: variant click reorders the active variant in MJML render output

### Blocked by

Issue 6.

---

## Issue 8: TemplateLibrary + manual template picker + Save-as-Template

**Type:** HITL

### What to build

`TemplateLibrary` (Postgres-backed) stores layout templates. Templates have two sources: AI-generated (created automatically by `VisualOrchestrator` selection runs — wired here) and designer-saved (created by an editor's "Save as template" action on the current campaign). The Template Picker drawer (UX_SPECS §3.7.2) shows a "Recommended for this campaign" rail of 3 cards followed by an "All templates" grid filterable by source (All / AI / Saved). Each tile displays a thumbnail, name, and source pill (✦ AI / ✋ Saved by [name]). The Visual Brief panel's template name links to the picker; manual selection survives Vibe Shift (Issue 15) per UX_SPECS Pass 1 principle #2.

This is HITL because designer input is required: at least 2–3 hand-built seed templates must be loaded into the library for the AI's selection logic to have meaningful options. Both paths (AI generation + designer addition) are wired in this slice; designer seeds ship as fixtures committed with the slice.

### Acceptance criteria

- [ ] `Template` schema: (id, name, source ∈ {ai, designer}, structural_pattern, visual_style_json, created_by, created_at)
- [ ] `TemplateLibrary` query interface: filter by source, structural type, recency; returns ordered candidates
- [ ] `VisualOrchestrator` queries `TemplateLibrary` for candidates and returns the selected template id in the visual brief; when no AI templates exist yet, the orchestrator falls back to the highest-priority designer template
- [ ] At least 3 designer seed templates committed as fixtures and loaded by Alembic data migration
- [ ] Template Picker drawer matches UX_SPECS §3.7.2: filters tabs, recommended rail, all-templates grid, source pills, [Cancel] / [Apply template] footer
- [ ] "Save as template" action lives in the Visual Brief panel; opens a small dialog asking only for a name; on save, current campaign's structural pattern + visual brief tokens are persisted as a new designer template
- [ ] Manually applied template is marked pinned and survives Vibe Shift (handler honoured by Issue 15 when it lands; this slice writes the pin flag)
- [ ] Test: orchestrator's selection returns a designer template when no AI templates exist; "save as template" round-trips a template that re-applies cleanly

### Blocked by

Issue 6.

---

## Issue 9: Manual theme override + theme picker + pinned theme

**Type:** AFK

### What to build

The Theme Picker drawer (UX_SPECS §3.7.1) lets the editor override the AI's chosen palette + typography. Themes are a separate table from templates — they pair colour tokens with font choices and apply on top of the structural template. When an editor manually applies a theme, it is "pinned" on the visual brief: subsequent AI suggestions and Vibe Shifts (Issue 15) preserve the pinned theme per UX_SPECS Pass 1 principle #2. The chat (Issue 14) can also apply themes by name; until then, application is via the picker only.

### Acceptance criteria

- [ ] `Theme` schema with palette (background, section, accent, button), typography (heading + body font, h1/h2/body sizes), and `pinned_at_campaign` linkage
- [ ] Theme Picker drawer matches UX_SPECS §3.7.1: 240×140 preview cards in a 2-col grid, selected card with `brand-primary` 2px border + check, [Cancel] / [Apply theme] footer
- [ ] Applying a theme writes a pin record on the campaign's visual brief and re-renders MJML
- [ ] Visual Brief panel shows a "pinned" indicator next to the palette/font row when a manual theme is active
- [ ] Pin survives subsequent orchestrator regenerations (Vibe Shift and theme regen ignore pinned themes)
- [ ] At least 6 seed themes shipped as fixtures (e.g. Bold Premium, Minimal Light, Festive, Tech Cool, Warm Neutral, High Contrast)
- [ ] Test: pinned theme persists after a simulated orchestrator regeneration; clearing the pin restores AI control

### Blocked by

Issue 6.

---

## Issue 10: Section locking

**Type:** AFK

### What to build

Each rendered section has a padlock toggle in its header (UX_SPECS §3.6.1). Locked sections show a 2px `prov-locked` left edge plus a small padlock in the upper-left corner (always visible). Locked sections are excluded from any AI shuffles, theme regenerations, or chat layout commands. Lock state is persisted per section. Fast Sync (Issue 13) still updates Price/UTM within locked sections — the lock scope is layout, not data.

### Acceptance criteria

- [ ] `Section.locked: bool` schema field, persisted via `CampaignRepository`
- [ ] Padlock toggle UI per UX_SPECS §3.6.1: hover-only chrome, click toggles state, locked sections show persistent left-edge treatment + tooltip "Locked: AI will not modify. Fast Sync still updates prices."
- [ ] Locked-section list also exposed in the rail (e.g. as count badge on the Visual Brief panel) so editors can see lock state without hunting
- [ ] `MJMLRenderer` reads the lock flag and preserves locked-section structure verbatim
- [ ] AI integrations (orchestrator regen + chat — wired now, consumed by future slices): pass `locked_section_ids` into prompts; system prompts must refuse to modify them
- [ ] Test: a locked section's MJML output is byte-identical before and after a simulated regeneration command
- [ ] Test: chat command (stubbed) attempting to reorder a locked section is rejected with a structured error

### Blocked by

Issue 5.

---

## Issue 11: Manual asset override (canvas Replace + chat URL/upload + Revert to AI)

**Type:** AFK

### What to build

`ManualAssetOverride` accepts a replacement asset for any banner, offer strip, or product image. The editor can override via two paths with input parity (UX_SPECS Pass 6 constraint 13): the canvas hover Replace pencil (UX_SPECS §3.6.2) opening an upload-or-URL panel, or the chat panel attaching a file or pasting a URL with a parser that recognises "replace the hero banner with [URL]" and "replace the image for [product name] with [URL or attachment]" patterns. On override, the asset shows a Manual provenance pill with a "Revert to AI" link on hover. Overrides persist per (campaign, target_type, target_id) and are substituted by `MJMLRenderer` before compilation. Overrides survive Fast Sync (Issue 13).

### Acceptance criteria

- [ ] `ManualOverride` schema: (id, campaign_id, target_type ∈ {hero_banner, offer_strip, product_image}, target_id, override_url, created_at, created_by)
- [ ] `ManualAssetOverride` module: accepts upload bytes or URL, validates as image, fetches URL with size/MIME guards, writes through `ImageStore`, persists override, writes into `SKUCache` for product images
- [ ] Canvas hover state matches UX_SPECS §3.6.2: provenance pill (top-left), action menu (top-right), Replace opens upload-or-URL panel
- [ ] Chat parser recognises both override patterns and disambiguates ("I see one hero banner. Replace it with the URL above?") per UX_SPECS Pass 6 risk #13; parser is unit tested with ambiguous inputs
- [ ] Override states match UX_SPECS §3.5 Manual Override Indicator table: empty / loading / success / partial / error
- [ ] Revert to AI clears the override and restores the prior asset URL; provenance pill switches back to AI
- [ ] Replacement assets re-run through `ImageQualityGate`; FAIL re-opens the warning card with the new verdict (Pass 6 risk #8)
- [ ] Test: override survives a simulated Fast Sync; clear restores the AI asset; chat parser correctly resolves ambiguous targets

### Blocked by

Issue 5.

---

## Issue 12: Inline text edit + edited-dot + Full Sync warning

**Type:** AFK

### What to build

The editor can click product names and button labels in the preview iframe to edit them inline (`contenteditable`, save on blur, `Enter` saves, `Esc` cancels per UX_SPECS §6 keyboard parity). After an edit, a 4px `info-600` "edited" dot appears next to the field with tooltip "Edited locally — Full Sync will revert" (UX_SPECS §3.6.2). A subsequent Full Sync prompts a confirmation modal listing "X inline text edits will be discarded — keep them?" with a "Convert text edits to overrides instead" preselected option (UX_SPECS §5.3 Full Sync flow / Pass 6 risk #4).

### Acceptance criteria

- [ ] Inline contenteditable on product name and button label only (other text remains immutable)
- [ ] Edits persist as `TextOverride(campaign_id, target_type, target_id, field, override_value)` rows; `MJMLRenderer` substitutes overrides at render time
- [ ] Edited dot indicator + tooltip per UX_SPECS §3.6.2
- [ ] Full Sync confirmation modal lists count of inline edits; "Convert text edits to overrides" toggle preselected when edits exist; on confirm, edits become overrides instead of being discarded
- [ ] Test: edit → blur → render shows new text; Full Sync without conversion reverts; Full Sync with conversion preserves
- [ ] Test: keyboard `Esc` cancels uncommitted edit, `Enter` commits

### Blocked by

Issue 5.

---

## Issue 13: Fast Sync — price/UTM-only refresh respecting locks + manual overrides

**Type:** AFK

### What to build

The Fast Sync button (now visible because Full Sync has run at least once) triggers a non-destructive refresh: re-read the Sheet, update only Price and UTM fields on existing products, never touch images, layout, locked-section structure, manual overrides (Issue 11), or text overrides (Issue 12). No confirmation needed (Pass 3 affordance row 3). Sync panel shows "Reading prices… 12/40" progress.

### Acceptance criteria

- [ ] `POST /campaigns/:id/sync/fast` endpoint runs `SheetReader`, diffs Price + UTM on each existing product, updates only those fields
- [ ] Manual overrides, text overrides, locked sections, processed image URLs, and visual brief are untouched
- [ ] Fast Sync button hidden until first successful Full Sync; tooltip differentiator "Full = re-scrape everything · Fast = update prices/UTMs in locked sections" per UX_SPECS Pass 6 risk #7
- [ ] Sync panel progress UI same as Full Sync but with adjusted copy
- [ ] Snapshot is created automatically before Fast Sync runs (Issue 16 wiring; if Issue 16 not yet shipped, snapshot logic is added in this slice and consumed by Issue 16)
- [ ] Test: a campaign with manual overrides, text overrides, and locked sections retains all of them after Fast Sync; Price + UTM diffs are applied
- [ ] Test: products absent from the Sheet are not deleted in Fast Sync (only present-row updates)

### Blocked by

Issues 10 and 11.

---

## Issue 14: AI Chat panel — layout commands, JSON-only, Apply/Discard diff preview

**Type:** HITL

### What to build

The chat panel (UX_SPECS §3.5.4) lets the editor send natural-language instructions. The frontend sends them to GPT-4o with a hardened system prompt that requires JSON command output strictly against a small enum (reorder_section, swap_products, apply_design_token, replace_asset, apply_theme_by_name, apply_template_by_name). The frontend translates the JSON into pre-approved MJML state mutations — the AI never writes HTML directly (Tech PRD Risk Mitigation §172). Every AI response is presented as a proposal card with a one-line diff summary and Apply / Discard buttons (UX_SPECS §3.5.4). Locked sections are passed in context and the AI is required to refuse modifications to them with a structured error. Example chips show on first load and hide after N user messages.

This is HITL because the system prompt is a security boundary (prompt-injection from chat input + tool-output drift) and must be reviewed before merge.

### Acceptance criteria

- [ ] `POST /campaigns/:id/chat` accepts a user message, returns a proposal containing: human-readable summary, JSON command list, diff preview text, locked-section refusal flags
- [ ] System prompt enforces JSON schema; output is validated and rejected with a re-prompt on parse failure (max 1 retry)
- [ ] JSON command schema covers the v1 enum; any command outside the enum is treated as a refusal
- [ ] Chat UI matches UX_SPECS §3.5.4: bubble alignment, AI proposal card with Apply/Discard, file attach (📎) accepts images, URL paste auto-detects and offers Replace inline (Issue 11 handles the mutation)
- [ ] Apply applies the JSON commands to campaign state and re-renders MJML; Discard does nothing
- [ ] Locked-section attempts produce the partial state per UX_SPECS §3.5 AI Chat table: "Cannot modify locked section 'Footwear'" with one-click unlock affordance per Pass 6 risk #6
- [ ] Example chips render on first load and hide after 5 user messages
- [ ] Tests: prompt-injection fixtures fail safely; JSON schema validation rejects malformed AI output; locked-section command produces refusal; Apply round-trips through MJML render

### Blocked by

Issues 5 and 10.

---

## Issue 15: Vibe Shift — regenerate brief + assets, preserve modal

**Type:** AFK

### What to build

Vibe Shift triggers a full regeneration: `VisualOrchestrator` is re-invoked with a user-supplied directive ("make it more urgent") plus the existing campaign context, producing a new visual brief; `ArtistAgent` regenerates banners and offer strips. Pinned themes (Issue 9), locked sections (Issue 10), manual overrides (Issue 11), and text overrides (Issue 12) are preserved verbatim. A confirmation modal (UX_SPECS §5.3 Vibe Shift flow) lists exactly what will regenerate vs preserve before the user commits, so they can never lose manual work silently (Pass 6 risk #2).

### Acceptance criteria

- [ ] Vibe Shift entry points: button in Visual Brief panel + chat command (parsed by Issue 14's enum)
- [ ] Confirmation modal renders two columns: "Will regenerate" (palette, hero banner, offer strips, fonts) and "Will preserve" (N locked sections, M manual overrides, pinned theme if any) — counts populated dynamically
- [ ] On confirm, an automatic snapshot is taken (Issue 16 wiring), then orchestrator + artist run; UI shows generation status pill + banner skeletons
- [ ] Pinned theme is preserved (the orchestrator receives the pin and emits a brief consistent with it for non-pinned axes only)
- [ ] Test: a campaign with locks, manual overrides, and pinned theme runs Vibe Shift and emerges with all of them intact; only non-locked, non-overridden sections + non-pinned brief axes change
- [ ] Test: directive text reaches the orchestrator's user-role context, does not corrupt the system prompt

### Blocked by

Issues 6 and 14.

---

## Issue 16: Snapshot timeline + restore

**Type:** AFK

### What to build

Significant changes (sync, vibe shift, theme apply, template apply, restore, lock toggle on >N sections, chat-applied command) auto-save a snapshot of the campaign's MJML-state JSON. The Snapshots panel (UX_SPECS §3.5.5) shows a reverse-chronological list with summary chips. Clicking a snapshot opens a non-destructive preview overlay with a yellow ribbon "Previewing 14:12 — read only". Restoring a snapshot first auto-snapshots the current state, then applies the chosen one (Pass 4 default — every restore is reversible).

### Acceptance criteria

- [ ] `Snapshot` schema: (id, campaign_id, mjml_state_json, summary_chip, created_at, created_by)
- [ ] Snapshot taken automatically on the listed trigger events; manual `Cmd/Ctrl+S` shortcut also forces a snapshot per UX_SPECS §5.4
- [ ] Snapshots panel UI matches UX_SPECS §3.5.5: filled `brand-primary` dot for current, hollow for older, summary chip per snapshot, "Show all" link when collapsed
- [ ] Click a snapshot tile → preview overlay (full preview pane replaced) with [Exit preview] / [Restore this version] and yellow ribbon
- [ ] Restore confirmation defaults to "Snapshot the current state first?" yes; on confirm, current state is captured, snapshot is applied, toast confirms
- [ ] Snapshots persist across sessions
- [ ] Test: restore round-trip preserves locks, manual overrides, pinned theme, text overrides
- [ ] Test: restoring snapshot N from a state with locks captures the pre-restore state as snapshot N+1

### Blocked by

Issue 5.

---

## Issue 17: Preference Memory — thumbs ±, implicit accept/revert, inject into orchestrator, reset

**Type:** AFK

### What to build

`PreferenceMemory` records two kinds of signals per editor: explicit (thumbs up/down on AI-authored cards — banner variants, theme summary, suggested layout — UX_SPECS Pass 3 affordance row 16) and implicit (accept = editor kept the AI's suggestion through to export or snapshot; revert = editor restored a snapshot that removed the AI's suggestion — Tech PRD Further Notes high-weight signal). `get_context(editor_id)` produces a natural-language summary capped at 10 strongest signals and is injected into `VisualOrchestrator` system prompt at new-campaign creation only (no mid-session adjustment). The "My Preferences" account page (UX_SPECS §3.10) shows current chips with delete-each and a "Reset all" button. Preferences are personal; never shared with teammates.

### Acceptance criteria

- [ ] `UserPreference` schema: (editor_id, signal_type ∈ {explicit_positive, explicit_negative, implicit_accept, implicit_revert}, asset_type, signal_value, campaign_id, created_at)
- [ ] Thumbs up/down handlers on banner thumbs (Issue 7), Visual Brief panel (theme card), and chat AI proposal cards write `explicit_*` rows
- [ ] Implicit signals: scheduled job (or post-export hook) records `implicit_accept` for AI suggestions present in the exported HTML; snapshot-restore handler records `implicit_revert` with high weight when the restore removed an AI suggestion
- [ ] `get_context(editor_id)` returns a natural-language string capped at 10 strongest signals (token cap per Tech PRD Further Notes)
- [ ] Visual Brief panel "Influenced by your preferences" line is now real; "Use neutral defaults this time" toggle (Pass 6 risk #9) bypasses injection per campaign
- [ ] My Preferences page (UX_SPECS §3.10) renders chips with × delete and "Reset all" button; reset confirmation per spec
- [ ] Test: thumbs-up on banner variant 2 then new campaign creation injects positive bias; reset clears all
- [ ] Test: implicit_revert weight outranks recent explicit signals when both target the same asset axis

### Blocked by

Issues 6 and 16.

---

## Issue 18: ResponsivenessValidator — multi-device validation surfaced in audit

**Type:** AFK

### What to build

`ResponsivenessValidator` is a pure function that simulates rendering at 375px (mobile) and 600px (desktop) viewport widths against the compiled HTML structure and returns a list of flagged issues (image wider than container, text overflow risk, stacked columns exceeding safe height). Called by the Pre-Flight Auditor (Issue 19) and surfaced in the audit report. No UI of its own — the surface is the audit panel and the existing viewport toggle.

### Acceptance criteria

- [ ] `ResponsivenessValidator(html_string) → list[Issue]` is a pure function; no side effects
- [ ] Heuristics covered: `img` wider than parent's max-width; `mj-column` width sum exceeding 600px desktop / 375px mobile; text element exceeding container with `nowrap`
- [ ] Each `Issue` has: severity (warn/error), description, target section_id or product_id, viewport (mobile/desktop)
- [ ] Test: synthetic HTML with a 700px-wide image flags a desktop and mobile error; clean HTML returns an empty list
- [ ] Test: stacked columns producing >2400px stacked mobile height returns a warn (configurable threshold)

### Blocked by

Issue 5.

---

## Issue 19: Pre-Flight Auditor + Export drawer + Copy-to-CleverTap

**Type:** AFK

### What to build

`PreFlightAuditor` is a pure function returning a structured audit report: minified file size in KB, presence of `{{unsubscribe_link}}` and `{{view_in_browser}}` (hard-stop if missing), UTM coverage (soft warning if any product missing UTM), responsiveness issues from `ResponsivenessValidator` (severity-aware), file size warnings (soft at 90KB, hard at ≥102KB). The Export drawer (UX_SPECS §3.7.3) is the only surface from which the editor can copy CleverTap-ready HTML (Pass 6 constraint 8). Hard-stops disable the Copy button; soft warnings are advisory. Approval status is shown but never gates (Pass 6 risk #14). On Copy: minified HTML lands on the clipboard, success toast "Copied · 87KB · ready to paste", drawer auto-closes after 2s. CleverTap unsubscribe + view-in-browser tags are auto-injected into the default footer (Pass 4 default — failure is opt-in by editor removing them).

### Acceptance criteria

- [ ] `PreFlightAuditor(html_string, config) → AuditReport` is a pure function; tested across all combinations of missing tags, oversized HTML (102KB exact boundary), missing UTMs, responsiveness failures, and clean HTML
- [ ] `POST /campaigns/:id/audit` returns the report; minification runs server-side using a stable HTML minifier
- [ ] Export drawer matches UX_SPECS §3.7.3: pre-flight rows by status (pass/warn/hard-stop), approval informational row, [Copy to CleverTap] button disabled when hard-stops exist, tooltip on disabled button lists remaining hard-stops
- [ ] Default footer template includes both CleverTap tags; auditor checks for their presence in the final compiled HTML, not just the template
- [ ] Live KB indicator in workspace footer: `neutral-400` < 90KB, `warn-600` 90–101KB, `danger-600` ≥102KB (UX_SPECS §5.5)
- [ ] Copy-to-clipboard handler writes minified HTML; success toast with size readout
- [ ] `Cmd/Ctrl + E` keyboard shortcut opens Export drawer
- [ ] Test: 102KB exact boundary case, audit returns hard-stop; 101KB returns soft warning; missing tag returns hard-stop and disables Copy

### Blocked by

Issues 5 and 18.

---

## Issue 20: Ghost URL + reviewer surface (read-only, responsive, no edit DOM)

**Type:** AFK

### What to build

The "Share for review" button generates a UUID v4 Ghost URL (Tech PRD Further Notes — never an incrementing integer) at `/preview/:token`. The route is unauthenticated and renders the latest compiled HTML preview. The reviewer surface (UX_SPECS §3.8) is the only fully responsive product surface (Pass 6 constraint 7 + 10) and contains zero editing affordances in the DOM — not greyed-out, not permission-checked, but absent. Sticky top bar shows campaign name + last-modified + viewport toggle; sticky bottom bar shows comments count (Issue 21) and Approve button (Issue 22). On mobile, the comment pin affordance becomes a floating action button.

### Acceptance criteria

- [ ] Editor's "Share for review" button generates a UUID v4 token, persists `(campaign_id, token, created_at)`, copies the URL to clipboard, and shows the share panel with [Copy] + [Mark as In Review] toggle
- [ ] `/preview/:token` route renders without auth, returns 404 for unknown tokens, and returns "This preview link is no longer valid" for archived campaigns (UX_SPECS §3.5 Reviewer Ghost URL error row)
- [ ] Sticky top bar (48px) per UX_SPECS §3.8: campaign name, last-updated timestamp, Desktop/Mobile toggle (no avatar)
- [ ] Sticky bottom bar (64px) with Comments count placeholder (Issue 21) and Approve button placeholder (Issue 22)
- [ ] Reviewer DOM contains zero edit affordances: no Replace pencil, no padlock toggle, no chat input, no provenance action menus — verified by snapshot test
- [ ] Surface is fully responsive down to 320px width
- [ ] Test: unauth GET renders preview; auth-only routes still 401 to anonymous users; UUID v4 enumeration produces 404 not enumerable patterns

### Blocked by

Issue 5.

---

## Issue 21: Reviewer comments + comment thread visible in editor

**Type:** AFK

### What to build

On the Ghost URL surface, hovering any section reveals a "Comment" pin affordance; clicking drops a numbered pin and opens a text field. Comments are stored with a `section_id` reference so that when the editor restores a snapshot (Issue 16) the UI can mark the comment as "Made on a previous version" and resolve it automatically if its section_id no longer exists (Tech PRD Further Notes). On the editor side, the workspace shows the reviewer comments overlay in the preview pane and a list view in the left rail; each thread supports Resolve and Reply only — no reassign, no status, no ceremony (Pass 4 simplification).

### Acceptance criteria

- [ ] `Comment` schema: (id, campaign_id, section_id, author_name, body, resolved, parent_id, created_at)
- [ ] Reviewer surface: hover-spawned numbered pins (`info-600`); click → text field; submit creates comment; reviewers identify themselves by name when first commenting (no account)
- [ ] Mobile: floating "Comment" FAB; tap to enter pin-placement mode (UX_SPECS §3.8)
- [ ] Editor side: preview pane overlays comment pins on the iframe; clicking a pin scrolls left-rail thread into view; left rail thread shows Resolve / Reply only
- [ ] Snapshot interaction: when restoring a snapshot, comments whose `section_id` does not exist in the restored state are auto-resolved with a "Section removed in version X" note
- [ ] Bottom bar comments count (Issue 20 placeholder) renders the live count and opens a slide-up sheet of all comments
- [ ] Test: comment created on Ghost URL appears in editor view; resolving a comment hides it from the active thread but keeps it in audit history

### Blocked by

Issue 20.

---

## Issue 22: Approval workflow — mark In Review, Approve, audit log, status pill

**Type:** AFK

### What to build

The editor toggles "Mark as In Review" in the share panel (Issue 20) — campaign status flips to `in_review` and a notification row is logged. The reviewer's Ghost URL bottom bar shows a sticky Approve button; clicking opens the confirmation "This logs your approval — continue?" plus the desktop/mobile reminder ("You reviewed Mobile — also confirm Desktop?" if the desktop toggle was never engaged this session — Pass 6 risk #11). On approve, an `ApprovalEvent` row is written and the button transforms to `[ ✓ Approved at 14:23 ]` (disabled, `success-50` bg). Editor side: campaign status pill flips to Approved per UX_SPECS §3.2 dashboard. Approval is informational and never blocks export (Pass 6 risk #14) — the Export drawer's approval row simply reads "● Approved by Reema · 14:02" or "● Awaiting approval".

### Acceptance criteria

- [ ] Campaign status lifecycle: draft → in_review → approved; status changes are recorded as audit events
- [ ] `ApprovalEvent` schema: (id, campaign_id, reviewer_name, approved_at, viewport_confirmed ∈ {desktop, mobile, both})
- [ ] Mark-as-In-Review toggle in share panel; flip is reversible
- [ ] Approve button on Ghost URL bottom bar with confirmation modal + viewport reminder per Pass 6 risk #11
- [ ] After approval: button disables and labels with timestamp; editor's status pill updates in dashboard and workspace top bar
- [ ] Export drawer approval row pulls from the latest ApprovalEvent; tooltip clarifies "Approval is for audit, not gating"
- [ ] Test: approval does not block export; status transitions are recorded; viewport_confirmed reflects which toggles the reviewer engaged

### Blocked by

Issue 20.

---

## Issue 23: Global Settings — Headers/Footers, Brand Tokens, Keyword Mappings, UTM Prefix

**Type:** AFK

### What to build

A separate `/settings` route (UX_SPECS §3.9) with four tabs: Headers & Footers, Brand Tokens, Keyword Mappings, UTM Prefix. Edit-in-place pattern (no separate edit modes). Save bar (`elev-overlay`) appears at the bottom of the viewport on any unsaved change. Changes to Headers/Footers and Brand Tokens propagate to all newly generated campaigns automatically; existing campaigns are unaffected unless re-rendered. Brand tokens (primary colour, secondary colour, font families) are stored in Postgres and loaded at MJML compile time — no developer redeployment needed for token changes. Keyword Mappings power `IconToCMapper` (Issue 5).

Brand tokens, default header/footer copy, and the initial keyword→icon map ship as fixtures committed with the slice; subsequent edits flow through the UI.

### Acceptance criteria

- [ ] `/settings` route protected by editor role; admin-only fields (e.g. service-account email reference) gated by admin role placeholder (full role gating in Issue 24)
- [ ] Four tabs: Headers & Footers, Brand Tokens, Keyword Mappings, UTM Prefix per UX_SPECS §3.9
- [ ] Edit-in-place inputs; Save bar appears with [Discard] / [Save] on any unsaved change
- [ ] `GlobalSettings`, `KeywordMapping` schemas with single-row + multi-row patterns respectively
- [ ] `MJMLRenderer` reads Brand Tokens at every compile; `IconToCMapper` reads Keyword Mappings at every render
- [ ] CleverTap unsubscribe + view-in-browser tags are part of the default footer fixture (Issue 19's auditor verifies them)
- [ ] Add / edit / delete Keyword Mappings; tested round-trip including unmatched-title fallback
- [ ] Test: editing a brand token does not retroactively change rendered campaigns until each is re-rendered; new campaign immediately consumes the latest tokens

### Blocked by

Issues 1 and 5.

---

## Issue 24: Reviewer accounts + admin role + RBAC + accessibility/keyboard polish

**Type:** AFK

### What to build

Wire real role gating onto the auth scaffolding from Issue 1. Admins can create reviewer accounts via `/settings/users` (admin-only tab). Reviewer accounts have read-only access: they can view campaigns, comment, and approve, but cannot edit, sync, run AI, or export. Editor accounts continue to have full access. Also lands in this slice: campaign Duplicate and Archive actions (made stubs in Issue 1), keyboard shortcuts per UX_SPECS §5.4 (`Cmd/Ctrl+K` focus chat, `Cmd/Ctrl+S` force snapshot, `Cmd/Ctrl+E` Export drawer, `Cmd/Ctrl+Shift+L` lock/unlock focused section, `D`/`M` viewport, `Esc` close drawer, `↑`/`↓` cycle chat history), `Shift+/` shortcut overlay, and accessibility polish: focus rings, aria-labels, role="alert"/"status" on toasts, skip-link "Jump to comments" on Ghost URL.

### Acceptance criteria

- [ ] `User.role ∈ {editor, reviewer, admin}`; default is editor; admin role can be set only by another admin or seed migration
- [ ] Admin-only `/settings/users` page lists users and allows admin to create reviewer accounts (email + password); reviewer login redirects to a reviewer-only dashboard listing assigned campaigns
- [ ] Reviewers cannot reach editor-only routes (`/campaigns/:id/edit`, `/settings`); attempted access returns 403; the React app routes them to the read-only view
- [ ] Campaign Duplicate: creates a new campaign with copied sections, products, manual overrides, text overrides, locks, pinned theme; sync timestamps reset; status reset to draft
- [ ] Campaign Archive: sets `archived=true`, hides from default dashboard, accessible via "Show archived" filter
- [ ] All keyboard shortcuts per UX_SPECS §5.4 wired and dismissable via overlay
- [ ] All interactive elements have visible focus rings (2px `brand-primary`, never `outline: none`)
- [ ] All icons have aria-labels; toasts use `role="alert"` (error) / `role="status"` (success/info); skeleton containers `aria-busy="true"`; reviewer Ghost URL has `Jump to comments` skip link
- [ ] Test: reviewer cannot POST to editor-only endpoints; admin can create reviewer; duplicated campaign opens in draft with copied state; keyboard shortcut overlay opens with `Shift+/`

### Blocked by

Issues 1 and 20.
