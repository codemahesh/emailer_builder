# Product Requirements Document (PRD): Dynamic Email Builder

## Executive Summary

The Dynamic Email Builder is an internal, web-based orchestration platform designed to empower non-technical marketing managers and designers to generate high-conversion, CleverTap-ready e-commerce emails in minutes. By utilizing Google Sheets as a single source of truth and a Multi-Agent AI system, the tool automates layout generation, image enhancement, banner creation, and HTML coding. It ensures 100% reliable image delivery via proxy hosting and guarantees compliance with Gmail’s 102KB size limit and CleverTap’s platform requirements.

## Problem Statement

Creating complex, multi-section promotional emails (e.g., "End of Month Mega Offers") is a heavily manual bottleneck. Designers spend hours copying product details, formatting prices, building responsive HTML grids, and writing UTM tags. Furthermore, relying on raw scraped images leads to broken links due to vendor hotlink protection, and low-resolution images degrade brand quality. Manually coded HTML often suffers from "code bloat," resulting in emails being clipped by Gmail or failing CleverTap syntax validation.

## Goals & Objectives

- **Speed (Time-to-Value):** Reduce campaign creation time from 4+ hours to under 15 minutes.
- **Asset Automation:** Eliminate the need for external graphics teams by using AI to upscale product images and auto-generate thematic banners.
- **Reliability & Compliance:** Guarantee 0% broken images, 100% CleverTap compatibility (Unsubscribe tags), and strict adherence to Gmail’s <102KB size limit.
- **No-Code Empowerment:** Allow users to build, modify, and lock complex email grids using natural language chat and a simple spreadsheet.

## User Personas

1.  **The Marketing Manager / Designer (Primary):** Needs to rapidly compile product lists, assign visual priorities, and generate a brand-compliant email without writing HTML or engineering AI prompts.
2.  **The Approving Manager (Stakeholder):** Needs a frictionless, accessible way to view the final email layout on mobile and desktop before approving the campaign deployment.

---

## User Stories & Requirements

### Epic 1: Data Integration & Global Management

**As a Marketing Manager, I want to connect a Google Sheet to the builder, so that product data is automatically imported without manual entry.**

- **Acceptance Criteria:**
  - System reads standard columns: `Section_Title`, `SKU`, `Product_Link`, `Priority` (High/Medium/Low), `Price`, `UTM_Campaign`, `Button_Name`.
  - System runs a Regex filter to format all scraped prices to the standard localized currency format.
  - System automatically stiches the Sheet's `UTM_Campaign` with a Global UTM Prefix defined in app settings.
  - System supports a "Full Sync" (re-scrapes everything) and a "Fast-Sync" (updates Prices and UTMs only for locked layouts).

**As a User, I want to manage headers and footers globally, so I don't have to rebuild them for every email.**

- **Acceptance Criteria:**
  - App contains a Global Settings tab for standard Headers, Footers, and Keyword tag clouds.
  - Changes made here propagate to all newly generated emails.

### Epic 2: Multi-Agent Asset Processing & Generation

**As a System, I want the Email Architect Agent to automatically deduce the campaign theme, so that the user does not have to learn prompt engineering.**

- **Acceptance Criteria:**
  - Agent 1 (Architect) scans the Sheet's `Section_Title` and product names to deduce an overarching theme (e.g., "Summer Electronics Sale").
  - Agent 1 constructs an optimized text-to-image prompt, integrating the theme and brand Hex colors, and sends it to Agent 3 (Artist).

**As a System, I want the Retoucher Agent to process scraped images, so that all products look uniform and high-quality without hallucinating fake product details.**

- **Acceptance Criteria:**
  - Agent 2 (Retoucher) evaluates scraped image resolution. If below 500x500px, it applies AI Super-Resolution (upscaling) to enhance quality while preserving exact SKU authenticity.
  - Agent 2 removes the original background and auto-crops the product dead-center with 10% padding.
  - Agent 2 applies a thematic background or brand color behind the isolated product.
  - Processed images are permanently hosted on an owned S3/Cloudinary bucket. A SKU-to-CDN cache prevents re-scraping existing products.

**As a Designer, I want the Artist Agent to automatically deliver ready-to-use Hero Banners and Offer Strips, so that the email feels cohesive instantly.**

- **Acceptance Criteria:**
  - Agent 3 (Artist) receives the prompt from Agent 1 and generates 3 distinct visual options for the Hero Banner and corresponding Offer Strips.
  - User can click a "Vibe Shift" button (e.g., "Make it more urgent") to force Agent 1 to rewrite the prompt and Agent 3 to rerender assets.

### Epic 3: Dynamic Template Generation (MJML)

**As a Designer, I want the system to auto-generate a responsive grid based on product priority, so the email looks visually appealing.**

- **Acceptance Criteria:**
  - High Priority = 1-column full-width Hero block; Medium = 2-column block; Low = 3-column block.
  - System groups products into MJML `<mj-section>` blocks based on the `Section_Title`.

**As a User, I want an automated Table of Contents (ToC), so that customers can easily navigate long emails.**

- **Acceptance Criteria:**
  - System generates an Icon-based Navigation Row at the top of the email.
  - Icons map automatically to the `Section_Title` via a pre-loaded Keyword Mapping Library (e.g., "Footwear" = Sneaker Icon).

### Epic 4: The AI Builder & Chat Interface

**As a Designer, I want to modify the email layout using natural language chat, so that I don't have to edit code.**

- **Acceptance Criteria:**
  - User can provide their own LLM API Key (OpenAI/Anthropic) to power the Chat.
  - AI outputs strictly JSON/MJML section commands to reorder sections or apply design tokens.
  - UI features a "Ghost Rendering" debounced live preview (1-2s loading spinner) to show changes in real-time.

**As a Designer, I want to "Lock" specific sections, so that the AI does not overwrite layouts I am already happy with.**

- **Acceptance Criteria:**
  - Every generated section features a "Padlock" UI toggle.
  - Locked sections are strictly ignored by the AI during global shuffles or theme regenerations.

### Epic 5: Export, Approval & Handoff

**As a Designer, I want a Shareable Link to send to my manager, so that I can get approval without exporting files.**

- **Acceptance Criteria:**
  - System generates a "Permanent Campaign Link" (Ghost URL) hosting the latest preview of the email for stakeholder viewing.

**As a User, I need to export the final code directly to CleverTap, so that it is ready to send.**

- **Acceptance Criteria:**
  - "Copy to CleverTap" button compiles MJML to standard HTML and automatically minifies it.
  - Pre-Flight Audit runs automatically:
    - **Hard Stop:** Disables download if CleverTap tags (`{{unsubscribe_link}}`, `{{view_in_browser}}`) are missing.
    - **Soft Warning:** Alerts the user if the minified HTML exceeds 102KB or if UTMs are missing.

---

## Success Metrics (AARRR/HEART)

- **Efficiency (Task Success):** Decrease average email build time from 4 hours to under 15 minutes.
- **Performance:** 100% of exported HTML files remain below the 102KB Gmail clipping threshold.
- **Quality:** 0% broken image links in deployed campaigns (measured via CleverTap error logs).
- **Adoption:** 90%+ of internal marketing campaigns utilize the builder within 3 months of rollout.

---

## Scope

**In-Scope:**

- Google Sheets API Integration (Read-only).
- Multi-Agent Architecture (Architect, Retoucher, Artist).
- AI image upscaling, background removal, and zero-prompt banner generation.
- S3/Cloudinary proxy hosting and SKU caching.
- BYO-Model (Bring Your Own Model) AI Chat wrapper.
- Icon-based automated Table of Contents.
- Pre-flight CleverTap compliance checker.

**Out-of-Scope:**

- Zero-Shot Product Recreation (The system will _never_ use Generative AI to draw a product from scratch; it will strictly upscale existing photos to prevent false advertising).
- Writing data back to the Google Sheet (Sheet remains the single source of truth).
- Hosting the Chat LLM API on our backend (Users supply their own keys).
- Native CleverTap dynamic audience segmentation (Liquid conditional logic).

---

## Technical Considerations

- **Architecture:** Frontend-heavy application (React/Vue) utilizing an MJML-in-browser compiler and an async task queue for the Multi-Agent orchestration.
- **Security:** LLM API Keys are saved strictly in Browser Local Storage. No central database of API keys exists.
- **Agent 1 Prompting Constraints:** The Email Architect requires an iron-clad System Prompt wrapper to prevent it from outputting raw HTML instead of the expected JSON/MJML array structure.
- **Image Processing Limits:** Processing 40+ images via the Retoucher Agent will be resource-intensive. Background asynchronous processing with WebSocket progress updates to the UI is mandatory.

---

## Design & UX Requirements

- **Workspace:** Side-by-side split screen. Chat/Controls on the left, Live Preview on the right.
- **Viewport Testing:** A simple Desktop/Mobile toggle above the preview window.
- **Version Control:** A "Snapshot Sidebar" displaying a timeline of changes, allowing users to click timestamps to revert to previous MJML states.
- **Brand Alignment:** Application must enforce company-specific design tokens (e.g., Primary Brand Color, Secondary Brand Color, Font Families) via a central `theme.json`.

---

## Timeline & Milestones

- **Phase 1: Foundation & Data** (Weeks 1-3) - Google Sheets API, S3 Proxy setup, SKU Caching, and basic MJML compiler engine.
- **Phase 2: The Multi-Agent Pipeline** (Weeks 4-6) - Integrate the Retoucher Agent (Upscaling/Bg Removal) and Artist Agent (Banner generation), build the async queue.
- **Phase 3: The AI Chat & UI** (Weeks 7-8) - BYO-Model integration, split-screen UI, Section Locking, Icon ToC, and Architect Agent logic (zero-prompting).
- **Phase 4: Handoff & Launch** (Week 9) - Pre-Flight Audit checks, Minifier, Ghost URL generation, and internal User Acceptance Testing.

---

## Risks & Mitigation

- **Risk:** Target website blocks the scraper (Anti-Bot restrictions).
  - _Mitigation:_ Use rotating proxies for scraping. If completely blocked, inject a "Coming Soon" category image and flag it in the UI for the user to manually upload.
- **Risk:** AI Chat model "hallucinates" and breaks the layout code.
  - _Mitigation:_ The AI never writes raw code directly to the canvas; it outputs JSON commands that the internal app engine translates into pre-approved, immutable MJML components.
- **Risk:** Image processing APIs timeout on large product sets.
  - _Mitigation:_ Decouple image processing from the UI thread. Use background workers and implement the "Fast-Sync" option for subsequent edits to avoid re-running the heavy image pipeline.
