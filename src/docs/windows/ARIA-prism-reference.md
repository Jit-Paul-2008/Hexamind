# ARIA Prism — Shape Reference & Geometry Spec

## Visual Reference
The approved prism shape for ARIA's body model is a **double-ended elongated bipyramid crystal** (6 vertices, 8 triangular faces).

Reference image: the wireframe crystal provided by the user on 2026-04-01.

## Geometry Definition (`buildCrystalGeometry()`)

```
Vertex layout:
  v0  →  upper apex      [+2.0,  0.00,  0.00]   (right spike, pre-tilt)
  v1  →  lower apex      [-2.0,  0.00,  0.00]   (left spike, pre-tilt)
  v2  →  belt front-top  [-0.1, +0.75, +0.65]
  v3  →  belt back-top   [+0.45,+0.35, -0.65]
  v4  →  belt front-bot  [+0.1, -0.75, +0.65]
  v5  →  belt back-bot   [-0.45,-0.35, -0.65]

8 triangular faces (winding CCW viewed from outside):
  Upper pyramid: (0,2,3)  (0,3,4)  (0,4,5)  (0,5,2)
  Lower pyramid: (1,3,2)  (1,4,3)  (1,5,4)  (1,2,5)

Group tilt: rotation.z = Math.PI / 6  (30°)
  → Maps the horizontal elongated axis to the upper-right / lower-left diagonal
  → Matches the reference image orientation exactly
```

## Material
- **Solid**: `MeshTransmissionMaterial` (from @react-three/drei)
  - color: `#0d0f13` (near-black dark glass)
  - attenuationColor: `#383e4e` (indigo-charcoal ambient tint)
  - transmission: 0.92, roughness: 0.08, ior: 1.5
- **Edges**: `THREE.EdgesGeometry` + `LineBasicMaterial`
  - color: `#b6bac5` (lavender-gray), opacity: 0.25–0.35 (animated pulse)

## Animation
- `rotation.y += delta * 0.22`  — slow constant Y spin
- `rotation.x += delta * 0.08`  — very slow X tilt
- `position.y = sin(t * 0.7) * 0.14`  — gentle float
- Edge opacity pulses with `sin(t * 1.2) * 0.1`

## Trigger
Appears on scroll via `useInView(amount: 0.35)` with blur-to-sharp + rise entrance animation.
