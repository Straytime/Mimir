# Design System: Industrial Precision / Lab Terminal

## 1. Overview & Creative North Star: "The Kinetic Monolith"
This design system is a radical departure from the "soft" web. Our Creative North Star is **The Kinetic Monolith**. It envisions the interface not as a website, but as a high-precision instrument—a piece of laboratory hardware carved from obsidian and powered by cold logic.

To achieve this, we move beyond the "template" look by embracing **Absolute Angularity**. By stripping away every curve, shadow, and decorative line, we create an environment of extreme focus. Complexity is managed through "Tonal Architecture" rather than structural borders. The result is a high-end, editorial-grade research platform that feels authoritative, clinical, and uncompromisingly technical.

## 2. Colors: Tonal Architecture
We do not use lines to define space; we use light and mass. The palette is rooted in deep, light-absorbing charcoals, punctuated by a high-intensity Amber signal.

### The "No-Line" Rule
**Explicit Instruction:** 1px solid borders are prohibited for sectioning. Structural boundaries must be defined solely through background color shifts.
* Place a `surface-container-high` module inside a `surface` layout to create a "recessed" or "elevated" zone.
* The eye should perceive the change in density, not a stroke.

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of technical plates.
* **Base Layer:** `surface-container-lowest` (#000000) for the primary workspace.
* **Intermediate Modules:** `surface-container` (#1a1919) for sidebars or secondary utilities.
* **Active Overlays:** `surface-bright` (#2c2c2c) for momentary focus areas.

### Signature "Amber Glow"
The `primary` (#ffad3a) and `primary_container` (#f59e0a) tokens are high-visibility signals. Use them only for:
1. Critical Action States (Active buttons)
2. Data Points of Interest 
3. Active Cursor/Focus States (A subtle 2px outer glow using `primary` at 20% opacity is the only "shadow" permitted).

## 3. Typography: Technical Authority
Our type system pairs the mathematical precision of **Space Grotesk** with the invisible clarity of **Inter**.

* **Space Grotesk (Headers/Technical Labels):** Used for `display`, `headline`, and `label` roles. It conveys a "terminal" aesthetic. Set letter-spacing to `-0.02em` for headers and `+0.05em` for small labels to mimic printed industrial plates.
* **Inter (Data/Body):** Used for `title` and `body` roles. In an LLM-driven context, readability of long-form analysis is paramount. Inter provides the neutral, high-legibility counterpoint to the aggressive headers.

**Typographic Hierarchy:**
* **Display-LG (3.5rem):** Reserved for singular, high-impact data points or terminal IDs.
* **Label-SM (0.6875rem, All Caps):** Used for metadata, timestamps, and "System Status" indicators.

## 4. Elevation & Depth: Tonal Layering
Traditional depth (shadows) is forbidden. We achieve hierarchy through **Density and Light Extraction.**

* **The Layering Principle:** Depth is achieved by "stacking." A `surface-container-highest` panel floating over a `surface_dim` background creates a natural lift.
* **The "Ghost Border" Fallback:** In extreme cases where contrast is required between identical tones, use a `outline_variant` (#494847) at **15% opacity**. This should feel like a faint etch on glass, not a drawn line.
* **Active "Glow" State:** Instead of lifting a card on hover, increase the background brightness by one tier (e.g., `surface-container` to `surface-container-high`) and apply a subtle `primary` glow to the left-hand edge (2px width).

## 5. Components: Precision Primitive

### Buttons
* **Style:** Zero border-radius. No gradients.
* **Primary:** `primary` background, `on_primary_fixed` text. High-contrast, maximum visibility.
* **Secondary:** `surface-variant` background, `on_surface` text. For auxiliary actions.
* **Interaction:** On hover, primary buttons should "invert" (text becomes Amber, background becomes black) to mimic a flickering terminal screen.

### Input Fields (The "Terminal" Input)
* **Style:** No background fill. Only a bottom-aligned `outline` (#777575) 2px thick.
* **Focus:** The bottom-bar shifts to `primary` (#ffad3a) with a 4px "block" cursor at the end of the text string.

### Cards & Lists
* **Constraint:** Forbid divider lines.
* **Execution:** Use the `Spacing Scale`. A `12` (2.75rem) gap between content blocks provides enough "air" for the eye to distinguish sections without needing a line.
* **Nesting:** Nested LLM responses should use a `surface_container_low` background to distinguish them from the main thread.

### Technical Micro-Components
* **Data Monoliths:** Small, high-density blocks of info using `label-sm` in `primary` color to highlight.
* **Terminal Scrim:** A 5% opacity scan-line pattern (linear-gradient) can be applied to the `surface` layer to enhance the "Lab Terminal" feel.
* **Attached Hint Panels:** Selector help text should be rendered as a docked overlay anchored to a `relative` trigger region. Keep it rectangular, shadowless, and tone-shifted from the base surface; it may overlap nearby empty space, but it must not consume layout height or force surrounding modules to reflow.

## 6. Do's and Don'ts

### Do:
* **Embrace Asymmetry:** Align technical metadata to the far right while keeping primary text left-aligned to create a "control panel" feel.
* **Use Mono-spacing Logic:** Even though Inter isn't a mono font, treat layouts as if they are on a grid of cells. Align everything to the 0.2rem/0.4rem spacing increments.
* **Trust the Amber:** Let the Vivid Amber do the heavy lifting. If the screen feels "boring," don't add more colors—add more Amber signal markers.

### Don't:
* **Never use a Border Radius:** Even 1px of rounding destroys the "Industrial Precision" aesthetic.
* **No Soft Shadows:** If it looks like it’s "floating" on a cloud, it’s wrong. It should look like it’s "mounted" on a rack.
* **Avoid "Web" Patterns:** No rounded "Pill" chips. Use rectangular blocks. No "standard" blue links. Use Amber underlines or chevrons `>`.
