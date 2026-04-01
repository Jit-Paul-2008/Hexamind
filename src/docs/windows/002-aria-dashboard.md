# UI Window 002: The Interactive ARIA Dashboard

**Route Path:** `/aria`
**Component File:** `src/app/aria/page.tsx`

## Design Aesthetic
- Builds heavily upon the track established in `ROADMAP.md` (Track A - Frontend First).
- Digital Brutalism themes using sophisticated darks and low-opacity whites to emphasize premium UI.
- Background is composed of a responsive 3D WebGL Canvas scene that occupies the lowest z-index layer.

## Interactions
### Canvas
- Features a spinning Geometrical compound mesh (Octahedron and Icosahedron combined).
- Incorporates `MeshTransmissionMaterial` meaning it refracts the light and backdrop using computationally expensive but highly realistic glass/liquid materials.
- Managed by `PresentationControls`, allowing the user to rotate the object natively with spring physics.

### UI Overlay
- Housed in `src/components/ui/OverlayList.tsx`.
- Infinite mock scroll with "snap-mandatory" logic.
- Framer Motion provides staged delayed entry animations for each element as they initially mount.
- `pointer-events-none` container masks interaction except where necessary so the user can interact freely with the background canvas and the scrollable list at the same time.

## Review Notes
*(Leave notes here during UX reviews)*
- Needs to be hooked up to `LangGraph`/`FastAPI` once Track B is initiated.
