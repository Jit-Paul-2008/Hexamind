"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import type { AgentShape } from "@/lib/agents";

function ShapeMesh({ shape, accentColor }: { shape: AgentShape; accentColor: string }) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (!meshRef.current) return;
    meshRef.current.rotation.y += delta * 0.55;
    meshRef.current.rotation.x += delta * 0.22;
    const pulse = 1 + Math.sin(state.clock.elapsedTime * 1.3) * 0.04;
    meshRef.current.scale.setScalar(pulse);
  });

  const geo = () => {
    switch (shape) {
      case "tetrahedron":  return <tetrahedronGeometry args={[1.1, 0]} />;
      case "icosahedron":  return <icosahedronGeometry args={[1.1, 0]} />;
      case "dodecahedron": return <dodecahedronGeometry args={[0.95, 0]} />;
      case "box":          return <boxGeometry args={[1.5, 1.5, 1.5]} />;
    }
  };

  return (
    <mesh ref={meshRef}>
      {geo()}
      <meshStandardMaterial
        color={accentColor}
        metalness={0.45}
        roughness={0.12}
        emissive={accentColor}
        emissiveIntensity={0.2}
        transparent
        opacity={0.88}
      />
    </mesh>
  );
}

export default function AgentShape({
  shape,
  accentColor,
}: {
  shape: AgentShape;
  accentColor: string;
}) {
  return (
    <div style={{ width: "100%", height: "100%" }}>
      <Canvas camera={{ position: [0, 0, 4], fov: 36 }} gl={{ antialias: true, alpha: true }}>
        <ambientLight intensity={0.45} />
        <directionalLight position={[5, 5, 5]} intensity={1.2} color="#ffffff" />
        <directionalLight position={[-4, -3, -2]} intensity={0.7} color={accentColor} />
        <ShapeMesh shape={shape} accentColor={accentColor} />
      </Canvas>
    </div>
  );
}
