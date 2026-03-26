# Design System Specification: The Lab Terminal

## 1. Overview & Creative North Star
**The Creative North Star: "The Digital Autopsy"**

This design system rejects the "friendly" clutter of modern SaaS in favor of a sterile, high-precision environment. It is built for deep focus and linear intelligence. We are moving away from the horizontal fragmentation of sidebars and dashboards toward a singular, vertical narrative—a "storytelling" scroll that mimics the output of a high-end research terminal.

The aesthetic is **Surgical Minimalism**. By utilizing a hyper-focused, single-column layout, we force the user into a state of immersion. There is no "interface" to navigate; there is only the data. To achieve this, we rely on intentional asymmetry within the center column and a radical commitment to flat, docked elements.

---

## 2. Colors
Our palette is a study in clinical precision. We use "surgical" black and white to define the environment, with a single, high-frequency kinetic accent.

### The Palette
- **Background (`#131313`):** A deep, infinite black. This is the "Lab Floor."
- **Primary (`#FFFFFF`):** Pure light. Used for critical data and primary actions.
- **Surface Tint / Primary Accent (`#00DCE5`):** A sharp, electric cyan. This is the "Laser." Use it sparingly for active states, data highlights, and progress indicators.
- **Grayscale (Secondary/Tertiary):** Strictly monochromatic (`#C6C6C7`, `#454747`). Used for metadata and de-emphasized UI.

### The Rules of Engagement
- **The No-Line Rule:** 1px solid borders for sectioning are strictly prohibited. In a laboratory environment, boundaries are defined by light and shadow, not ink. Separate sections using background shifts (e.g., transitioning from `surface` to `surface-container-low`).
- **Surface Hierarchy:** Depth is "docked," not floating. Use `surface-container-lowest` (`#0E0E0E`) for recessed input areas and `surface-container-high` (`#2A2A2A`) for active data blocks.
- **Signature Textures:** For high-priority CTAs, use a subtle gradient transition from `surface-tint` (`#00DCE5`) to `primary-container` (`#31EAF3`). This provides a "glowing filament" effect that feels alive.

---

## 3. Typography
The system utilizes a dual-engine typographic approach to balance technical precision with academic rigor.

### The Engines
- **Space Grotesk (The Technical Layer):** Used for UI elements, labels, data points, and code. It conveys the "Terminal" aspect of the brand.
- **Newsreader (The Narrative Layer):** Used for long-form research and editorial content. This is the "Human" element within the machine.

### Hierarchy & Scale
- **Display LG (56px, Space Grotesk):** For major section breaks in the infinite scroll.
- **Title MD (18px, Newsreader):** For analytical insights and research summaries.
- **Label SM (11px, Space Grotesk, All Caps):** For technical metadata and timestamps.

**Mixed-Language Handling:** For Chinese/English mixed text, maintain a 1.6x line-height for `body-md` to ensure that complex characters do not feel "cramped" against the sterile Latin glyphs of Newsreader.

---

## 4. Elevation & Depth
In "The Lab Terminal," there are no shadows. Objects do not "float" above the surface; they are integrated into it.

- **The Layering Principle:** Depth is achieved through **Tonal Stacking**. 
    - Base: `surface` (`#131313`)
    - Inset Content: `surface-container-low` (`#1B1B1B`)
    - Highlighted Data: `surface-container-high` (`#2A2A2A`)
- **Glassmorphism:** To maintain immersion during the infinite scroll, use `backdrop-blur` (20px) on the top navigation header with a 70% opacity `surface` color. This allows the "data" to ghost behind the header as it passes.
- **The Ghost Border:** If a boundary is required for accessibility, use `outline-variant` (`#474747`) at 15% opacity. It should be felt, not seen.

---

## 5. Components

### Buttons
- **Primary:** Sharp `0px` corners. Background: `primary` (#FFFFFF), Text: `on-primary` (#002021). 
- **Active State:** A 2px bottom-glow using `surface-tint` (#00DCE5).
- **Secondary:** Transparent background with a `ghost-border`. Text: `primary`.

### Input Fields
- **The Inset Look:** Inputs must be docked into the page. Use `surface-container-lowest` with `0px` border-radius.
- **Focus State:** Change the background to `surface-container-high` and add a `surface-tint` vertical "caret" on the left edge.

### Data Chips
- Small, `0px` radius containers. Use `secondary-container` for the background. Text must be `label-sm` in Space Grotesk.

### The "Infinite" List
- Forbid all horizontal dividers. Separate list items using `spacing-6` (2rem) of vertical white space. If items need grouping, use a subtle background shift to `surface-container-low`.

### Pulse Indicator (Custom Component)
- A 4px square of `surface-tint` that slowly pulses. Place this next to "Live" or "Processing" data to signify the terminal is active.

---

## 6. Do's and Don'ts

### Do
- **Do** use `0px` border-radius for everything. The lab is a place of hard edges.
- **Do** center-align the main content column (max-width: 800px) to create a focused, cinematic experience.
- **Do** use "leading zeros" for all numbers (e.g., `01`, `02`) to maintain the technical terminal vibe.

### Don't
- **Don't** use sidebars. The user should never be distracted from the vertical flow.
- **Don't** use standard "Drop Shadows." Use tonal shifts or nothing at all.
- **Don't** use "Dirty" colors. If it's not pure grayscale or the specific Primary Accent, it doesn't belong in the lab.
- **Don't** use icons with rounded caps. All iconography must be sharp-edged and linear.

---

## 7. Spacing Scale
Precision is maintained through a rigid adherence to the spacing scale.
- **Content Gaps:** Use `spacing-10` (3.5rem) between major story blocks.
- **Data Grouping:** Use `spacing-2` (0.7rem) for related technical metadata.
- **Margin:** Always maintain a minimum of `spacing-8` (2.75rem) horizontal padding on mobile to ensure the "column" feel is preserved.```