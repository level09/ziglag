# Design System Strategy: High-End Editorial & Tonal Layering

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Digital Atelier."** 

We are moving away from the rigid, "bootstrap-style" layouts of the early 2020s toward a sophisticated, editorial experience that feels curated rather than engineered. This system rejects the standard 1px border and the generic drop shadow in favor of **Tonal Depth** and **Asymmetric Breathing Room**. 

By leveraging the tension between high-contrast typography (Plus Jakarta Sans) and soft, nested surfaces (Be Vietnam Pro), we create an environment that feels premium, authoritative, and intentionally designed. The goal is to make every screen feel like a page from a high-end fashion or architectural journal—minimalist yet deeply textured.

---

## 2. Colors & Surface Architecture

The palette is anchored by a deep indigo-violet (`primary: #353aaf`) and balanced by warm, organic neutrals (`surface: #fbf9f8`). This is not a "flat" design system; it is a system of light and material.

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders to define sections. Boundaries must be established through color shifts. 
- To separate a header from a hero, transition from `surface` to `surface-container-low`. 
- To define a card, place a `surface-container-lowest` (#ffffff) element against a `surface-container` (#f0eded) background.

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of fine paper. 
- **Level 0 (Base):** `surface` (#fbf9f8) – The canvas.
- **Level 1 (Sections):** `surface-container-low` (#f6f3f2) – Subtle layout shifts.
- **Level 2 (Interactive Elements):** `surface-container-highest` (#e4e2e1) – High-priority utility areas.

### The Glass & Gradient Rule
To inject "soul" into the digital interface:
- **Hero Gradients:** Use a linear gradient from `primary` (#353aaf) to `primary_container` (#4e54c8) at a 135-degree angle. This provides a soft luminosity that flat fills cannot replicate.
- **Glassmorphism:** For floating navigation or modal overlays, use `surface` at 70% opacity with a `24px` backdrop-blur. This allows the underlying content to bleed through, creating an integrated, high-end feel.

---

## 3. Typography: The Editorial Voice

We utilize a three-font strategy to create clear brand hierarchy and a signature rhythm.

*   **Display & Headline (Plus Jakarta Sans):** Our "Commanding" voice. Use `display-lg` (3.5rem) with tight letter-spacing (-0.02em) for hero sections. This typeface provides the structural authority of a modern broadsheet.
*   **Body & Title (Be Vietnam Pro):** Our "Functional" voice. This geometric sans-serif offers exceptional readability while maintaining the "Atelier" aesthetic. 
*   **Labels (Inter):** Our "Technical" voice. Used sparingly for micro-copy and metadata to provide a crisp, utilitarian contrast to the softer body text.

**Typographic Intent:** Always lean into high-contrast scales. Do not be afraid to jump from a `display-lg` headline directly to a `body-md` description, skipping middle weights to create visual "drama."

---

## 4. Elevation & Depth

Standard shadows are forbidden. We define depth through light physics and tonal layering.

*   **The Layering Principle:** Soft lift is achieved by nesting. A `surface-container-lowest` (#ffffff) card sitting on a `surface-container-low` (#f6f3f2) background provides enough contrast for the eye to perceive a change in plane without artificial "ink."
*   **Ambient Shadows:** If a floating element (like a FAB or Popover) requires a shadow, use: `box-shadow: 0 20px 40px rgba(53, 58, 175, 0.06);`. The shadow must be tinted with the `primary` hue to mimic natural ambient occlusion.
*   **The Ghost Border:** If accessibility requires a stroke (e.g., in high-contrast modes), use the `outline_variant` token at **15% opacity**. It should be felt, not seen.

---

## 5. Component Guidelines

### Buttons (The Statement Piece)
- **Primary:** Gradient fill (`primary` to `primary_container`), `full` roundedness, and `1rem 2rem` padding. Transitions should be a slow `0.3s ease-out`.
- **Secondary:** `surface-container-highest` background with `on_surface` text. No border.
- **Tertiary:** Text-only, using `label-md` in all-caps with `0.1rem` letter-spacing.

### Cards & Lists
- **The Divider Ban:** Never use horizontal rules `<hr>`. Use `spacing-12` (3rem) of vertical white space or a subtle background shift to `surface-container-low` to denote a new item.
- **Composition:** Use `rounded-xl` (1.5rem) for all large cards to soften the editorial edge.

### Input Fields
- **State over Stroke:** Use a `surface-container-highest` background fill for the input area. On focus, do not thicken a border; instead, shift the background to `surface-container-lowest` and add a subtle `primary` glow (2px blur).

### Signature Component: The "Content Reveal"
Use a large-scale `display-md` headline that overlaps two different surface tiers (e.g., half on `surface`, half on `surface-container-low`). This intentional asymmetry breaks the "template" look and feels bespoke.

---

## 6. Do’s and Don’ts

### Do:
- **Embrace White Space:** If a section feels crowded, double the spacing token (e.g., move from `spacing-10` to `spacing-20`).
- **Use Tonal Transitions:** Shift background colors to guide the user's eye through the narrative of the page.
- **Optical Kerning:** Manually tighten headlines (`display` and `headline` scales) to ensure they feel like a cohesive visual unit.

### Don't:
- **No Pure Blacks:** Never use `#000000`. Use `on_surface` (#1b1c1c) for deep contrast that retains warmth.
- **No Default Borders:** Avoid the `outline` token at 100% opacity. It creates "visual noise" that breaks the premium feel.
- **No Tight Grids:** Avoid cramming elements into a 12-column constraint. Allow elements to "bleed" off-center to maintain the editorial vibe.