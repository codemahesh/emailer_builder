# UX Specifications: Dynamic Email Builder

Generated from `PRD.md` and `TECHNICAL_PRD.md` using the 6-pass PRD-to-UX foundation method.

---

## Table of Contents

1. [Pass 1: Mental Model & User Intent](#pass-1-mental-model--user-intent)
2. [Pass 2: Information Architecture](#pass-2-information-architecture)
3. [Pass 3: Affordances & Action Clarity](#pass-3-affordances--action-clarity)
4. [Pass 4: Cognitive Load & Decision Minimization](#pass-4-cognitive-load--decision-minimization)
5. [Pass 5: State Design & Feedback](#pass-5-state-design--feedback)
6. [Pass 6: Flow Integrity Check](#pass-6-flow-integrity-check)
7. [Visual Specifications](#visual-specifications)

---

## Pass 1: Mental Model & User Intent

**Primary user intent (Editor):** "Turn a Google Sheet of products into a finished, brand-compliant email I can paste into CleverTap — without touching HTML or waiting on a designer."

**Primary user intent (Reviewer):** "Look at this email the way a customer will see it, leave my notes, and approve it."

**Likely misconceptions:**
- *"The AI builds the email; I'm just watching."* — Reality: the editor curates. AI proposes; editor accepts, locks, overrides, or shifts vibe. Without intervention, output is generic.
- *"Editing the preview edits the Sheet."* — Reality: Sheet is read-only source. Inline edits are local overrides; the next Full Sync would wipe non-overridden data.
- *"Locking a section means it's frozen forever."* — Reality: Lock excludes from AI shuffles and theme regen, but Fast Sync still updates Price/UTM inside it.
- *"The chat writes code into my email."* — Reality: chat issues structured JSON commands against pre-approved MJML components. It cannot break layout.
- *"Once I see the preview, the email is done."* — Reality: banners arrive asynchronously; the first preview is a structural placeholder while Artist runs.
- *"Approval blocks export."* — Reality: approval is an audit trail, not a gate. Editor can always export.
- *"My preferences are the team's preferences."* — Reality: per-editor only.
- *"A high-resolution image is always usable."* — Reality: blur detection can FAIL even a 2000px image; resolution alone is not quality.

**UX principles to reinforce/correct:**
1. **Source-of-truth hierarchy must be visible at all times:** Sheet → Sync → AI proposal → Editor override. The user must always know which layer they are touching.
2. **AI is a collaborator, not an author:** Every AI-generated artefact carries a visible "AI" provenance badge with one-click override and one-click revert.
3. **Async work is not failure:** The interface treats "Generating banners" as a normal first-class state, not a loading screen blocking work.
4. **Locks are scoped, not absolute:** The lock icon must communicate *what* it protects against (AI shuffles, theme regen) and *what it permits* (Fast Sync price refresh).
5. **Provenance over polish:** Every asset shows where it came from (AI / Sheet scrape / Manual override / Designer template) so the editor never has to guess what a Vibe Shift will overwrite.

---

## Pass 2: Information Architecture

**All user-visible concepts:**

Auth & identity: Editor account, Reviewer account, Session, Logout
Workspace: Campaign, Campaign dashboard, Campaign status (Draft / In Review / Approved), Last-modified timestamp, Duplicate, Archive
Source data: Google Sheet URL, Sheet columns (Section_Title, SKU, Product_Link, Priority, Price, UTM_Campaign, Button_Name), Sync status, Sync mode (Full / Fast), Failed-row report
Products: SKU, Product name, Product link, Scraped image, Processed image, Price (raw + formatted), UTM (raw + stitched), Button label, Priority (High/Medium/Low), Coming-Soon placeholder
Image quality: Quality verdict (PASS / WARN / FAIL), Blur warning, Resolution warning, Replacement upload (file or URL), Processing progress, Per-SKU progress
Visual brief: Campaign theme name, Layout template name, Colour palette, Product background colour, Font hierarchy, DALL-E prompt (read-only diagnostic)
Templates: AI-generated template, Designer-saved template, Template picker, "Save as Template" action
Assets: Hero banner (3 variants), Offer strip, Per-product image, Section header
Editor canvas: Section, Product card, Table of Contents row, Header, Footer, Lock toggle, Inline-editable text (product name, button label), AI provenance badge, Manual-override badge
Chat: Chat panel, Chat message, Vibe Shift command, Asset replacement command (URL/upload), Layout command, Theme command, Template command, Thumbs-up/down on AI suggestion
Viewport: Desktop (600px) toggle, Mobile (375px) toggle
Version: Snapshot, Snapshot timeline, Restore action
Review: Ghost URL, Inline comment, Comment thread, Mark "In Review", Approve action, Approval audit log
Audit: Pre-flight report, File size readout (KB / 102KB), CleverTap tag check, UTM coverage check, Responsiveness warnings
Export: Compile, Minify, Copy to CleverTap
Global settings: Header template, Footer template, Brand tokens (colours, fonts), Keyword→Icon mapping, Global UTM prefix, OpenAI key (admin only — server-side reference)
Preferences: Personal preference profile, Reset preferences, Preference summary view

**Grouped structure:**

### A. Workspace Shell (always visible)
- Campaign dashboard: Primary
- Campaign name + status + last-modified: Primary
- New / Duplicate / Archive: Primary
- Global Settings link: Secondary
- Account / Logout: Secondary
- Rationale: The shell is where editors land, switch between campaigns, and orient.

### B. Campaign Workspace (split-screen, the dominant surface)

**Left rail — Controls & Chat**
- Sync controls (Full / Fast / status): Primary
- Visual brief summary (theme, palette, template): Primary
- Chat panel with AI: Primary
- Snapshot timeline: Secondary
- Quality warnings tray: Secondary (becomes Primary when populated)
- Pre-flight audit summary: Primary at export time, Secondary otherwise
- Rationale: Everything that *changes* the email lives on the left.

**Right rail — Live Preview**
- Email canvas (sections, products, ToC, header, footer): Primary
- Viewport toggle (Desktop / Mobile): Primary
- Per-section lock toggle: Primary
- AI provenance badges + override/revert: Primary
- Inline-editable product text: Secondary (revealed on hover/click)
- Reviewer comments overlay: Secondary
- Rationale: Everything that *displays* the email lives on the right.

### C. Modal / Drawer surfaces (invoked, not persistent)
- Sheet connection drawer: Primary on first sync, Hidden after
- Quality warning card with replacement upload: Primary when triggered
- Theme picker: Hidden, opened on demand
- Template picker: Hidden, opened on demand
- "Save as Template" dialog: Hidden
- Export drawer (pre-flight + Copy to CleverTap): Primary at export
- Rationale: These are decisive moments, not constant context — modal surfacing prevents the workspace from drowning in chrome.

### D. Global Settings (separate route)
- Headers / Footers editor: Primary
- Brand tokens: Primary
- Keyword → Icon mappings: Secondary
- Global UTM prefix: Secondary
- Rationale: Configuration is rarely edited; a separate route keeps it out of the campaign flow.

### E. Reviewer Surface (Ghost URL, no auth)
- Email preview (Desktop / Mobile toggle): Primary
- Inline comment affordance: Primary
- Approve button: Primary
- Campaign name + last-modified: Secondary
- No editing controls: Hidden by role, not present at all
- Rationale: Reviewers must see *the email*, not the builder. Anything not directly serving review/approve is removed.

### F. Account / Preferences
- Personal preference profile: Secondary
- Reset preferences: Hidden (inside profile)
- Logout: Secondary
- Rationale: Personal settings are infrequent.

---

## Pass 3: Affordances & Action Clarity

| Action | Visual / Interaction Signal |
| --- | --- |
| Connect a Google Sheet | Empty-state CTA on a new campaign: a single conspicuous input field with paste affordance + "Connect" button. Pre-flight check (URL format) before submit. |
| Run Full Sync | Primary button labelled "Full Sync" with a secondary line "Re-scrapes everything". Confirmation dialog warns it will discard non-overridden assets. |
| Run Fast Sync | Adjacent button labelled "Fast Sync" with secondary line "Updates prices & UTMs only". No confirmation needed — non-destructive. |
| See sync progress | Inline progress strip below sync buttons: "27 / 40 products imported · 2 failed". Failed count is clickable → drawer with per-row failures. |
| Identify a failed scrape | Product card shows a "Coming Soon" placeholder image with a yellow corner badge "Scrape failed — replace?" |
| Replace a failed/blurry image | Click the warning badge → quality warning card opens inline with two tabs: Upload file / Paste URL. Drop-zone visual = clearly receptive. |
| Recognise an AI-generated asset | Small "AI" pill badge in the top-right of any AI-produced asset (banner, processed image, strip). Hover reveals "Generated by VisualOrchestrator + ArtistAgent". |
| Override an asset from the canvas | Hover over any image asset reveals a "Replace" pencil icon. Click opens upload-or-URL panel. After override, badge changes to "Manual" with a small "Revert to AI" link. |
| Override an asset via chat | Type or attach in chat: chat parses "replace the hero banner with [URL]" or attached file. Confirmation chip appears in chat: "Replaced hero banner — [Revert]". |
| Edit product text | Click directly on the product name or button label in the preview → inline contenteditable. Save on blur. A small "edited" dot appears next to the field. |
| Lock a section | Padlock icon in the section header. Open padlock = unlocked, closed padlock = locked. Locked section gets a subtle border treatment + tooltip "Locked: AI will not modify. Fast Sync still updates prices." |
| Toggle viewport | Segmented control above the preview: "Desktop · Mobile". Active segment is unmistakable; preview animates width change. |
| Pick a template manually | "Templates" button in left rail opens a grid picker. Each tile shows a thumbnail + label + provenance ("AI" or "Saved by Priya"). Click to apply, "Apply" confirms. |
| Save current as a template | "Save as template" action inside the visual-brief summary panel. Opens a small dialog asking for name only. |
| Pick a theme manually | "Theme" button next to template button. Same picker pattern. Manually selected theme shows a "pinned" indicator that survives Vibe Shift. |
| Issue a Vibe Shift | Type into chat ("make it more urgent") OR click "Vibe Shift" button next to visual brief summary, which prefills a chat suggestion. AI response shows what it will regenerate before doing it. |
| Approve an AI suggestion (preference signal) | Thumbs up / thumbs down icons appear next to each AI-authored card (theme summary, generated banner option, suggested layout). Tap = recorded; subtle confirmation. |
| Restore a snapshot | Snapshot timeline tile. Click → "Preview this version" (non-destructive). "Restore" button confirms; current state is auto-snapshotted before replacement so the restore is itself reversible. |
| Generate a Ghost URL | "Share for review" button. Opens a small panel with the URL + Copy button + "Mark as In Review" toggle. |
| Leave a reviewer comment | Reviewer hovers any section in the Ghost URL preview → "Comment" pin appears. Click drops a pin and opens a text field. |
| Approve as reviewer | Sticky "Approve" button at the bottom of the Ghost URL preview. Confirmation modal "This logs your approval — continue?" |
| Run the pre-flight audit | Automatic on opening the Export drawer. Hard-stop errors are red and disable the export button. Soft warnings are amber and do not. |
| Copy to CleverTap | Primary button in Export drawer. Disabled if any hard-stop error exists. On click: HTML copied, success toast "Copied · 87KB · ready to paste". |
| Adjust personal preferences | Account menu → "My preferences" → list of stored signals with delete-each + a "Reset all" button. |

**Affordance rules:**
- If user sees a **dashed border + drop-zone glyph**, they should assume "I can drop a file here."
- If user sees an **"AI" pill**, they should assume "this came from a model and can be overridden or thumb-rated."
- If user sees a **"Manual" pill**, they should assume "I overrode this; Fast Sync will not touch it; I can revert."
- If user sees a **closed padlock**, they should assume "AI will not modify this section, but prices will still refresh on Fast Sync."
- If user sees a **red banner in the audit panel**, they should assume "I cannot export until I fix this."
- If user sees an **amber banner in the audit panel**, they should assume "I can export, but I should know about this."
- If user sees **fields rendered with inline edit affordance (cursor + subtle hover background)**, they should assume "I can edit this without leaving the preview, and edits override the Sheet locally."
- If user sees a **greyed-out shimmer in a banner slot**, they should assume "this asset is being generated; I can keep working."
- If user sees a **timeline tile with a star/dot**, they should assume "this is the current state; everything above is older."

---

## Pass 4: Cognitive Load & Decision Minimization

**Friction points:**

| Moment | Type | Simplification |
| --- | --- | --- |
| New campaign creation: too many fields up front | Choice | Two-field empty state only: name + Sheet URL. Everything else (theme, template, brand override) deferred until after first sync. |
| Choosing between Full Sync vs Fast Sync the first time | Choice | First sync is *always* Full — Fast Sync button only appears after a successful Full Sync. No decision presented when only one is valid. |
| Editor staring at "Generating banners…" with nothing to do | Waiting | Initial preview renders immediately with palette-driven placeholder banners. Editor can already lock sections, edit text, reorder via chat, run quality fixes. Banner swap is animated and non-disruptive. |
| Deciding which of 3 banner variants to use | Choice | Auto-select variant 1 by default; show variants 2/3 as small thumbnails beside the active banner with "Swap" affordance. No modal. |
| Understanding why an image was flagged | Uncertainty | Quality warning card explains the verdict in one line: "Too blurry to use" or "Below 500×500 — auto-upscaling didn't help." Replacement is the next obvious action. |
| Knowing whether Vibe Shift will overwrite manual work | Uncertainty | Vibe Shift confirmation lists: "Will regenerate: hero banner, palette. Will preserve: 4 locked sections, 2 manual image overrides, pinned theme." User confirms with full information. |
| Picking the right layout template from a long list | Choice | Visual grid with 3 default suggestions surfaced first ("Recommended for this campaign"), then "Browse all". Defaults reduce 90% of cases to one click. |
| Finding the source of an asset to override | Uncertainty | Hover-state on every asset reveals provenance + actions. No need to navigate menus. |
| Knowing if the email is too big | Uncertainty | Live KB readout in the export drawer, plus a passive footer indicator in the workspace once HTML exceeds 90KB ("Approaching 102KB Gmail limit"). |
| Forgetting to add CleverTap tags | Uncertainty | Tags are inserted *automatically* into the standard footer. Pre-flight audit only fails if the editor explicitly removed them. |
| Resolving a reviewer comment thread | Choice | Each comment has Resolve / Reply only. No "Reassign", "Status", or other ceremony. |
| Restoring a snapshot anxiously ("will I lose my current work?") | Uncertainty | Restore auto-snapshots the current state first. Toast: "Snapshot saved · restored to 2:14 PM version." |
| Reviewing a long email on Ghost URL | Waiting | Sticky Approve button at the bottom; sticky viewport toggle at top; comment pins float above content. Reviewer never has to scroll-search for action surfaces. |

**Defaults introduced:**
- **First sync = Full Sync.** Rationale: Fast Sync is meaningless on an empty campaign.
- **Hero banner variant 1 selected automatically.** Rationale: editors rarely need to A/B; surface alternatives without forcing a decision.
- **Initial preview uses palette placeholders.** Rationale: never block the editor on async generation.
- **CleverTap unsubscribe + view-in-browser tags injected into the default footer.** Rationale: the most common compliance failure becomes the default state.
- **Approval is optional.** Rationale: campaigns ship under deadline pressure; process never blocks delivery.
- **Locked-section behaviour: AI ignores layout, Fast Sync updates prices.** Rationale: this matches what editors actually want — frozen design, fresh data.
- **Manual overrides survive Fast Sync.** Rationale: a deliberate replacement is a stronger signal than a Sheet refresh.
- **VisualOrchestrator auto-selects the layout template.** Rationale: editor can override, but the empty-canvas problem is solved by default.
- **Snapshot before destructive action.** Rationale: every restore, Vibe Shift, and Full Sync is implicitly reversible.
- **Per-editor preferences seed VisualOrchestrator on every new campaign.** Rationale: editors don't have to redo preference work each time.

---

## Pass 5: State Design & Feedback

### Element: Campaign Dashboard (list)
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | "No campaigns yet" + single "New Campaign" CTA + 1-line description | "I need to start by creating one." | New Campaign |
| Loading | Skeleton rows | "Loading my work" | Wait (no action) |
| Success | Card per campaign: name, status pill, last-modified, thumbnail | "These are mine, sorted by recency." | Open / Duplicate / Archive / New |
| Partial | Cards plus a yellow banner "1 campaign failed to load — retry" | "Most loaded; one is broken." | Retry / Open the working ones |
| Error | Full-page error with "Retry" + support link | "The dashboard itself is down." | Retry / Logout |

### Element: Sync Operation
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | "Connect a Google Sheet to begin" with URL field | "I haven't synced anything." | Paste URL + Connect |
| Loading | Progress strip "Reading sheet… 12/40 products" with cancel | "It's running; I can see how far." | Cancel |
| Success | Green confirmation "40 products imported · 0 failures · last synced 2 min ago" | "Good to go." | Proceed to layout |
| Partial | Amber strip "37 of 40 imported · 3 failed" + clickable failure list | "Most worked; I need to address 3." | View failures / Replace images / Continue |
| Error | Red banner "Could not access the sheet — check sharing with service account" + steps | "Auth/sharing problem; I know what to fix." | Retry / Open settings |

### Element: Image Quality / Processing
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | No products yet — hidden | n/a | n/a |
| Loading | Per-tile shimmer + progress bar in left rail "Processing 18/40 images" | "Pipeline is running, I can keep editing structure." | Edit text, lock sections, chat |
| Success | All product tiles render the processed (background-removed, centred) image | "All assets are clean and uniform." | Continue |
| Partial | Most tiles render; some tiles show a yellow "Quality issue" badge | "A few products need attention." | Click badge → replace |
| Error | A tile shows red border + "Processing failed — upload a replacement" | "This one is broken; I must replace it manually." | Upload / Paste URL / Retry |

### Element: Visual Brief & Banner Generation
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | Brief panel reads "Awaiting sync" | "Need data first." | Sync |
| Loading | Brief panel populates first (theme, palette, template). Hero banner slot shows shimmer + "Generating 3 options…" | "Brief is ready; banners are coming." | Lock sections, override theme, chat, edit text |
| Success | Hero banner shows variant 1; thumbnails for variants 2 & 3 visible | "Banners ready, I can choose." | Swap variants / Vibe Shift / Override |
| Partial | Brief ready; banners failed → grey block + "Banner generation failed — retry or upload your own" | "AI couldn't render banners; I can supply one." | Retry / Upload |
| Error | Brief itself failed → red banner "Couldn't deduce a theme — try resyncing or set a theme manually" | "Need to intervene." | Retry / Open theme picker |

### Element: AI Chat Panel
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | Greeting + 3 example chips ("Reorder by priority", "Make it more urgent", "Replace hero with…") | "I can talk to it; here's the kind of thing it answers to." | Type / Click chip |
| Loading | User message + AI thinking dots | "It's working." | Wait / Cancel |
| Success | AI response card: human-readable summary + "Apply" / "Discard" buttons + diff preview ("Will reorder Section 2 above Section 1") | "I see what it proposes before it happens." | Apply / Discard / Edit instruction |
| Partial | AI applied some commands; one rejected ("Cannot modify locked section 'Footwear'") | "It respected my locks." | Unlock if intended / Continue |
| Error | "I couldn't parse that — try one of these" + suggestions | "It didn't understand; I have alternatives." | Retype / Click suggestion |

### Element: Live Preview Canvas
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | "Sync a sheet to see your preview" | "Nothing to render yet." | Sync |
| Loading | Skeleton sections matching template structure | "Layout is rendering." | Wait briefly |
| Success | Compiled email at chosen viewport with all assets | "This is what recipients will see." | Edit / Lock / Override / Toggle viewport |
| Partial | Email renders; missing assets show placeholder + "Generating" or "Replace" | "Mostly done; some gaps." | Address gaps |
| Error | Red overlay "Render failed — restore last snapshot?" | "Something broke; I can recover." | Restore snapshot / Reload |

### Element: Snapshot Timeline
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | "Your edits will appear here as snapshots" | "Nothing saved yet." | Make any change |
| Loading | Skeleton list | "Loading history." | Wait |
| Success | Reverse-chronological list of timestamps with summary chip ("Sync", "Vibe Shift", "Locked Footwear") | "I can see what changed and when." | Click any → preview / restore |
| Partial | List with a "Some snapshots unavailable" notice | "Most history is intact." | Use what's there |
| Error | "Couldn't load history — retry" | "History fetch failed." | Retry |

### Element: Pre-Flight Audit (in Export drawer)
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | n/a — audit only runs at export time | n/a | Open export |
| Loading | "Running checks…" with spinner | "Validating compliance." | Wait |
| Success (clean) | All checks green: size, tags, UTMs, responsiveness | "Ready to ship." | Copy to CleverTap |
| Partial (warnings only) | Amber warnings listed; export button still active | "Risky but legal — my call." | Address / Export anyway |
| Error (hard stops) | Red hard-stop list + Export button disabled | "I cannot ship until I fix these." | Fix items / Re-run |

### Element: Reviewer Ghost URL
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | n/a — Ghost URL always loads a preview | n/a | n/a |
| Loading | Skeleton email + viewport toggle | "Email is loading." | Wait |
| Success | Email at chosen viewport + Approve button + comment pins | "I can review and respond." | Toggle viewport / Comment / Approve |
| Partial | Email renders with note "Some assets still generating — refresh in a minute" | "Editor is mid-flow; I can return." | Refresh / Comment on what's there |
| Error | "This preview link is no longer valid" | "Editor revoked or campaign archived." | Contact editor (mailto) |

### Element: Quality Warning Card (per product)
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | n/a — only appears when triggered | n/a | n/a |
| Loading | "Checking image…" | "Quality gate is running." | Wait |
| Success (PASS, hidden) | Card not shown; product tile is clean | n/a | n/a |
| Partial (WARN) | Yellow card "Below 500×500 — upscaled, may look soft" + replace affordance | "It works, but I should consider replacing." | Continue / Replace |
| Error (FAIL) | Red card "Too blurry to use — please replace" + replace affordance is the only way forward for this product | "I must act before export." | Upload / Paste URL / Skip product |

### Element: Manual Override Indicator (per asset)
| State | User Sees | User Understands | User Can Do |
| --- | --- | --- | --- |
| Empty | No badge | "AI/scrape default." | Override if needed |
| Loading | "Uploading…" badge | "My replacement is being saved." | Wait |
| Success | "Manual" pill + small "Revert to AI" link on hover | "This is mine; Fast Sync won't touch it." | Revert / Re-replace |
| Partial | "Manual (URL pending)" if URL fetch is retrying | "Replacement is in flight." | Cancel |
| Error | Red pill "Override failed — file invalid or URL unreachable" | "It didn't take." | Retry / Pick another |

---

## Pass 6: Flow Integrity Check

**Flow risks:**

| Risk | Where | Mitigation |
| --- | --- | --- |
| Editor pastes a Sheet URL not shared with the service account | Initial sync | Pre-flight URL test before kicking off scrape; error state names the service account email and shows a copyable "Share with…" snippet. |
| Editor runs a Vibe Shift and loses 30 minutes of manual asset overrides | Vibe Shift trigger | Confirmation lists exactly what will be regenerated vs preserved; manual overrides and locks are *always* preserved; user must confirm. |
| Editor doesn't realise banners are still generating, exports too early | Export at sync+1 minute | Export drawer surfaces "1 banner still generating — wait or use placeholder" as a soft warning; if a banner slot is the placeholder, that's a soft warning too. |
| Editor edits text in preview, then runs Full Sync, loses edits silently | Full Sync after inline edits | Full Sync confirmation explicitly lists "X inline text edits will be discarded — keep them?" with a "Convert edits to overrides" option. |
| Reviewer leaves comments on a section that the editor then deletes | Snapshot restore or section removal | Comments persist in the thread but display "Made on a previous version" with snapshot link; resolved automatically if section_id no longer exists. |
| Editor locks every section, then issues an AI chat command and is confused why nothing changed | Chat after over-locking | AI response acknowledges constraint: "All sections are locked, so I can't reorder. Unlock 'Apparel' to apply this change?" with a one-click unlock. |
| First-time editor doesn't understand the difference between Full and Fast Sync | Sync UI | First sync forces Full Sync (Fast hidden). Once Fast is exposed, hover tooltip diff: "Full = re-scrape everything · Fast = update prices/UTMs in locked sections." |
| Editor uploads a replacement image that itself fails the quality gate | Manual override path | Replacement is gated through the same ImageQualityGate; FAIL on upload returns the user to the same warning card with the new verdict — no silent acceptance. |
| Editor's preferences quietly steer every campaign toward the same look | New-campaign theme | Visual brief panel shows "Influenced by your preferences" line with a "Use neutral defaults this time" toggle, so editors can opt out per campaign. |
| Reviewer approves on mobile viewport without checking desktop | Ghost URL | "Approve" button asks "You reviewed Mobile — also confirm Desktop?" if the desktop toggle was never engaged this session. |
| Two editors open the same campaign and overwrite each other | Multi-tab / multi-editor | Display a passive "Priya is also editing this campaign" indicator at the top of the workspace; last-write-wins is acceptable for v1, but the editor must *know* it's a risk. |
| 102KB limit hit silently as editor adds sections | Mid-build | Soft floating indicator in workspace shows live size; turns amber at 90KB, red at 100KB. |
| Editor uses chat to "replace hero banner" but ambiguity exists (multiple banners) | Chat command parsing | Chat parser asks back: "I see one hero banner. Replace it with the URL above?" — explicit confirmation when target identifier is ambiguous. |
| Editor expects approval to gate export and is surprised it doesn't | Export | Export drawer always shows approval status as informational ("Approved by Reema · 2:01 PM"); never blocks. Tooltip on the badge clarifies "Approval is for audit, not gating." |

**Visibility decisions:**

**Must be visible at all times in the workspace:**
- Campaign name + status pill
- Sheet connection status + last-synced timestamp
- Sync controls
- Visual brief summary (theme, palette swatch, template name)
- AI/Manual provenance on every asset
- Lock state on every section
- Viewport toggle
- File-size indicator (passive until threshold)
- Chat panel
- Snapshot timeline (collapsed by default)

**Must be visible at decisive moments:**
- Quality warnings (when triggered)
- Vibe Shift confirmation (what regenerates vs preserves)
- Pre-flight audit results (in export drawer)
- Reviewer comments overlay (when present)
- "Banners still generating" notice (only while async work is in flight)

**Can be implied / progressively disclosed:**
- DALL-E prompt text (diagnostic — hidden behind "show prompt")
- Per-snapshot diff details (revealed on hover)
- Failed-row scrape details (drawer behind a count)
- Brand tokens detail (only shown in Global Settings)
- Per-asset provenance hover-detail (revealed on hover, not always visible)
- AI Chat example chips (hidden once the user has sent N messages)
- Reset preferences (inside account → preferences)

**UX constraints (hard rules for the visual phase):**
1. The split-screen ratio must keep the preview readable at the smallest supported screen — preview cannot collapse below 600px effective width on desktop.
2. Every AI-generated artefact must carry an "AI" pill that survives across viewport toggles and snapshot restores.
3. The padlock icon, the AI pill, and the Manual pill use *distinct* shapes/iconography — they must be distinguishable without relying on colour alone (accessibility: protan/deutan).
4. Hard-stop audit errors and soft warnings must use *both* colour and icon (red stop-octagon vs amber warn-triangle) to avoid colour-only signalling.
5. The first preview must render within 4 seconds of sync completion, even if banners are still generating — placeholder banner slots are a feature, not a fallback.
6. Inline text edits, manual overrides, locks, and snapshots must persist across page reloads in the same session — no "you'll lose your work" warnings should ever appear under normal use.
7. The reviewer Ghost URL must NEVER expose any editing affordance — not greyed out, not hidden behind a permission check, but absent from the rendered DOM.
8. The Export drawer must be the *only* surface that triggers `Copy to CleverTap` — the action is consequential enough to warrant its own moment.
9. Chat AI never acts without showing what it will do first ("Apply / Discard" diff preview); silent application is forbidden.
10. The workspace must function on a 1280×800 laptop without horizontal scroll; 1440×900 is the design target.
11. Loading skeletons must reflect final layout structure (not generic shimmer rectangles), so editors can orient before content arrives.
12. Confirmation dialogs are reserved for *destructive* or *expensive* actions only: Full Sync, Vibe Shift, Restore snapshot, Approve. Everything else commits immediately with toast feedback.
13. The chat panel and the manual override panel must accept the same inputs (URL, file upload) and produce the same result — input parity is non-negotiable.
14. Provenance rules: scrape > manual > AI in display priority. If a product has both a scraped image and a manual override, the manual override is shown with "Manual" pill; the scraped image is recoverable via "Revert to scrape" only if no AI processing is involved.

---

# Visual Specifications

Built against the 6-pass foundation. Every visual decision below traces back to a foundation decision — no decoration without rationale.

---

## 1. Design System

### 1.1 Design Principles (visual)

1. **Calm chrome, loud content.** The email preview has its own visual identity (campaign colours, banners, products). The builder chrome must recede so the email reads correctly. Workspace = greyscale + one accent; previews bring the colour.
2. **Provenance through shape, not just colour.** AI / Manual / Scrape / Locked badges are iconographically distinct so they survive colour-blindness and dark mode.
3. **Density tuned for laptops.** Designed for 1440×900 with full functionality at 1280×800. Power-user densities, not marketing-page airiness.
4. **State is a first-class citizen.** Every component has its 5 states (empty/loading/success/partial/error) drawn — not retrofitted.

### 1.2 Colour Tokens

Stored in `theme.json` (per Tech PRD §Design & UX). All values WCAG AA against intended pairings.

**Neutral scale (workspace chrome)**

| Token | Hex | Usage |
| --- | --- | --- |
| `neutral-0` | `#FFFFFF` | Surface base, cards |
| `neutral-50` | `#F8F9FB` | App background, left-rail base |
| `neutral-100` | `#EEF1F5` | Hover, divider, skeleton |
| `neutral-200` | `#DDE3EB` | Borders, inactive separators |
| `neutral-400` | `#8A94A6` | Secondary text, muted icons |
| `neutral-600` | `#4A5567` | Body text |
| `neutral-800` | `#1F2937` | Headings, primary text |
| `neutral-900` | `#0F1623` | Top bar, modal scrim |

**Brand & action**

| Token | Hex | Usage |
| --- | --- | --- |
| `brand-primary` | `#2E5BFF` | Primary buttons, focus rings, active toggles |
| `brand-primary-hover` | `#1E47D9` | Hover state |
| `brand-primary-soft` | `#E8EEFF` | Selected backgrounds, primary tint chips |

**Semantic state**

| Token | Hex | Pair with | Usage |
| --- | --- | --- | --- |
| `success-600` | `#0F8A4A` | `success-50: #E7F6EC` | Sync success, audit pass, Approved |
| `warn-600` | `#C2761B` | `warn-50: #FDF3E2` | WARN quality, soft audit warnings, file size 90–101KB |
| `danger-600` | `#C8281F` | `danger-50: #FCE8E6` | FAIL quality, hard-stop audit errors, file size ≥102KB |
| `info-600` | `#1B6AB0` | `info-50: #E5F1FB` | Informational notices, "still generating" |

**Provenance (always paired with iconography, never colour-only)**

| Token | Hex | Icon | Meaning |
| --- | --- | --- | --- |
| `prov-ai` | `#7B3FE4` | sparkle | AI-generated |
| `prov-manual` | `#0F8A4A` | hand | Manual override |
| `prov-scrape` | `#4A5567` | link | Scraped from source |
| `prov-locked` | `#1F2937` | padlock-closed | Locked section |

### 1.3 Typography

Single sans-serif family, system-stacked for performance.

```
font-stack: "Inter", -apple-system, "Segoe UI", Roboto, sans-serif;
font-stack-mono: "JetBrains Mono", "Cascadia Mono", Menlo, monospace;
```

| Token | Size / Line | Weight | Usage |
| --- | --- | --- | --- |
| `text-display` | 24 / 32 | 600 | Empty-state headlines |
| `text-h1` | 18 / 26 | 600 | Drawer titles, dashboard headers |
| `text-h2` | 15 / 22 | 600 | Section headers in left rail |
| `text-h3` | 13 / 18 | 600 | Card titles, panel labels |
| `text-body` | 14 / 20 | 400 | Default body |
| `text-body-strong` | 14 / 20 | 500 | Emphasis in body |
| `text-small` | 12 / 16 | 400 | Metadata, timestamps, badges |
| `text-micro` | 11 / 14 | 500 | Pill text, status |
| `text-mono` | 12 / 18 | 400 | UTM strings, KB readouts, prompt diagnostics |

### 1.4 Spacing & Radii

4px base grid.

| Token | Value | Usage |
| --- | --- | --- |
| `space-1` | 4px | Icon-to-text gap |
| `space-2` | 8px | Inside pills, tight stacks |
| `space-3` | 12px | Card padding (compact) |
| `space-4` | 16px | Card padding (default), control gutters |
| `space-5` | 24px | Section gaps |
| `space-6` | 32px | Drawer padding |
| `space-7` | 48px | Empty-state breathing room |
| `radius-sm` | 4px | Pills, inputs |
| `radius-md` | 8px | Cards, buttons, panels |
| `radius-lg` | 12px | Drawers, modals |
| `radius-pill` | 999px | Status pills, toggles |

### 1.5 Elevation

Three layers only — anything more becomes noise.

| Token | Shadow | Usage |
| --- | --- | --- |
| `elev-flat` | none + 1px `neutral-200` border | Cards in flow |
| `elev-raised` | `0 2px 6px rgba(15, 22, 35, 0.08)` | Hover, active card |
| `elev-overlay` | `0 16px 48px rgba(15, 22, 35, 0.18)` | Drawers, modals, popovers |

### 1.6 Iconography

16 / 20 / 24px outline icons. Semantic mapping (locked at design-system level so visuals stay consistent across surfaces):

| Icon | Meaning |
| --- | --- |
| sparkle | AI-generated artefact |
| hand | Manual override |
| link | Scraped source |
| padlock-closed / padlock-open | Section lock state |
| eye | Preview / view |
| pencil | Inline edit affordance |
| swap | Variant swap, revert |
| upload | Drop-zone |
| clock | Snapshot |
| comment | Reviewer comment |
| check-shield | Pre-flight pass |
| warn-triangle | Soft warning |
| stop-octagon | Hard stop |

---

## 2. Layout System

### 2.1 Breakpoints

| Name | Width | Behaviour |
| --- | --- | --- |
| `lg` | ≥ 1440px | Design target. Left rail 380px, preview fills remainder. |
| `md` | 1280–1439px | Left rail 340px. All content visible without horizontal scroll. |
| `sm` | 1024–1279px | Left rail collapses to 56px icon strip; expands to 340px on demand (overlay). Reviewer Ghost URL is fully responsive below this. |
| `xs` | < 1024px | **Editor is not supported.** Workspace shows "Builder requires a screen ≥ 1024px wide." Reviewer Ghost URL still works at all widths down to 320px. |

The reviewer surface (Ghost URL) is the only fully responsive product surface. The builder is a desktop tool, by foundation decision (Pass 6, constraint 10).

### 2.2 Global Frame (every authenticated screen)

```
┌────────────────────────────────────────────────────────────────────┐
│  Top Bar — 56px                                                    │
│  [Logo]  Campaigns › Acme Mega Sale     [Status pill]   [Avatar ▾] │
├──────────────┬─────────────────────────────────────────────────────┤
│              │                                                     │
│   Left Rail  │                Main Surface                         │
│   380px      │                (campaign / dashboard / settings)    │
│              │                                                     │
└──────────────┴─────────────────────────────────────────────────────┘
```

**Top bar**
- Background: `neutral-900`, text `neutral-0`.
- Breadcrumb: `Campaigns / [name]` with `›` separators in `neutral-400`.
- Status pill (campaign-scoped routes only): Draft / In Review / Approved.
- Avatar opens menu: My Preferences · Global Settings (admin) · Log out.

---

## 3. Screen Specifications

### 3.1 Login

Single-column, 400px-wide card centred on `neutral-50`.

```
┌──────────────────────────┐
│        [Logo]            │
│   Sign in to Builder     │  ← text-display
│                          │
│   Email                  │  ← text-h3 label
│   [_________________]    │
│   Password               │
│   [_________________]    │
│                          │
│   [    Sign in    ]      │  ← brand-primary, full width
│                          │
│   Forgot password? ·     │
│   text-small, neutral-400│
└──────────────────────────┘
```

States: idle / loading (button → spinner) / error (input border `danger-600`, helper text below).

### 3.2 Campaign Dashboard

Full-bleed grid; left rail collapses to icon strip on this route (no campaign-specific controls).

**Header row** (sticky, 80px)
- Title "My Campaigns" (`text-h1`).
- Right: search input + `[+ New Campaign]` (`brand-primary`).

**Filter row** (40px)
- Status segmented control: All · Draft · In Review · Approved.
- Sort: Last modified ▾.

**Grid**
- 3 columns at `lg`, 2 at `md`, 1 at `sm`.
- Card: 320×240, `radius-md`, `elev-flat`, hover `elev-raised`.

**Card anatomy**
```
┌──────────────────────────┐
│                          │
│   [Email thumbnail]      │  160px tall
│                          │
├──────────────────────────┤
│  Acme Mega Sale          │  text-body-strong
│  [Draft pill]            │  status pill, micro
│  Edited 2h ago · Priya   │  text-small, neutral-400
│                  [⋯]     │  overflow → Duplicate / Archive
└──────────────────────────┘
```

**Status pills**
- Draft: `neutral-100` bg, `neutral-600` text.
- In Review: `warn-50` bg, `warn-600` text, clock icon.
- Approved: `success-50` bg, `success-600` text, check icon.

**Empty state** (no campaigns)
- 480px wide centred block. Illustration (line art, neutral palette). `text-display` headline "Start your first campaign". `text-body` description. `[+ New Campaign]` button.

**Loading**: skeleton cards with shimmer animation (1.4s loop).

### 3.3 New Campaign Modal

Foundation: two-field empty state, defer everything else (Pass 4).

```
┌────────────────────────────────────┐
│  New Campaign                  [×] │
├────────────────────────────────────┤
│                                    │
│  Campaign name                     │
│  [Acme End of Month Mega       ]   │
│                                    │
│  Google Sheet URL                  │
│  [https://docs.google.com/... ]    │
│  ↳ Share with: builder@…           │ ← copyable chip, info-600
│                                    │
│         [Cancel]  [ Connect ]      │
└────────────────────────────────────┘
```

Width 480px. URL field validates on blur; service-account email is copy-on-click. Connect button is disabled until both fields are valid.

### 3.4 Campaign Workspace (the dominant surface)

This is the screen editors live in. Every Pass 1–6 decision converges here.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Top Bar                                                            │
├──────────────────────┬──────────────────────────────────────────────┤
│  LEFT RAIL  380px    │  PREVIEW PANE                                │
│                      │                                              │
│  ┌──────────────────┐│  ┌────────────────────────────────────────┐  │
│  │ Sync             ││  │  [Desktop · Mobile]   [⊕ Share]  [⇪]   │  │
│  │ ● 40/40 · 2 min  ││  ├────────────────────────────────────────┤  │
│  │ [Full] [Fast]    ││  │                                        │  │
│  └──────────────────┘│  │                                        │  │
│  ┌──────────────────┐│  │      EMAIL PREVIEW IFRAME              │  │
│  │ Visual brief     ││  │      (600px or 375px)                  │  │
│  │ "Summer Electric"││  │                                        │  │
│  │ ▦ palette  📐 t. ││  │                                        │  │
│  │ [Vibe shift]     ││  │                                        │  │
│  └──────────────────┘│  │                                        │  │
│  ┌──────────────────┐│  │                                        │  │
│  │ Quality (2) ⚠    ││  │                                        │  │
│  └──────────────────┘│  │                                        │  │
│  ┌──────────────────┐│  │                                        │  │
│  │ CHAT             ││  │                                        │  │
│  │ ...              ││  │                                        │  │
│  │                  ││  │                                        │  │
│  │ [Type a command] ││  │                                        │  │
│  └──────────────────┘│  └────────────────────────────────────────┘  │
│  ┌──────────────────┐│                                              │
│  │ Snapshots ▸      ││  Footer status: 87KB · 12 sections · 40 prod │
│  └──────────────────┘│  Co-editor: Priya is also editing            │
└──────────────────────┴──────────────────────────────────────────────┘
```

**Left rail** (vertical scroll, all panels stacked, `neutral-50` background):
- **Sync panel** — always at top.
- **Visual brief panel** — appears after first sync.
- **Quality warnings panel** — collapsed if 0 issues; expanded with red dot if any FAIL exists.
- **Chat panel** — flexes to fill remaining height; input pinned to bottom.
- **Snapshots panel** — collapsible, defaults to collapsed once history > 3 entries.
- **Pre-flight panel** — appears only when Export drawer opens, replacing Snapshots position.

**Preview pane**:
- Toolbar: Desktop/Mobile segmented control (left), `[⊕ Share for review]` and `[Export ⇪]` (right).
- Canvas background: `neutral-100` so the email's white edges are visible.
- Email iframe centred, 600px wide (Desktop) or 375px wide (Mobile). Animated width transition (250ms).
- Bottom status strip: live size readout (KB), section/product counts, co-editor presence.

### 3.5 Left-Rail Panels — Detail

#### 3.5.1 Sync Panel

```
┌──────────────────────────────────┐
│ SYNC                          ⓘ  │  text-h3
│ ● 40 of 40 imported              │  success-600 dot
│   2 minutes ago · 0 failures     │  text-small neutral-400
│                                  │
│ [ Full Sync ] [ Fast Sync ]      │
└──────────────────────────────────┘
```

- Status dot: success-600 (clean) / warn-600 (partial) / danger-600 (error) / spinner (loading).
- Progress while running: dot replaced by spinner; status line becomes "Reading sheet… 12/40" with a thin progress bar below.
- Failure state: count is clickable, opens drawer listing failed rows with replace-image affordance.
- Fast Sync button is hidden until first Full Sync completes.

#### 3.5.2 Visual Brief Panel

```
┌──────────────────────────────────┐
│ VISUAL BRIEF                ✦ AI │
│                                  │
│ "Summer Electronics Sale"        │  text-body-strong
│                                  │
│ Palette:  ■■■■■                  │  5 swatches, click to inspect
│ Template: Flash Sale (3-tier)    │  link to picker
│ Fonts:    Inter / 28·18·14       │
│                                  │
│ Influenced by your preferences   │  text-small info-600
│ [ Vibe Shift ] [ Override theme ]│
└──────────────────────────────────┘
```

- AI sparkle pill in header denotes provenance.
- "Influenced by your preferences" includes a one-click "Use neutral defaults this time" toggle (foundation Pass 6 risk mitigation).
- Override theme opens the Theme Picker drawer.
- Template name links to Template Picker drawer.

#### 3.5.3 Quality Warnings Panel

Collapsed default state shows count: `Quality (2) ⚠`. Expanded:

```
┌──────────────────────────────────┐
│ QUALITY                          │
│                                  │
│ ⛔ SKU-1042 · Sneaker            │
│    Too blurry to use             │
│    [ Replace ]                   │
│                                  │
│ ⚠ SKU-2218 · Headphones          │
│    Below 500×500 — upscaled      │
│    [ Replace ] [ Keep ]          │
└──────────────────────────────────┘
```

- FAIL items use `danger-600` icon; can't be dismissed without replacement.
- WARN items use `warn-600` icon; "Keep" dismisses for this campaign.
- "Replace" opens the Quality Warning Card inline (described §4.4).

#### 3.5.4 Chat Panel

```
┌──────────────────────────────────┐
│ CHAT                             │
│ ┌──────────────────────────────┐ │
│ │ Priya 14:02                  │ │
│ │ Reorder by priority          │ │
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ ✦ Builder 14:02              │ │
│ │ Will move "Footwear" above   │ │
│ │ "Apparel" — keep "Tech"      │ │
│ │ locked.                      │ │
│ │ [Apply] [Discard]            │ │
│ └──────────────────────────────┘ │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ Try: "make it more urgent"   │ │  example chips, hidden after N msgs
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ Type a command…  [📎] [↑]    │ │
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
```

- User messages: right-aligned, `brand-primary-soft` bubble, `neutral-800` text.
- AI messages: left-aligned, `neutral-0` bubble with 1px `neutral-200` border, AI sparkle in header.
- AI proposal cards always include Apply / Discard buttons + a one-line diff summary (foundation Pass 5).
- File attach (📎) accepts images for asset replacement.
- URL paste in input is auto-detected and offered as "Replace [target]?" inline.
- Input height grows to 4 lines max; then scrolls.

#### 3.5.5 Snapshots Panel

```
┌──────────────────────────────────┐
│ SNAPSHOTS              [Show all]│
│                                  │
│ ● 14:18  Current                 │
│ ○ 14:12  Vibe Shift              │
│ ○ 14:05  Locked Footwear         │
│ ○ 13:48  Full Sync               │
└──────────────────────────────────┘
```

- Current snapshot dot: filled `brand-primary`.
- Older: hollow `neutral-400`.
- Click any → preview overlay (non-destructive). "Restore" button in preview overlay.
- Restore action confirmation: "Snapshot the current state first?" (default yes, per Pass 4 default).

### 3.6 Email Preview Pane — Detail

#### 3.6.1 Section Header (in-canvas)

```
                              ┌─ Section header overlay (on hover) ─┐
                              │ 🔓 Lock · Save as template · ⋯      │
                              └──────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│ FOOTWEAR                                                 │  ← actual email content
│ [icon ToC entry]                                         │
└──────────────────────────────────────────────────────────┘
```

- Hover-only chrome appears 8px above the section, never altering email layout.
- Lock toggle here mirrors the rail's section list.
- Locked sections get a 2px `prov-locked` left edge and a tiny padlock in the upper-left corner (always visible, not just hover).

#### 3.6.2 Asset Hover State

```
┌──────────────────────────┐
│ [✦ AI]            [✏ ⌃]  │  ← provenance pill (top-left), action menu (top-right)
│                          │
│      [PRODUCT IMAGE]     │
│                          │
│  Wireless Headphones     │
│  ₹4,999  [Buy now →]     │
└──────────────────────────┘
```

- Provenance pill always visible: AI / Manual / Scrape.
- Action menu (✏) appears on hover only: Replace · Revert · Inspect.
- Inline-editable text (product name, button label) shows pencil cursor + subtle `neutral-100` highlight on hover; click to edit.
- After inline edit: a tiny edited-dot indicator (4px `info-600` dot) next to the field, with tooltip "Edited locally — Full Sync will revert".

#### 3.6.3 Banner Variant Switcher

When 3 banners are generated:

```
┌──────────────────────────────────────┐
│ [    ACTIVE HERO BANNER    ]         │
│                                      │
│ Variants:  [thumb1*] [thumb2] [thumb3]│  active = brand-primary border
└──────────────────────────────────────┘
```

- Thumbs are 80×40, click to swap into the main slot.
- Each thumb has thumbs-up/down on hover (preference signal capture, Pass 4).
- During generation: thumbs are skeleton boxes; main slot is a palette-driven gradient placeholder so editor isn't blocked.

### 3.7 Drawers (right-side, 480px)

Open over preview pane, dim it 30% with `neutral-900` scrim.

#### 3.7.1 Theme Picker Drawer

- Header: "Choose theme" + close.
- Grid of theme cards (2 cols), each showing a 240×140 preview applying the theme to a sample email module.
- Selected theme has `brand-primary` 2px border + check.
- Footer: `[Cancel] [Apply theme]`.
- After apply: theme pinned indicator appears on Visual Brief panel.

#### 3.7.2 Template Picker Drawer

- Header: "Choose template" + filters (All · AI · Saved).
- "Recommended for this campaign" rail at top (3 cards, foundation Pass 4 default).
- "All templates" grid below.
- Each tile: 240×180 thumbnail, name, source pill (✦ AI / ✋ Saved by [name]).
- Footer: `[Cancel] [Apply template]`.

#### 3.7.3 Export Drawer (Pre-Flight + Copy)

```
┌──────────────────────────────────────┐
│ Export to CleverTap            [×]  │
├──────────────────────────────────────┤
│ PRE-FLIGHT AUDIT                     │
│                                      │
│ ✓  CleverTap tags present            │  success row
│ ✓  All UTMs populated                │
│ ⚠  Size: 99 KB (Gmail limit 102 KB)  │  warn row
│ ⛔ 1 image exceeds container on mobile│  hard-stop row
│    [View issue]                      │
│                                      │
├──────────────────────────────────────┤
│ Approval: ● Approved by Reema · 14:02│  informational, never gates
├──────────────────────────────────────┤
│           [ Copy to CleverTap ]      │  disabled when hard-stops exist
└──────────────────────────────────────┘
```

- Hard-stop rows: `danger-50` background, stop-octagon icon, link to the issue location.
- Soft warnings: `warn-50` background, warn-triangle icon, dismissible link.
- Pass rows: `success-50` background, check icon.
- Button: `brand-primary` enabled / `neutral-200` disabled (with tooltip listing remaining hard-stops).
- After copy: success toast + drawer auto-closes after 2s.

#### 3.7.4 Quality Warning Card (in-canvas overlay)

When user clicks a quality warning:

```
┌──────────────────────────────────────┐
│ Image quality issue              [×] │
│                                      │
│ [thumbnail]   SKU-1042 · Sneaker     │
│               ⛔ Too blurry to use   │
│                                      │
│ ┌─────────────┬─────────────┐        │
│ │  Upload     │   URL       │        │  tabs
│ ├─────────────┴─────────────┤        │
│ │  [drop-zone area]          │        │
│ │   or click to browse       │        │
│ └────────────────────────────┘        │
│                                      │
│ Replacement is checked again         │  reassurance line
│         [Cancel] [Use this image]    │
└──────────────────────────────────────┘
```

- Re-runs through ImageQualityGate on submit (Pass 6 risk mitigation).
- If replacement also fails: card stays open, verdict updates inline.

### 3.8 Reviewer Ghost URL Surface

The only fully responsive product surface. No editing affordances exist in the DOM (Pass 6 constraint 7).

```
┌─────────────────────────────────────────┐
│  Acme Mega Sale · Last updated 14:18    │  sticky top, 48px
│                       [Desktop · Mobile]│
├─────────────────────────────────────────┤
│                                         │
│         [EMAIL PREVIEW]                 │
│                                         │
│         ┌──────────┐                    │
│         │ section  │  ← hover spawns    │
│         └──────────┘     comment pin    │
│                                         │
├─────────────────────────────────────────┤
│ Comments (3)                  [Approve] │  sticky bottom, 64px
└─────────────────────────────────────────┘
```

- Top bar: campaign name + last-modified + viewport toggle. No avatar (anonymous reviewer).
- Comment pins: numbered circles in `info-600`, drop on click, expand to text field.
- Bottom bar:
  - Comments count (left) — clicking opens a slide-up sheet listing all comments, click any to scroll-into-view.
  - Approve button (right, `brand-primary`).
- Approve confirmation: "You've reviewed Mobile only — also confirm Desktop?" if Desktop toggle never engaged this session (Pass 6 risk).
- After approval: button transforms to `[ ✓ Approved at 14:23 ]` (disabled, `success-50` bg).

Mobile (<1024px): comment pins become a "comment" floating action button bottom-right; tapping starts a tap-to-place pin flow.

### 3.9 Global Settings (separate route)

Three-tab page: Headers & Footers · Brand Tokens · Keyword Mappings · UTM Prefix.

Standard form layout, 720px max-width content column. Edit-in-place pattern (no separate edit modes). Save bar (`elev-overlay`) appears at bottom of viewport on any unsaved change.

### 3.10 My Preferences

Account menu → "My Preferences".

```
┌──────────────────────────────────────┐
│ Your preferences                     │
│                                      │
│ The AI biases new campaigns toward:  │
│                                      │
│ ✦ Bold, high-contrast palettes  [×]  │  preference chip with delete
│ ✦ Sans-serif fonts              [×]  │
│ ✦ 2-column product grids        [×]  │
│ ✦ Avoid pastel backgrounds      [×]  │  negative signal, hand-icon variant
│                                      │
│ Last updated 3 days ago              │
│                                      │
│         [Reset all preferences]      │
└──────────────────────────────────────┘
```

- Reset confirmation: "This clears X preferences and starts the AI from neutral defaults. Continue?"

---

## 4. Component Specifications

### 4.1 Button

| Variant | Background | Text | Border | Use |
| --- | --- | --- | --- | --- |
| Primary | `brand-primary` | `neutral-0` | none | Single per surface, decisive action |
| Secondary | `neutral-0` | `neutral-800` | 1px `neutral-200` | Standard actions |
| Ghost | transparent | `brand-primary` | none | Tertiary inline actions |
| Danger | `danger-600` | `neutral-0` | none | Destructive only (confirmation modals) |
| Disabled | `neutral-100` | `neutral-400` | none | Any variant when blocked |

Sizes: small (28h, padding 8/12) · default (36h, 8/16) · large (44h, 12/20). Hover: -hover token. Focus: 2px `brand-primary` ring with 2px `neutral-0` offset.

### 4.2 Pills & Badges

- Provenance pill: 20h, `radius-pill`, icon + 11px label. Background = token-50, text = token-600.
- Status pill: same shape, semantic colour.
- Quality verdict badge: 24h, icon-only, drops a tooltip on hover.

### 4.3 Inputs

- Height 36, `radius-sm`, 1px `neutral-200` border, `neutral-0` bg.
- Focus: border `brand-primary`, 2px ring.
- Error: border `danger-600`, helper text `danger-600` 12px below.
- Disabled: bg `neutral-100`, text `neutral-400`.

### 4.4 Toast

- Position: bottom-centre, 24px from edge. Stack upward. Auto-dismiss 4s (success), 6s (warn), sticky until dismissed (error).
- 320px wide, `elev-overlay`, `radius-md`, icon + message + close.
- Toast types match semantic palette.

### 4.5 Skeleton Loader

- Background `neutral-100`, shimmer overlay `neutral-50` to `neutral-0` at 1.4s.
- Skeletons reflect final layout structure, not generic rectangles (Pass 6 constraint 11).

### 4.6 Tooltip

- Background `neutral-900`, text `neutral-0`, 12px, `radius-sm`.
- 8px from anchor, arrow optional. Show after 400ms hover.

### 4.7 Modal vs Drawer

- **Modal** (centred, scrim): irreversible decisions, short forms (New Campaign, Restore confirmation, Approve confirmation).
- **Drawer** (right-side, scrim): browse-and-pick, longer flows (Theme picker, Template picker, Export, Failed rows list).

---

## 5. Interaction Specifications

### 5.1 Animation Tokens

| Token | Duration | Easing | Use |
| --- | --- | --- | --- |
| `motion-instant` | 80ms | `ease-out` | State flips (toggle, check) |
| `motion-quick` | 160ms | `ease-out` | Hover, tooltip |
| `motion-default` | 240ms | `cubic-bezier(0.2, 0.8, 0.2, 1)` | Drawer, modal, viewport toggle |
| `motion-slow` | 400ms | `ease-in-out` | Banner swap-in, snapshot restore |
| `motion-shimmer` | 1400ms loop | linear | Skeletons |

### 5.2 Hover & Focus

- All interactive surfaces have hover and focus states.
- Keyboard focus is always visible (2px `brand-primary` ring, never `outline: none`).
- Tab order follows visual order: top bar → left rail (top to bottom) → preview toolbar → preview content → footer.

### 5.3 Critical Interaction Flows

**Vibe Shift confirmation flow** (Pass 6 risk mitigation)
1. User triggers Vibe Shift (button or chat).
2. Modal opens with two columns:
   - "Will regenerate" (icons of affected items).
   - "Will preserve" (locked sections, manual overrides, pinned theme).
3. Buttons: `[Cancel]` `[Regenerate]`.
4. On regenerate: snapshot auto-created → loading state → assets swap in.

**Full Sync confirmation flow**
1. User clicks Full Sync.
2. Modal: "This re-scrapes everything and discards: [count] inline text edits."
3. Option: `☑ Convert text edits to overrides instead` (preselected if any edits exist).
4. Buttons: `[Cancel]` `[Run Full Sync]`.

**Banner swap-in animation**
- Placeholder fades out (160ms) while real banner fades in (240ms) with 80ms overlap.
- Tiny "✦ generated" toast appears bottom-right of preview for 3s.

**Snapshot restore flow**
1. Click snapshot tile → preview overlay (full preview pane is replaced by snapshot rendering, with a yellow ribbon "Previewing 14:12 — read only").
2. `[Exit preview]` `[Restore this version]`.
3. On restore: confirmation toast, snapshot timeline updates with current state captured first.

### 5.4 Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| `⌘/Ctrl + K` | Focus chat input |
| `⌘/Ctrl + S` | Force snapshot |
| `⌘/Ctrl + E` | Open Export drawer |
| `⌘/Ctrl + ⇧ + L` | Lock/unlock current section (when section focused) |
| `D` / `M` | Toggle Desktop / Mobile viewport |
| `Esc` | Close drawer/modal/exit snapshot preview |
| `↑` / `↓` in chat | Cycle through previous user messages |

Shortcut hints surface in tooltips and a `?` overlay (Shift+/).

### 5.5 Live Indicators

- **Co-editor presence**: footer strip "Priya is also editing" with 16px avatar; passive only, no merge conflict UI in v1 (Pass 6 risk #11, last-write-wins).
- **File size readout**: live update on every render. Default `neutral-400`, becomes `warn-600` at ≥90KB, `danger-600` at ≥100KB.
- **Generation status pill** in preview toolbar: "✦ Generating 2 banners…" with spinner, dismisses when complete.

---

## 6. Accessibility

- All colour pairings tested at WCAG AA minimum (4.5:1 body, 3:1 large text/icons).
- Provenance, lock, and audit signals never rely on colour alone (Pass 6 constraint 3, 4) — paired with iconography.
- Focus rings always visible.
- All icons have aria-labels; all interactive icons have descriptive titles.
- Skeleton loaders are `aria-busy="true"` on their container.
- Toasts use `role="status"` (success/info) or `role="alert"` (error).
- Keyboard parity: every mouse interaction has a keyboard equivalent. Inline-edit affordances are `contenteditable` with `Enter` to save / `Esc` to cancel.
- Reviewer Ghost URL: comments are reachable via skip-link "Jump to comments".

---

## 7. Component-to-Foundation Traceability

A spot-check that every visual decision is anchored. Sample mapping:

| Visual decision | Foundation source |
| --- | --- |
| Provenance pills always visible on assets | Pass 1 (mental model #2), Pass 3 (affordance rules) |
| Lock icon = closed/open shapes, not colour | Pass 1 (#4), Pass 6 (constraint 3) |
| First-sync hides Fast Sync button | Pass 4 (default), Pass 6 (risk #7) |
| Banner placeholder during generation | Pass 5 (Visual Brief loading), Pass 6 (constraint 5) |
| Export drawer is the only Copy-to-CleverTap surface | Pass 6 (constraint 8) |
| Approval pill is informational, never gates | Pass 1 (mental model misconception), Pass 6 (risk #14) |
| Vibe Shift modal lists "preserve" column | Pass 6 (risk #2) |
| Reviewer surface has no edit affordances in DOM | Pass 6 (constraint 7) |
| File-size indicator goes amber at 90KB | Pass 4 (uncertainty mitigation), Pass 6 (risk #12) |
| Builder requires ≥1024px | Pass 6 (constraint 10) |
| Inline-edit shows "edited" dot | Pass 1 (misconception #2), Pass 6 (risk #4) |

---

## 8. Handoff Notes

- **Iconography**: bundle a single icon set (suggest Phosphor or Lucide). Provenance icons must be visually distinct shapes.
- **theme.json**: ship the colour, type, spacing, radius, and elevation tokens as a single file consumed by both the React app and the MJML compiler (the latter for brand-token injection per Tech PRD §246).
- **Empty-state illustrations**: keep flat line-art in `neutral-400` only — no chromatic illustrations that would compete with the email preview's colour content.
- **Preview iframe**: enforce a fixed device-frame chrome (subtle 1px `neutral-200` border, no skeuomorphic device shells) so the focus stays on email content.
- **No dark mode in v1**: the email previews are predominantly light-on-light, and dual-theming the chrome creates contrast inconsistencies against preview iframes. Defer to v2.

---

*End of UX Specifications.*
