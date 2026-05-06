name description
prd-ui-prototype
Generate interactive UI prototypes from PRD using frontend-design principles. Creates distinctive, production-grade HTML/CSS/JS prototypes with bold aesthetic choices.
User Input
$ARGUMENTS
You MUST consider the user input before proceeding (if not empty).

Goal
Generate interactive visual UI prototypes from a PRD using the frontend-design skill's principles. Extract context from the PRD, ask targeted questions about components and design preferences, then produce production-quality HTML prototypes with distinctive, context-specific aesthetics.

Design Methodology: This skill applies the exact design thinking and aesthetics guidelines from the frontend-design skill (claude-plugins-official/frontend-design) to create distinctive, production-grade interfaces that avoid generic AI aesthetics.

Execution Steps

1. Resolve PRD Path
   If $ARGUMENTS is empty, abort with: "Please provide a path to a PRD file. Example: /prd-ui-prototype prd/my-feature/prd.md"
   Validate the path exists and is a markdown file
   Extract the feature name from the path (e.g., prd/user-auth/prd.md → user-auth)
2. Read PRD Context
   Read the PRD file using the Read tool and extract:

User Stories — List of personas and their goals
Functional Requirements — Features and capabilities to implement
User Flows — Step-by-step interaction sequences
Design Guidelines — Visual direction, branding, accessibility requirements
Platform/Technology — Web, mobile, desktop, framework constraints
Create an internal summary of:

Key components mentioned (forms, modals, dashboards, navigation, etc.)
Target platforms (web, mobile-web, native mobile, desktop)
Existing design constraints or brand guidelines 3. Interactive Discovery
IMPORTANT: Before asking questions, first check for existing prototypes and read previous design choices (this is Step 3.5-3.7 in execution order, but conceptually happens before asking questions).

Use AskUserQuestion to gather UI-specific requirements.

Question 1: Component Scope

Header: "Scope"
Question: "Which components do you want to prototype?"
Multi-select: false
Options:
"All major components identified in PRD (Recommended)" (description: "Generate prototypes for all key UI components mentioned in the PRD")
"Let me select specific components" (description: "Choose which components to prototype from a list")
"Custom component list" (description: "I'll provide a custom list of components")
Question 1b: Select Specific Components (Conditional) Only asked if user selects "Let me select specific components" in Question 1.

Header: "Components"
Question: "Which components should be prototyped? (select all that apply)"
Multi-select: true
Options:
Dynamically extract from PRD (look for: login form, dashboard, settings panel, navigation bar, user profile, etc.)
IMPORTANT: Maximum 4 options per question
If PRD has ≤4 components: Present all in a single multi-select question
If PRD has 5-8 components: Split into two questions:
Question 1b: "Primary Components" (first 4 components)
Question 1c: "Additional Components" (remaining components)
If PRD has >8 components: Prioritize top 4 by:
Frequency in user stories
P0 functional requirements
Core user flows
Then ask if user wants to see more components
If user selects "Custom component list" in Question 1, ask a follow-up text question for the component list.

Question 2: Fidelity Level

Header: "Fidelity"
Question: "What level of fidelity do you want for these prototypes? {PREVIOUS_CHOICE_SUFFIX}"
Multi-select: false
Options:
"Low fidelity - Wireframes" (description: "Basic layout and structure, minimal styling, grayscale")
"Medium fidelity - Styled mockups (Recommended)" (description: "Full color, typography, spacing - looks polished but not fully interactive")
"High fidelity - Production-ready" (description: "Pixel-perfect, fully styled, ready to integrate into codebase")
{PREVIOUS_CHOICE_SUFFIX}: If previous fidelity was detected from design-spec.md, append to question: "(Previous: {fidelity})"

Question 3: Aesthetic Direction (Primary Options)

Header: "Aesthetic"
Question: "What aesthetic direction should the prototypes follow? {PREVIOUS_CHOICE_SUFFIX}"
Multi-select: false
Options:
"Let designer decide based on PRD context (Recommended)" (description: "frontend-design skill will choose an appropriate aesthetic")
"Minimal & refined" (description: "Clean, spacious, elegant, restrained color palette")
"Bold & maximalist" (description: "Vibrant colors, strong typography, rich visuals")
"Show more aesthetic options..." (description: "View additional aesthetic directions")
{PREVIOUS_CHOICE_SUFFIX}: If previous aesthetic was detected from design-spec.md, append to question: "(Previous: {aesthetic})"

Question 3b: Extended Aesthetic Options (Conditional) Only asked if user selects "Show more aesthetic options..." in Question 3.

Header: "Aesthetic"
Question: "Choose an aesthetic direction:"
Multi-select: false
Options:
"Professional/corporate" (description: "Trust-building, conventional, accessible")
"Retro-futuristic" (description: "Nostalgic tech aesthetics with modern execution")
"Go back to main options" (description: "Return to the primary aesthetic choices")
If user selects "Go back to main options", re-present Question 3.

Question 4: Interactivity

Header: "Interactivity"
Question: "What level of interactivity should the prototypes include? {PREVIOUS_CHOICE_SUFFIX}"
Multi-select: false
Options:
"Basic interactions (Recommended)" (description: "Hover states, click feedback, basic animations")
"Static HTML only" (description: "No JavaScript, pure CSS for faster loading")
"Full interactivity" (description: "Forms, state management, animations, micro-interactions")
{PREVIOUS_CHOICE_SUFFIX}: If previous interactivity was detected from design-spec.md, append to question: "(Previous: {interactivity})"

3.5. Check for Existing Prototypes
Before creating new prototypes, check if prototypes already exist:

Construct prototype directory path: prd/<feature-name>/prototype-ui/
Check for existing HTML files using Glob tool:
Glob with pattern="\*.html" path="prd/<feature-name>/prototype-ui/"
If HTML files found:
Count the number of prototype components
Check if design-spec.md exists in the same directory
Store the existing prototype directory path for potential backup
Present warning to user via AskUserQuestion:
Overwrite Warning Question:

Header: "Existing prototypes"
Question: "This PRD already has [N] prototype component(s). What would you like to do?"
Multi-select: false
Options:
"Create timestamped backup and generate fresh (Recommended)" (description: "Moves prototype-ui/ to prototype-ui-backup-YYYYMMDD-HHMMSS/, then generates new prototypes. Safe and preserves history.")
"Cancel - keep existing prototypes" (description: "Stop here without making changes. You can manually rename or delete the folder if needed.")
Handle user choice:
If "Cancel" selected: Exit gracefully with message: "Prototype generation cancelled. Existing prototypes preserved at prd/<feature-name>/prototype-ui/"
If "Create backup" selected: Proceed to Step 3.6
If no existing prototypes found: Skip to Step 3.7 (Read Previous Design Choices)
3.6. Create Timestamped Backup (Conditional)
Only runs if user selected "Create timestamped backup" in Step 3.5

Generate timestamp: Use format YYYYMMDD-HHMMSS (e.g., 20260213-143022)
Construct backup path: prd/<feature-name>/prototype-ui-backup-<timestamp>/
Move existing directory using Bash tool:
mv "prd/<feature-name>/prototype-ui" "prd/<feature-name>/prototype-ui-backup-<timestamp>"
Store backup path for use in final report (Step 8)
Confirm success: Verify the move completed without errors
Proceed to Step 3.7
3.7. Read Previous Design Choices (Optional)
Attempt to preserve design choices from previous prototypes

Check for design-spec.md in either:

Backup directory (if backup was just created in Step 3.6)
Current prototype-ui directory (if it wasn't backed up but was detected)
If design-spec.md found, read it and extract:

Aesthetic direction — Look for "Aesthetic:" under "## Design Direction"
Fidelity level — Look for "Fidelity:" under "## Design Direction"
Interactivity level — Look for "Interactivity:" under "## Design Direction"
Parse the values:

Aesthetic examples:
From Question 3 (Primary): "let-designer-decide", "minimal-refined", "bold-maximalist"
From Question 3b (Extended): "professional-corporate", "retro-futuristic"
Fidelity examples: "low", "medium", "high"
Interactivity examples: "static", "basic-interactions", "full-interactivity"
Components (if stored): Array of component names (e.g., ["login-form", "dashboard", "user-profile"])
Store parsed values to pre-fill the questions in Step 3 (Interactive Discovery)

Pre-fill logic for multi-question flow:

If previous aesthetic is from extended set ("professional-corporate", "retro-futuristic"):
In Question 3: Auto-select "Show more aesthetic options..."
Automatically navigate to Question 3b with the previous choice selected
Display in Question 3b suffix: "(Previous: {aesthetic})"
If previous aesthetic is from primary set ("let-designer-decide", "minimal-refined", "bold-maximalist"):
Pre-select in Question 3 directly
Display in Question 3 suffix: "(Previous: {aesthetic})"
If no previous aesthetic found: Use default suffix without "(Previous: ...)"
Important: If design-spec.md doesn't exist or is malformed, gracefully skip this step and proceed with fresh questions.

Note: This step conceptually happens before asking the user questions in Step 3, so the implementation should check for existing prototypes and read design choices before presenting the AskUserQuestion in Step 3. The step numbering reflects execution order.

4. Create Output Directory
   Derive output path: prd/<feature-name>/prototype-ui/
   Create the directory if it doesn't exist using Write tool (write a placeholder file if needed, then remove it)
5. Generate Prototypes Using Frontend-Design Principles
   For each selected component:

Apply the frontend-design skill methodology:

Design Thinking
Before coding, understand the context and commit to a BOLD aesthetic direction:

Purpose: What problem does this interface solve? Who uses it?
Tone: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
Constraints: Technical requirements (framework, performance, accessibility).
Differentiation: What makes this UNFORGETTABLE? What's the one thing someone will remember?
CRITICAL: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:

Production-grade and functional
Visually striking and memorable
Cohesive with a clear aesthetic point-of-view
Meticulously refined in every detail
Frontend Aesthetics Guidelines
Focus on:

Typography: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
Color & Theme: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
Motion: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise.
Spatial Composition: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
Backgrounds & Visual Details: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays.
NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

IMPORTANT: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Remember: Claude is capable of extraordinary creative work. Don't hold back, show what can truly be created when thinking outside the box and committing fully to a distinctive vision.

Implementation
Apply these principles to create production-quality HTML/CSS/JS code:

Honor the fidelity level (low/medium/high) from user discovery
Implement interactivity level (static/basic/full) from user discovery
Respect aesthetic direction from user discovery or PRD context
Save to prd/<feature-name>/prototype-ui/<component-name>.html (kebab-case)
Include proper DOCTYPE, meta tags, accessibility attributes, semantic HTML
Each file should be complete and standalone with embedded CSS and JavaScript
After each component, provide progress feedback: "✓ Generated prototype for "

6. Generate Design Specification
   Create a markdown file documenting the design decisions:

Path: prd/<feature-name>/prototype-ui/design-spec.md

Content structure:

# Design Specification — <Feature Name>

**Generated:** <date>
**Source PRD:** `<path-to-prd>`

## Overview

<1-2 sentence summary of the prototype set>

## Components

### <Component 1 Name>

- **File:** `<component-1>.html`
- **Purpose:** <from PRD>
- **User Flow:** <from PRD>
- **Key Features:** <bullet list>

### <Component 2 Name>

...

## Design Direction

**Aesthetic:** <chosen aesthetic>
**Fidelity:** <chosen fidelity level>
**Interactivity:** <chosen interactivity level>
**Components:** <list of component names>

**IMPORTANT**: Store the actual aesthetic selected by the user, not meta-options:

- Valid aesthetic values: "let-designer-decide", "minimal-refined", "bold-maximalist", "professional-corporate", "retro-futuristic"
- Do NOT store: "show-more-aesthetic-options" or "go-back-to-main-options"
- Valid fidelity values: "low", "medium", "high"
- Valid interactivity values: "static", "basic-interactions", "full-interactivity"
- Components should be stored as a comma-separated list (e.g., "login-form, dashboard, user-profile")

## Rationale

<Brief explanation of why this aesthetic/fidelity combination was chosen based on PRD context>

## Technical Notes

<Any framework constraints, browser requirements, accessibility features>

## Next Steps

- Review prototypes in browser by opening `index.html`
- Gather stakeholder feedback
- Use as reference for implementation (see `tasks.md` if generated)

7. Generate Index File
   Create an HTML index for easy navigation:

Path: prd/<feature-name>/prototype-ui/index.html

Content structure (responsive, clean HTML):

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><Feature Name> - UI Prototypes</title>
    <style>
        /* Clean, minimal styling for the index */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            line-height: 1.6;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
            background: #f9fafb;
        }
        header {
            margin-bottom: 3rem;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 1rem;
        }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .meta { color: #6b7280; font-size: 0.875rem; }
        .components {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }
        .component-card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1.5rem;
            transition: box-shadow 0.2s;
        }
        .component-card:hover {
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .component-card h2 {
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }
        .component-card p {
            color: #6b7280;
            font-size: 0.875rem;
            margin-bottom: 1rem;
        }
        .component-card a {
            display: inline-block;
            background: #3b82f6;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            text-decoration: none;
            font-size: 0.875rem;
            transition: background 0.2s;
        }
        .component-card a:hover {
            background: #2563eb;
        }
        .footer {
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <header>
        <h1><Feature Name> - UI Prototypes</h1>
        <p class="meta">Generated from PRD • <Date> • <Component Count> components</p>
    </header>

    <main class="components">
        <!-- For each component -->
        <div class="component-card">
            <h2><Component Name></h2>
            <p><Component description from PRD></p>
            <a href="<component-name>.html">View Prototype →</a>
        </div>
    </main>

    <footer class="footer">
        <p><strong>Design Specification:</strong> <a href="design-spec.md">design-spec.md</a></p>
        <p><strong>Source PRD:</strong> <code><path-to-prd></code></p>
        <p>Generated using Claude Code PRD Builder • <a href="https://claude.ai/code">claude.ai/code</a></p>
    </footer>

</body>
</html>
8. Summary Report
Provide a comprehensive summary including backup information (if applicable):

✅ **Prototype generation complete**

{IF_BACKUP_CREATED}
📂 **Backup created:**

- Old prototypes saved to: `prd/<feature-name>/prototype-ui-backup-<timestamp>/`

📦 **Generated prototypes:**

- prd/<feature-name>/prototype-ui/<component-1>.html
- prd/<feature-name>/prototype-ui/<component-2>.html
- ... (list all components)
- prd/<feature-name>/prototype-ui/design-spec.md
- prd/<feature-name>/prototype-ui/index.html

{IF_DESIGN_CHOICES_PRESERVED}
🎨 **Design choices preserved:**

- Aesthetic: <aesthetic> (from previous prototype)
- Fidelity: <fidelity> (from previous prototype)
- Interactivity: <interactivity> (from previous prototype)

📖 **Next steps:**

1.  Open `prd/<feature-name>/prototype-ui/index.html` in browser to review prototypes
    {IF_BACKUP_CREATED}2. Compare with backup if needed: `prototype-ui-backup-<timestamp>/`
    {ENDIF}
2.  Run `/prd-export prd/<feature-name>/prd.md` to create stakeholder summary
3.  Run `/prd-tasks prd/<feature-name>/prd.md` to generate implementation tasks
    Template Variables:

{IF_BACKUP_CREATED}: Include this section only if a backup was created in Step 3.6
{IF_DESIGN_CHOICES_PRESERVED}: Include this section only if previous choices were detected in Step 3.7
Replace <timestamp>, <aesthetic>, <fidelity>, <interactivity> with actual values
Operating Principles
Always read the PRD first — Extract as much context as possible before asking questions
Ask focused questions — Don't ask about things already clear in the PRD
Generate incrementally — Create and save one component at a time, showing progress
Handle errors gracefully — If frontend-design fails for one component, continue with others
Provide clear feedback — Show what's being created and where files are saved
Create professional output — The index and design spec should be stakeholder-ready
Respect user choices — Honor the aesthetic and fidelity preferences exactly
Avoid duplication — If components overlap, ask the user to clarify scope
Save incrementally — Don't wait to save all components at the end
