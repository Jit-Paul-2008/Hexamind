# UI Window 001: The Flow Landing Page

**Route Path:** `/`
**Component File:** `src/app/page.tsx`

## Design Aesthetic
- Inspired by Google Flow / Google I/O landing pages: open, cinematic, text-first.
- Background image (`/images/flow-bg.png`) is a dark abstract fluid render.
- Text is NOT contained inside a glass box. Elements float independently on the image.
- Mouse-tracking spotlight blur follows the cursor using `framer-motion` spring values to create a radial glow that feels physical.

## Layout (top to bottom)
- **Top-left**: `HEXAMIND // SYSTEM V1.0` label with pulsing dot indicator
- **Top-right**: `ARIA OFFLINE` glassmorphic pill status
- **Center**: Hero headline in two separate lines with distinct sizes and fonts:
  - `Think` — large serif, white, full bleed
  - `Beyond Limits.` — italic serif, lavender-gray, slightly smaller
- **Below center**: Sub-tagline paragraph in light sans-serif
- **CTA**: `Initiate ARIA` pill button with animated line, arrow, and ambient hover glow. Routes to `/aria`.
- **Bottom-left**: `Est. 2026 — Hexamind Labs` metadata
- **Bottom-right**: `Scroll after entry` with bouncing arrow

## Interactions
- **Mouse spotlight**: `useMotionValue` + `useSpring` track cursor position. A 400px radial gradient follows with smooth spring physical lag.
- **Entrance**: All elements stagger-animate in (opacity fade + y translation) with increasing delays.
- **CTA hover**: Button expands ambient blur, line stretches, arrow translates right.

## Review Notes
- ✅ No single glass container — open layout matches Google Flow reference
- ✅ Mouse blur spotlight active

