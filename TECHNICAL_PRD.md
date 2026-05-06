# Technical PRD: Dynamic Email Builder — Implementation

## Problem Statement

Marketing managers and designers at the company spend 4+ hours per email campaign manually copying product details from the e-commerce site, formatting prices, building responsive HTML grids, writing UTM tags, and coordinating with external graphics teams for banners. Raw scraped product images suffer from broken links and inconsistent quality. Manually coded HTML frequently exceeds Gmail's 102KB clipping threshold or fails CleverTap's syntax requirements, discovered only at the point of deployment. There is no structured approval workflow, so stakeholder sign-off happens informally over chat with no audit trail. The AI has no memory of past creative decisions, so editors repeat the same corrections campaign after campaign.

---

## Solution

A web-based email campaign builder that connects to a Google Sheet as the single source of truth, automatically scrapes and processes product images from the company's own e-commerce site, runs an AI visual orchestration phase that selects a layout template and produces a complete creative brief before rendering begins, generates hero banners and offer strips asynchronously while the editor can already review the layout, and provides manual override controls for every AI-generated asset via both the UI and a chat interface. A per-editor preference memory biases future AI recommendations toward each editor's accepted choices. A structured review-and-approval workflow and a pre-flight compliance audit gate the final CleverTap HTML export.

---

## User Stories

### Authentication & Access

1. As an editor, I want to log in with a username and password, so that only authorised team members can access the builder.
2. As an editor, I want my session to persist across browser tabs without re-logging in, so that I can work across multiple windows efficiently.
3. As an admin, I want to create reviewer accounts with read-only access, so that approving managers cannot accidentally modify a campaign.
4. As a reviewer, I want to receive a direct link to the campaign preview without needing an account, so that external stakeholders can view the email without onboarding friction.
5. As an editor, I want to be able to log out from any device, so that I can secure my session after using a shared machine.

### Campaign Management

6. As an editor, I want to create a new campaign by giving it a name and pasting a Google Sheet URL, so that all product data is sourced from a single, familiar spreadsheet.
7. As an editor, I want to see a dashboard of all my campaigns with their status (Draft, In Review, Approved), so that I can quickly resume work on any active campaign.
8. As an editor, I want to duplicate an existing campaign, so that I can reuse a layout for a similar promotion without starting from scratch.
9. As an editor, I want to archive campaigns I no longer need, so that my dashboard stays uncluttered.
10. As an editor, I want each campaign to display its last-modified timestamp, so that I know which version is the most recent.

### Google Sheets Integration

11. As an editor, I want the system to read standard columns from my Sheet (Section_Title, SKU, Product_Link, Priority, Price, UTM_Campaign, Button_Name) automatically, so that I do not have to map columns manually.
12. As an editor, I want the system to run a Full Sync that re-scrapes all product data and images from the Sheet, so that I can build a campaign fresh from the latest product information.
13. As an editor, I want to run a Fast Sync that updates only Prices and UTMs for sections I have already locked, so that I can refresh pricing without losing approved layouts.
14. As an editor, I want the system to automatically stitch the Sheet's UTM_Campaign value with a Global UTM Prefix defined in settings, so that all UTMs are consistently formatted without manual concatenation.
15. As an editor, I want the system to apply a regex formatter to all scraped prices and display them in a standard localized currency format, so that no manual price correction is needed.
16. As an editor, I want to see a sync status indicator showing how many products were successfully imported and whether any failed, so that I can identify and fix data gaps before building the layout.

### Product Scraping

17. As a system, I want to scrape product name, price, image URL, and product URL from the company e-commerce site using the Product_Link column, so that the builder always has up-to-date product details.
18. As a system, I want to detect when a scrape returns no usable image and inject a "Coming Soon" placeholder image, so that the campaign layout is never broken by a failed scrape.
19. As an editor, I want to manually upload a replacement image for any product that failed to scrape, so that I can unblock the campaign without waiting for the scraper to be fixed.

### Image Quality Gate

20. As a system, I want to run a blur detection check on every scraped product image before processing begins, so that unrecoverably blurry images are identified early and do not waste processing time.
21. As a system, I want to flag any image whose pixel dimensions remain below threshold after upscaling, so that resolution failures are surfaced to the editor rather than silently producing a degraded result.
22. As an editor, I want to see a quality warning card on any product image that fails the blur or resolution check, so that I know exactly which assets need manual replacement.
23. As an editor, I want to upload a replacement image directly from the quality warning card via file upload or URL, so that I can fix bad assets in the same flow without navigating away.

### Image Processing Pipeline

24. As a system, I want to remove the background from each scraped product image and auto-crop the product dead-centre with 10% padding, so that all products appear uniform regardless of the original photo composition.
25. As a system, I want to detect images below 500×500px and apply AI super-resolution upscaling before processing, so that all product images meet a minimum quality standard without fabricating product details.
26. As a system, I want to apply the product background colour specified in the current campaign's visual brief to each processed product image, so that product tiles are visually cohesive with the email theme.
27. As an editor, I want to see a real-time progress bar while images are being processed in the background, so that I know the pipeline is running and can estimate when it will finish.
28. As a system, I want to cache processed images by SKU so that re-syncing a campaign does not reprocess images that have already been enhanced, so that Fast Sync completes quickly.
29. As an editor, I want processed images to remain available via a stable URL after processing is complete, so that the final email HTML never contains broken image links.

### AI Visual Orchestration Phase

30. As a system (VisualOrchestrator), I want to scan all Section_Title values and product names immediately after sync, deduce an overarching campaign theme, select a layout template, and produce a complete visual brief — including colour palette, product background colour, font size hierarchy, and a DALL-E prompt — before any layout is rendered, so that all downstream agents receive consistent creative direction.
31. As an editor, I want to see a default email preview within seconds of a sync completing, so that I am not blocked waiting for banner generation to finish.
32. As an editor, I want banner and strip generation to happen in the background after the initial preview renders, with assets swapping in as they complete, so that I can begin reviewing the layout structure while assets are being created.
33. As an editor, I want the AI's chosen theme, colour palette, and layout template to be displayed in a summary panel, so that I understand the creative rationale before making overrides.

### Template Selection & Management

34. As a system, I want to generate and select the most appropriate layout template based on the campaign's product count, section structure, and deduced theme, so that the email structure is optimised for the content without manual selection.
35. As an editor, I want to browse and manually select a layout template from a visual picker, so that I can override the AI's template choice when I have a specific layout in mind.
36. As an editor, I want to type a template preference in the chat (e.g. "use a flash sale layout"), so that I can switch templates without leaving the chat interface.
37. As an editor, I want to save the current campaign's layout and visual style as a named template, so that I can reuse a proven design for future campaigns without rebuilding it.
38. As an editor, I want to see AI-generated templates alongside designer-saved templates in the same picker, so that the library grows over time without me having to distinguish between sources.

### Manual Theme & Visual Override

39. As an editor, I want to open a theme picker and select from available visual themes (colour palette + typography) to override the AI's choice, so that I have final say on the email's visual personality.
40. As an editor, I want to type a theme preference in chat (e.g. "make it dark and premium"), so that I can redirect the AI's visual direction conversationally without navigating menus.
41. As an editor, I want any manually selected theme or template to be preserved through subsequent AI suggestions and Vibe Shift operations, so that my explicit choices are never silently overridden.

### Manual Asset Override

42. As an editor, I want to click on any banner, product image, or offer strip in the preview and replace it with my own file, so that I can override AI-generated assets without leaving the builder.
43. As an editor, I want to paste an image URL in the chat panel to replace a specific asset, so that I can quickly swap in approved brand assets from our CDN.
44. As an editor, I want to upload an image file directly in the chat panel to replace a specific asset, so that I can use locally stored files without needing to host them first.
45. As an editor, I want to edit product text (product name, button label) inline in the preview panel, so that I can fix copy issues without updating the Google Sheet and re-syncing.
46. As an editor, I want manual asset overrides to survive Fast Sync operations, so that images I deliberately replaced are not overwritten when prices are refreshed.
47. As an editor, I want to clear a manual override and revert to the AI-generated asset with one click, so that I can compare the two versions easily.

### AI Chat Interface

48. As an editor, I want to type natural language instructions in a chat panel to reorder sections, swap product positions, or apply design changes, so that I can modify the layout without touching code.
49. As an editor, I want the AI Chat to output JSON layout commands rather than raw HTML, so that the system applies changes using pre-approved MJML components and cannot break the layout structure.
50. As an editor, I want the AI Chat to respect locked sections and never modify them during global layout changes, so that approved work is never accidentally overwritten.
51. As an editor, I want to type a Vibe Shift instruction in chat (e.g. "make it more urgent") and have the VisualOrchestrator rewrite the creative brief and regenerate all assets, so that I can redirect the campaign's entire visual direction conversationally.

### Section Locking

52. As an editor, I want to toggle a padlock icon on any section to lock it, so that the section is excluded from AI shuffles and theme regenerations.
53. As an editor, I want locked sections to be visually distinct from unlocked sections in the builder, so that I can see at a glance which parts of the layout are protected.
54. As an editor, I want Fast Sync to update Price and UTM data within locked sections without altering their layout, so that I can keep product details current without losing my layout work.

### Multi-Device Validation

55. As a system, I want to validate the compiled HTML at mobile (375px) and desktop (600px) viewport widths and flag any layout issues, so that editors are alerted to responsiveness problems before export.
56. As an editor, I want to toggle between Desktop and Mobile viewport in the preview pane, so that I can verify the layout is responsive before sending.
57. As an editor, I want to see a list of responsiveness warnings (e.g. "image exceeds container width on mobile") in the pre-flight audit report, so that I can address layout issues before the campaign is sent.

### MJML Layout Generation

58. As a system, I want to automatically assign layout priority to products based on the Priority column (High = full-width 1-column, Medium = 2-column, Low = 3-column), so that the most important products receive the most prominent visual placement.
59. As a system, I want to group products into MJML section blocks based on their Section_Title, so that the email is logically structured by category.
60. As an editor, I want the system to automatically generate an icon-based Table of Contents at the top of the email mapped to each Section_Title using the keyword mapping library, so that readers can navigate long emails instantly.
61. As an editor, I want the live preview to refresh within 1–2 seconds of any layout change, so that I can evaluate modifications in near real-time.

### AI Preference Learning

62. As an editor, I want to give a thumbs up or thumbs down on any AI-suggested banner, layout, or theme choice, so that the system learns my preferences explicitly.
63. As a system, I want to track which AI suggestions an editor accepts, modifies, or reverts, so that implicit preference signals are captured without requiring manual feedback on every decision.
64. As an editor, I want the AI to bias its visual recommendations toward my past accepted choices in future campaigns, so that I spend less time correcting the AI's starting point over time.
65. As an editor, I want to view and reset my stored preferences at any time, so that I can start fresh if my brand style changes.
66. As an editor, I want my preference profile to be personal to my account, so that my individual style choices do not override my colleagues' preferences.

### Snapshot Sidebar & Version History

67. As an editor, I want the system to automatically save a snapshot of the MJML state each time I make a significant change, so that I have a complete history of the campaign's evolution.
68. As an editor, I want to click any snapshot timestamp in the sidebar to restore the email to that exact state, so that I can recover from a bad AI Chat suggestion without manually undoing changes.
69. As an editor, I want snapshot history to persist across sessions, so that I can return the next day and still revert to a previous version.

### Global Settings

70. As an editor, I want to manage standard Headers and Footers in a Global Settings tab, so that I do not have to rebuild them for every campaign.
71. As an editor, I want changes to Headers and Footers to propagate to all newly generated campaigns automatically, so that brand consistency is enforced without manual updates.
72. As an editor, I want to edit brand tokens (primary colour, secondary colour, font families) in the Global Settings tab, so that the MJML compiler always uses the correct design system values without a developer redeployment.
73. As an editor, I want to add, edit, and delete keyword-to-icon mappings (e.g. "Footwear" → Sneaker Icon) in the Global Settings tab, so that new product categories are supported without developer involvement.

### Review & Approval Workflow

74. As an editor, I want to generate a shareable Ghost URL for the current campaign preview, so that I can send it to a reviewer without them needing an account.
75. As an editor, I want to mark a campaign as "In Review" to notify the assigned reviewer, so that there is a clear handoff point in the workflow.
76. As a reviewer, I want to view the campaign preview at the Ghost URL on both desktop and mobile viewports, so that I can evaluate the email as recipients would see it.
77. As a reviewer, I want to leave inline comments on specific sections of the preview, so that my feedback is contextually attached to the relevant part of the email.
78. As an editor, I want to see all reviewer comments alongside the live preview, so that I can action feedback without switching between tools.
79. As a reviewer, I want to click an Approve button to mark the campaign as approved, so that there is a clear, auditable record of sign-off.
80. As an editor, I want approval to be optional and not block the export, so that time-sensitive campaigns are never held up by process.

### Pre-Flight Audit & Export

81. As an editor, I want the system to automatically check that the CleverTap unsubscribe tag and view-in-browser tag are present before export, so that I cannot accidentally send a non-compliant email.
82. As an editor, I want the pre-flight audit to display a hard-stop error if required CleverTap tags are missing, so that compliance is enforced at the point of export.
83. As an editor, I want a soft warning if the minified HTML exceeds 102KB, so that I am alerted to Gmail clipping risk before sending.
84. As an editor, I want a soft warning if any product UTMs are missing, so that campaign tracking is not silently broken.
85. As an editor, I want responsiveness validation failures to appear in the pre-flight audit, so that all compliance and quality checks are visible in one place before export.
86. As an editor, I want a "Copy to CleverTap" button that compiles, minifies, and copies the final HTML to my clipboard, so that I can paste it directly into CleverTap's template editor with zero reformatting.

---

## Implementation Decisions

### Modules

The following deep modules will be built. Each encapsulates significant logic behind a narrow, stable interface and can be tested in complete isolation.

**1. SheetReader**
Connects to the Google Sheets API using a Service Account JSON credential. Accepts a Sheet URL, reads the expected columns, and returns a structured list of product records. Owns price regex formatting and UTM stitching with the global prefix. No knowledge of the HTTP layer or database.

**2. ProductScraper**
Accepts a product URL from the company e-commerce site and returns a structured product record containing name, price, and raw image URL. Uses httpx and BeautifulSoup. Isolated from the queue, database, and image pipeline. Returns a typed result that includes a failure state when the page cannot be parsed, allowing callers to inject placeholder images.

**3. ImageQualityGate**
Accepts a raw image URL or bytes. Runs two checks in sequence: pixel dimension check (below 500×500px triggers upscaling flag) and Laplacian variance blur detection via OpenCV (below threshold triggers a FAIL result). Returns a structured quality result: PASS, WARN (low-res but upscalable), or FAIL (too blurry to recover). Has no knowledge of storage, queues, or the UI. Called before ImageProcessor in the pipeline. On FAIL, the job emits a manual override prompt rather than proceeding to processing.

**4. ImageProcessor**
Accepts a raw image URL, a processing configuration, and the product background colour from the active campaign's visual brief. Performs background removal via REMBG, applies AI super-resolution upscaling via Real-ESRGAN if flagged by the ImageQualityGate, auto-crops the product dead-centre with 10% padding, and composites the product onto the specified background colour. Returns processed image bytes. Has zero knowledge of storage, queues, or HTTP.

**5. ImageStore**
Abstracts image persistence behind a simple interface: write(bytes) → url, read(url) → bytes. The v1 implementation writes to the local filesystem and serves files via a FastAPI static route. The v2 implementation swaps the adapter for S3 + CloudFront. No other module references a storage provider directly.

**6. SKUCache**
Stores the mapping of SKU → processed image URL in Redis. Accepts a SKU and returns a cached URL or a cache miss. Used by the image processing job to skip re-processing already-enhanced products during Fast Sync. Manual overrides write directly to this cache, bypassing the processing pipeline entirely.

**7. VisualOrchestrator**
Accepts a list of section titles, product names, brand tokens, and the current editor's preference context from PreferenceMemory. Calls GPT-4o with a hardened system prompt that enforces structured JSON output. Returns a complete visual brief containing: campaign theme, selected layout template identifier, colour palette (background, section backgrounds, accent, button), product background colour, font size hierarchy (h1/h2/body), and a DALL-E 3 prompt for banner generation. This is a fast call — the brief is returned before any image processing begins. No knowledge of the HTTP layer or database.

**8. TemplateLibrary**
Stores named layout templates in PostgreSQL. Each template is a combination of an MJML structural pattern and a visual style descriptor. Templates are created in two ways: generated by the VisualOrchestrator and saved automatically, or saved explicitly by an editor via the "Save as Template" action on any campaign. Exposes a query interface that returns templates filtered by structural type, visual mood, or recency. The VisualOrchestrator calls this module to retrieve candidate templates before making its selection.

**9. ArtistAgent**
Accepts a DALL-E 3 prompt string from the VisualOrchestrator. Calls the DALL-E 3 API and returns three generated Hero Banner image URLs and a corresponding set of Offer Strip images. Runs asynchronously after the initial preview render. No knowledge of storage or campaigns.

**10. MJMLRenderer**
Accepts a campaign data structure (sections, products, priority assignments, visual brief tokens, header, footer, ToC mappings, manual overrides) and returns compiled HTML. Invokes the MJML compiler server-side. This module is a pure function — identical inputs always produce identical outputs. Owns the priority-to-layout mapping logic (High = 1-column, Medium = 2-column, Low = 3-column). Manual asset overrides are substituted at this layer before compilation.

**11. ResponsivenessValidator**
Accepts a compiled HTML string. Simulates rendering at 375px (mobile) and 600px (desktop) viewport widths using layout heuristics applied to the HTML structure. Returns a list of flagged issues (image wider than container, text overflow risk, stacked columns exceeding safe height). Pure function with no side effects. Called by the PreFlightAuditor.

**12. PreFlightAuditor**
Accepts an HTML string and an audit configuration. Returns a structured report containing: file size in KB, presence of required CleverTap tags, UTM coverage, responsiveness validation results from ResponsivenessValidator, and a list of hard-stop errors vs soft warnings. Pure function with no side effects.

**13. PreferenceMemory**
Stores per-editor preference signals in PostgreSQL. Two signal types: explicit (thumbs up/down recorded against a specific asset type, theme, or layout decision) and implicit (accept = editor kept the AI's suggestion through to export or snapshot; revert = editor restored a prior snapshot removing the suggestion). Exposes a `get_context(editor_id)` method that returns a formatted natural-language preference summary for injection into the VisualOrchestrator's system prompt. Exposes a `reset(editor_id)` method. Has no knowledge of the AI layer.

**14. ManualAssetOverride**
Handles replacement asset ingestion from both the UI panel (file upload) and the chat interface (file attachment or URL paste). Validates the asset (checks it is a valid image, fetches URL if provided). Writes the asset through ImageStore and records the override in PostgreSQL against the specific product or section. Overrides survive Fast Sync operations. Exposes a `clear(override_id)` method to revert to the AI-generated asset.

**15. UTMBuilder**
Accepts a campaign UTM slug and a global UTM prefix from settings. Returns the correctly concatenated UTM string. Pure function. Used by SheetReader and the export pipeline.

**16. PriceFormatter**
Accepts a raw price string and a locale config. Applies regex normalisation and returns a formatted localized price string. Pure function. Used by SheetReader.

**17. IconToCMapper**
Accepts a list of section titles and the current keyword-to-icon mapping table from settings. Returns an ordered list of icon assignments for the Table of Contents navigation row. Pure function.

**18. CampaignRepository**
Owns all PostgreSQL reads and writes for campaigns, sections, products, snapshots, comments, approval events, templates, manual overrides, and preference signals. The only module that touches the database schema directly. Exposes a typed interface to the API layer.

**19. JobQueue**
Wraps ARQ + Redis. Enqueues image processing and banner generation jobs and provides a typed interface for checking job status. Emits progress events consumed by the WebSocket gateway.

**20. WebSocketGateway**
Accepts job progress events from the JobQueue and pushes them to the correct connected React client. Decoupled from business logic — it only routes events.

### Architectural Decisions

- The OpenAI API key is stored as a server-side environment variable. It is never sent to the browser.
- Google Sheets authentication uses a Service Account JSON credential stored in the server environment. Users share their Sheet with the service account email address.
- MJML is compiled exclusively on the FastAPI server. The React frontend never bundles or runs the MJML compiler.
- The React frontend communicates with the MJML renderer via a POST endpoint that returns compiled HTML for the preview iframe.
- The VisualOrchestrator runs as a blocking call immediately after sync completes. It is fast (single GPT-4o call, ~2–4 seconds). The initial email preview renders using the visual brief's tokens before banners are available.
- Banner generation (ArtistAgent) runs asynchronously as an ARQ job after the initial preview renders. The UI shows placeholder banner slots with a "Generating..." indicator and swaps in real assets via WebSocket when ready.
- The AI Chat interface sends natural language messages to GPT-4o with a strict system prompt that enforces JSON command output only. The frontend applies those JSON commands to the campaign data structure and re-renders via the MJML endpoint. The AI never writes HTML directly.
- Manual asset overrides are stored in PostgreSQL as a mapping of (campaign_id, product_id or section_id) → override_url. The MJMLRenderer substitutes overrides before compilation. The ImageStore abstraction means overrides from URL and file upload are stored identically.
- Manual overrides survive Fast Sync. Full Sync clears only unoverridden assets; overridden assets are preserved unless the editor explicitly clears them.
- Preference signals are stored per editor, not per team. The `get_context` method formats signals as a natural-language summary injected into the VisualOrchestrator's system prompt on every new campaign. Preferences only apply at campaign creation time, not mid-session.
- Image quality gate runs before the processing queue. A FAIL result emits a UI prompt and does not enqueue the image for processing. A WARN result enqueues with the upscaling flag set.
- Template records are stored in PostgreSQL. AI-generated templates and designer-saved templates are distinguished by a `source` field but are otherwise identical. The VisualOrchestrator queries the TemplateLibrary as part of its selection logic.
- The ImageStore interface is the only abstraction layer between modules and the storage backend, ensuring the local → S3 migration requires changes in exactly one place.
- Redis serves dual purpose: ARQ job queue and SKU image cache.
- Snapshots are stored as serialised MJML state JSON in PostgreSQL, linked to their campaign. The snapshot sidebar queries this table ordered by creation timestamp.
- Ghost URLs are unauthenticated routes that look up a campaign by a UUID v4 token and render the latest compiled HTML preview. No session is required to view them.
- Brand tokens (colours, fonts), headers, footers, and keyword-to-icon mappings are stored in PostgreSQL and loaded at MJML compile time.
- User authentication uses FastAPI-Users with JWT tokens and bcrypt password hashing. Two roles: editor (full access) and reviewer (read + comment + approve only).
- Deployment targets Railway with four services: React static site, FastAPI application server, PostgreSQL, Redis.

### Schema Decisions

Core entities: User, Campaign, Section, Product, ProcessedImage, ManualOverride, VisualBrief, Template, Snapshot, Comment, ApprovalEvent, GlobalSettings, KeywordMapping, UserPreference.

Campaign status lifecycle: draft → in_review → approved. Status is informational only and does not gate any action.

UserPreference stores (editor_id, signal_type, asset_type, signal_value, campaign_id) tuples. Signal types: explicit_positive, explicit_negative, implicit_accept, implicit_revert.

Template stores (id, name, source, structural_pattern, visual_style_json, created_by, created_at).

ManualOverride stores (campaign_id, target_type, target_id, override_url, created_at). Target type is one of: product_image, hero_banner, offer_strip.

---

## Testing Decisions

### What Makes a Good Test

A good test exercises the observable behaviour of a module through its public interface only. It does not assert on internal state, private methods, or implementation details. It sets up realistic inputs, calls the module, and asserts on the returned output or emitted side effects. Tests should be fast, deterministic, and require no running infrastructure unless they are explicitly integration tests.

### Modules to Test

The following deep modules are highest priority for unit testing because they contain the most complex logic and are fully isolated from infrastructure:

- **PreFlightAuditor** — test all combinations of missing CleverTap tags, oversized HTML, missing UTMs, responsiveness failures, and fully valid HTML. Each case is a pure function call. Test the 102KB boundary exactly.
- **MJMLRenderer** — test that priority assignments produce correct column layouts, that visual brief tokens (colours, fonts) are applied, that ToC rows are generated correctly, that locked sections are preserved verbatim, and that manual overrides are substituted correctly.
- **ResponsivenessValidator** — test with HTML that has known overflow conditions at mobile widths vs HTML that is clean. Pure function.
- **ImageQualityGate** — test with a synthetic sharp image (PASS), a synthetic blurry image (FAIL), and a synthetic small image (WARN). Use OpenCV to generate test inputs programmatically.
- **PriceFormatter** — test regex normalisation across a range of raw price string formats and edge cases (missing currency symbol, decimal variations, negative prices).
- **UTMBuilder** — test concatenation with and without a global prefix, and with empty campaign slugs.
- **IconToCMapper** — test that section titles match correctly against the keyword table, that unmatched titles receive a default icon, and that ordering is preserved.
- **PreferenceMemory.get_context** — test that explicit positive signals appear in the returned summary, that explicit negative signals appear as avoidances, and that an empty preference set returns a neutral context string.
- **SheetReader** — test with mock Sheet API responses to verify column parsing, price formatting delegation, and UTM stitching.

The following modules warrant integration testing with real infrastructure in a test environment:

- **ImageProcessor** — test with a real low-resolution image to verify the upscaling branch is taken, and with a high-resolution image to verify it is skipped.
- **SKUCache** — test cache hit and miss against a real Redis instance. Test that a manual override write is returned on subsequent lookups.
- **CampaignRepository** — test all CRUD operations against a real PostgreSQL test database using isolated transactions that are rolled back after each test. Include ManualOverride and UserPreference CRUD.
- **ManualAssetOverride** — integration test with a real ImageStore (local filesystem adapter) to verify that URL fetch, file upload, and cache write all produce a consistent stored override URL.

### Prior Art

No existing tests are present in the codebase at time of writing. The testing patterns above should establish the conventions for this project.

---

## Out of Scope

- **Zero-Shot Product Recreation:** Generative AI will never be used to fabricate a product image from scratch. The system strictly upscales and processes existing scraped photos to prevent false advertising.
- **Writing back to Google Sheet:** The Sheet remains read-only. The system never modifies it.
- **Hosting the OpenAI API on a per-user basis:** A single bundled API key is used. There is no BYO-key UI.
- **Native CleverTap dynamic audience segmentation:** Liquid conditional logic (personalised segments per recipient) is not supported.
- **Direct CleverTap API push:** v1 exports via clipboard only. API-based template creation in CleverTap is deferred to v2.
- **GPU-accelerated image processing:** The image pipeline runs on a CPU instance. GPU upgrade is a future infrastructure decision.
- **OAuth-based Google login for app authentication:** Users authenticate with username and password only. Google Workspace SSO is deferred.
- **Multi-company or multi-tenant support:** The tool is built for a single company's e-commerce site and brand tokens.
- **Post-send performance analytics:** Open rates, click rates, and CleverTap reporting API integration are deferred. No analytics pipeline is built in v1.
- **Email client compatibility testing:** Rendering validation across Outlook, Apple Mail, and other clients (Litmus-style testing) is out of scope. MJML's cross-client output is relied upon.
- **GPT-4o Vision aesthetic scoring:** AI assessment of image aesthetic quality (lighting, composition, angle) is deferred to v2. Quality gating in v1 uses pixel dimensions and blur detection only.
- **Mid-session preference adjustment:** The AI does not adjust its suggestions in real-time based on actions taken within the current session. Preferences are only applied at the start of a new campaign.

---

## Further Notes

- The `ImageStore` abstraction is the single most important architectural decision for future-proofing. Every other module receives image URLs, never raw bytes or file paths. This guarantees the local → S3 migration is a one-file change.
- The VisualOrchestrator system prompt must be treated as a critical security boundary. It must instruct GPT-4o to output only valid JSON and refuse any instruction from the product data that attempts to override it (prompt injection risk via product names or Section_Title values in the Sheet).
- The VisualOrchestrator's preference injection must be capped in token length. A single editor's preference history could grow large over many campaigns. Summarise to the 10 strongest signals maximum before injection.
- Processing 40 images on CPU at 5–15 seconds each means a full sync can take up to 10 minutes. The WebSocket progress bar is mandatory for the tool to feel usable.
- The Ghost URL token must be a UUID v4, not an incrementing integer, to prevent enumeration of campaign previews by unauthenticated users.
- Reviewer comments store a `section_id` reference so that when the editor restores a snapshot, the UI can indicate which comments apply to the current state and which were made on a now-different version.
- Manual overrides in the chat interface should support two natural language patterns: "replace the hero banner with [URL]" and "replace the image for [product name] with [URL or attachment]". The chat parser must extract target type and target identifier reliably before calling ManualAssetOverride.
- The implicit preference signal from a snapshot revert is the most reliable negative signal available. When an editor reverts to a state before an AI suggestion was applied, that suggestion should be recorded as implicit_revert with high weight.
