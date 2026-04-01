# UI Window 001: The Flow Landing Page

**Route Path:** `/`
**Component File:** `src/app/page.tsx`

## Design Aesthetic
- Inserts the user into the Hexamind experience with a "Google Flow" style immersion.
- Features a high-quality abstract, deep blurry background (`/images/flow-bg.png`).
- Employs severe "glassmorphism" (`backdrop-blur-3xl`, `bg-indigo-charcoal/20`, white border strokes).
- Focuses purely on one CTA: **"Initiate ARIA"**.

## Interactions
- **Entrance:** The primary welcome module container fades and floats up (`framer-motion` `y: 30` to `y: 0` entrance).
- **Hover States:** The glowing pill button CTA features an expanded white blurry drop-shadow and a subtle arrow shift upon hover.
- **Exit / Routing:** Clicking the button triggers an exit via Next.js router. The `template.tsx` root wraps the layout, ensuring that route changes invoke a smooth fade and blur crossfade to the next window.

## Purpose
Sets the mood. Welcomes users to the premium, technical venture studio environment without overwhelming them with data or models immediately.

## Review Notes
*(Leave notes here during UX reviews)*
- Needs review on background image compression quality for mobile devices.
